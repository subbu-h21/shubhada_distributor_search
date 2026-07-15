"""RETAILIO adapter — https://order.retailio.in

Requires a valid cookie session (see retailio_session.py). Cookies are added
to the browser context before any navigation and localStorage tokens (if
captured during OTP verification) are replayed after the first load so the
SPA hydrates in a signed-in state.

Flow:
  1. Attach cookies + localStorage → navigate to the main app URL
  2. Type product name word-by-word into the search field, wait for the
     autocomplete list (Retailio shows product cards with MRP/PTR/Scheme
     and a stock badge inline).
  3. Pick the best matching card using shared canonicalization / scoring.
  4. Extract Stock + MRP + PTR + Scheme for the chosen product.
  5. Emit one ExtractedItem per SKU variant (pack) that matched.

If the SPA lands us back on the login page the adapter returns
LOGIN_FAILED with detail SESSION_EXPIRED so the frontend can prompt
re-verification of OTP.
"""
from __future__ import annotations
import re
from typing import List, Optional
from .base import BaseAdapter, ExtractionOutcome, ExtractedItem
from .match import canon, score, ACCEPT_THRESHOLD


APP_URL = "https://order.retailio.in/rio/home"
SEARCH_URL = "https://order.retailio.in/rio/products"
LOGIN_URL = "https://order.retailio.in/rio/secure-login"


def _clean(txt: str) -> str:
    return re.sub(r"\s+", " ", (txt or "").strip())


def _first_num(txt: str) -> Optional[str]:
    """Return the first number (int/float) as a string, or None."""
    if not txt:
        return None
    m = re.search(r"\d+(?:\.\d+)?", txt)
    return m.group(0) if m else None


class RetailioAdapter(BaseAdapter):
    portal_type = "RETAILIO"

    def __init__(self, cookies: Optional[list] = None, local_storage: Optional[dict] = None, screenshotter=None):
        super().__init__(screenshotter=screenshotter)
        self.cookies = cookies or []
        self.local_storage = local_storage or {}

    # ---------- Login (no-op) ----------
    async def test_login(self, page, url: str, username: str, password: str):
        try:
            if self.cookies:
                try: await page.context.add_cookies(self.cookies)
                except Exception: pass
            await page.goto(APP_URL, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3500)
            if "secure-login" in (page.url or "").lower():
                return False, "SESSION_EXPIRED — re-authenticate via RETAILIO SESSION menu"
            return True, "Session OK"
        except Exception as e:
            return False, f"{e.__class__.__name__}: {e}"

    async def _apply_session(self, page):
        if self.cookies:
            try: await page.context.add_cookies(self.cookies)
            except Exception: pass

    async def _replay_local_storage(self, page):
        if not self.local_storage:
            return
        try:
            await page.evaluate(
                "(kv) => { for (const [k,v] of Object.entries(kv)) { try { localStorage.setItem(k, v); } catch(e){} } }",
                self.local_storage,
            )
        except Exception:
            pass

    # ---------- Extract ----------
    async def extract(self, page, url: str, username: str, password: str,
                      product: str, quantity: int, distributor_name: str = "",
                      force_candidate_name: Optional[str] = None) -> ExtractionOutcome:
        out = ExtractionOutcome()
        out.requested_qty = quantity or None

        if not self.cookies:
            out.status = "LOGIN_FAILED"
            out.detail = "SESSION_EXPIRED — please re-authenticate via RETAILIO SESSION menu"
            return out

        await self._apply_session(page)

        try:
            await page.goto(APP_URL, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            await self._replay_local_storage(page)
            # Reload once so the SPA picks up localStorage tokens
            try:
                await page.reload(timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)
            except Exception:
                pass

            if "secure-login" in (page.url or "").lower():
                out.status = "LOGIN_FAILED"
                out.detail = "SESSION_EXPIRED — please re-authenticate via RETAILIO SESSION menu"
                out.login_screenshot = await self._screenshot(page, "session-expired")
                return out
            out.login_screenshot = await self._screenshot(page, "logged-in")

            # Find the search input. Retailio uses a top-bar autocomplete.
            search_selectors = [
                'input[placeholder*="Search" i]',
                'input[placeholder*="product" i]',
                'input[type="search"]',
                'input[name*="search" i]',
                'input.search-input',
                'header input',
            ]
            search_el = None
            for sel in search_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        search_el = el
                        break
                except Exception:
                    continue

            if not search_el:
                # Some Retailio builds route to a dedicated search page
                try:
                    await page.goto(SEARCH_URL, timeout=45000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(2500)
                except Exception:
                    pass
                for sel in search_selectors:
                    try:
                        el = await page.query_selector(sel)
                        if el and await el.is_visible():
                            search_el = el
                            break
                    except Exception:
                        continue

            if not search_el:
                out.status = "ERROR"
                out.detail = "Search input not found on Retailio SPA"
                out.results_screenshot = await self._screenshot(page, "no-search")
                return out

            try:
                await search_el.click()
                await search_el.fill("")
            except Exception:
                pass

            raw_tokens = re.findall(r"[a-z0-9]+", product.lower())
            if not raw_tokens:
                out.status = "NOT_FOUND"
                out.detail = "Empty product query"
                return out
            query_canon = canon(product)

            for i, tok in enumerate(raw_tokens):
                if i > 0:
                    try: await page.keyboard.type(" ", delay=60)
                    except Exception: pass
                try:
                    await page.keyboard.type(tok, delay=90)
                except Exception:
                    break
                await page.wait_for_timeout(900 if i < len(raw_tokens) - 1 else 2500)

            out.search_screenshot = await self._screenshot(page, "autocomplete-open")

            # Collect autocomplete rows / product cards.
            # Retailio typically renders suggestions under an autocomplete
            # container with items containing product name, MRP, PTR, and a
            # stock chip. We fall back to `div[role="option"]` or common
            # product-card classes.
            row_selectors = [
                'ul[role="listbox"] li',
                'div[role="listbox"] div[role="option"]',
                '.autocomplete-item',
                '.search-result-item',
                '.product-suggestion',
                '.product-card',
                '.MuiAutocomplete-option',
                'li.product',
            ]
            candidates = []
            rows = []
            for sel in row_selectors:
                try:
                    els = await page.query_selector_all(sel)
                    if els:
                        rows = els
                        break
                except Exception:
                    continue

            for r in rows:
                try:
                    txt = _clean(await r.inner_text()) or ""
                    if not txt:
                        continue
                    # Product name is usually the first line
                    name_line = txt.split("\n")[0].strip()
                    if not name_line:
                        continue
                    candidates.append((r, txt, name_line))
                except Exception:
                    continue

            if not candidates:
                out.status = "NOT_FOUND"
                out.detail = "No autocomplete suggestions returned by Retailio"
                out.results_screenshot = await self._screenshot(page, "no-suggestions")
                return out

            best_el, best_score, best_txt, best_name = None, -1000, None, None
            for r, full, name in candidates:
                s = score(query_canon, name)
                if s > best_score:
                    best_score, best_el, best_txt, best_name = s, r, full, name
            out.debug["candidates"] = [{"name": n, "score": score(query_canon, n)} for _, _, n in candidates[:15]]
            out.debug["query_canon"] = query_canon

            # Manual pick override
            if force_candidate_name:
                f_canon = canon(force_candidate_name)
                for r, full, name in candidates:
                    if canon(name) == f_canon or force_candidate_name.lower() in name.lower():
                        best_el, best_score, best_txt, best_name = r, 55, full, name
                        break

            if best_el is None or best_score < ACCEPT_THRESHOLD:
                out.status = "NOT_FOUND"
                out.detail = f"No matching product variant in RETAILIO (best score {best_score})"
                out.debug["autocomplete_candidates"] = [n for _, _, n in candidates[:20]]
                out.results_screenshot = await self._screenshot(page, "no-match")
                return out

            # Click the best candidate to open the product detail
            try:
                await best_el.click()
            except Exception as e:
                out.status = "ERROR"
                out.detail = f"Click failed: {e}"
                return out

            # Wait for the detail card / variant list to appear
            await page.wait_for_timeout(3500)
            out.results_screenshot = await self._screenshot(page, "product-detail")

            # Extract Stock + MRP + PTR + Scheme.
            # Strategy: enumerate variant rows on the page and pick their fields.
            variants = await page.evaluate(
                """() => {
                    const results = [];
                    const cards = document.querySelectorAll('.variant-row, .pack-row, .sku-row, [data-testid*="variant"], [class*="variant"], [class*="pack-option"], [class*="product-detail"]');
                    // Fallback: any product card containing MRP + PTR labels
                    const scan = cards.length ? Array.from(cards) : Array.from(document.querySelectorAll('div,section,article')).filter(n => {
                        const t = (n.innerText || '').toLowerCase();
                        return t.includes('mrp') && (t.includes('ptr') || t.includes('rate'));
                    }).slice(0, 8);

                    for (const c of scan) {
                        const t = (c.innerText || '').trim();
                        if (!t) continue;
                        const pick = (rx) => {
                            const m = t.match(rx);
                            return m ? m[1].trim() : null;
                        };
                        const pack = pick(/pack[:\\s]*([\\w\\s\\d*]+)/i);
                        const mrp = pick(/mrp[^\\d]*([\\d.]+)/i);
                        const ptr = pick(/ptr[^\\d]*([\\d.]+)/i) || pick(/rate[^\\d]*([\\d.]+)/i);
                        const scheme = pick(/scheme[^A-Za-z0-9]*([\\w\\d\\+\\-\\s\\/%\\.]+?)(?:\\n|$)/i);
                        const stockTxt = pick(/stock[^A-Za-z0-9]*([A-Za-z0-9]+)/i);
                        const outOfStock = /out\\s*of\\s*stock|not\\s*available|unavailable/i.test(t);
                        results.push({ pack, mrp, ptr, scheme, stockTxt, outOfStock, text: t.slice(0, 400) });
                    }
                    return results;
                }"""
            ) or []

            items: List[ExtractedItem] = []
            for v in variants:
                stock_num = _first_num(v.get("stockTxt") or "")
                if v.get("outOfStock") and not stock_num:
                    stock_num = "0"
                items.append(ExtractedItem(
                    product=product,
                    matched_name=best_name,
                    pack=v.get("pack") or None,
                    mrp=v.get("mrp") or None,
                    ptr=v.get("ptr") or None,
                    scheme=v.get("scheme") or None,
                    available_qty=stock_num,
                ))

            # If we couldn't find variant rows, still emit one item with the
            # header-level MRP/PTR captured from the page.
            if not items:
                header = await page.evaluate(
                    """() => {
                        const t = (document.body.innerText || '');
                        const pick = (rx) => { const m = t.match(rx); return m ? m[1] : null; };
                        return {
                            mrp: pick(/mrp[^\\d]*([\\d.]+)/i),
                            ptr: pick(/ptr[^\\d]*([\\d.]+)/i) || pick(/rate[^\\d]*([\\d.]+)/i),
                            scheme: pick(/scheme[^A-Za-z0-9]*([\\w\\d\\+\\-\\s\\/%\\.]+?)(?:\\n|$)/i),
                            stock: pick(/stock[^A-Za-z0-9]*([A-Za-z0-9]+)/i),
                            outOfStock: /out\\s*of\\s*stock|unavailable|not\\s*available/i.test(t),
                        };
                    }"""
                ) or {}
                stock_num = _first_num(header.get("stock") or "")
                if header.get("outOfStock") and not stock_num:
                    stock_num = "0"
                items.append(ExtractedItem(
                    product=product,
                    matched_name=best_name,
                    mrp=header.get("mrp"),
                    ptr=header.get("ptr"),
                    scheme=header.get("scheme"),
                    available_qty=stock_num,
                ))

            out.items = items
            in_stock = sum(1 for it in items if (it.available_qty or "").isdigit() and int(it.available_qty) > 0)
            out.status = "SUCCESS" if in_stock > 0 else "NOT_FOUND" if all((it.available_qty or "") in ("0", "") for it in items) and not any(it.mrp for it in items) else "SUCCESS"
            out.detail = f"{len(items)} variant(s), {in_stock} in stock"
            if quantity:
                total_stock = sum(int(it.available_qty) for it in items if (it.available_qty or "").isdigit())
                out.can_fulfill = total_stock >= quantity
            return out
        except Exception as e:
            out.status = "ERROR"
            out.detail = f"{e.__class__.__name__}: {e}"
            try: out.results_screenshot = await self._screenshot(page, "error")
            except Exception: pass
            return out
