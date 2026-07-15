"""RETAILIO adapter — https://order.retailio.in

Verified flow (with a live session cookie):
  1. Attach cookies + localStorage → navigate to /rio/home
  2. Click the sidebar link "Order by Product" (JS-nav, no href)
     which takes us to the product-search page.
  3. Type product word-by-word into #input_searchOrderByProduct
     (placeholder "Search for a product").
  4. Wait for the autocomplete suggestions / matching product cards
     to appear.
  5. Score candidates using shared canonicalization; click the best.
  6. Parse each matched product card for
        matched_name, manufacturer, pack (from description),
        stock (Qty NNN),
        scheme (e.g. "10+1" or "No Schemes" → None),
        PTR (₹...), MRP (₹...).
  7. Emit one ExtractedItem per matching card.

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
SEARCH_INPUT = "#input_searchOrderByProduct"


def _clean(txt: str) -> str:
    return re.sub(r"\s+", " ", (txt or "").strip())


def _first_num(txt: str) -> Optional[str]:
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

    async def _click_order_by_product(self, page) -> bool:
        """Click the "Order by Product" sidebar link. Returns True if clicked."""
        try:
            return bool(await page.evaluate("""() => {
                for (const a of document.querySelectorAll('a')) {
                    if (!a.offsetParent) continue;
                    const t = (a.innerText || a.title || '').trim();
                    if (t === 'Order by Product') { a.click(); return true; }
                }
                return false;
            }"""))
        except Exception:
            return False

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
            try:
                await page.reload(timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(4500)
            except Exception:
                pass

            if "secure-login" in (page.url or "").lower():
                out.status = "LOGIN_FAILED"
                out.detail = "SESSION_EXPIRED — please re-authenticate via RETAILIO SESSION menu"
                out.login_screenshot = await self._screenshot(page, "session-expired")
                return out
            out.login_screenshot = await self._screenshot(page, "logged-in")
            out.debug["landing_url"] = page.url

            # Click sidebar "Order by Product"
            clicked = await self._click_order_by_product(page)
            out.debug["order_by_product_clicked"] = clicked
            await page.wait_for_timeout(4500)

            # Locate the search input
            search_el = await page.query_selector(SEARCH_INPUT)
            if not search_el:
                # Some builds mount input asynchronously — poll for 5s
                for _ in range(20):
                    await page.wait_for_timeout(250)
                    search_el = await page.query_selector(SEARCH_INPUT)
                    if search_el:
                        break

            if not search_el:
                # Fallback: any input with the expected placeholder
                search_el = await page.query_selector('input[placeholder="Search for a product"]')

            if not search_el:
                out.status = "ERROR"
                out.detail = "Product-search input not found on Retailio Order by Product page"
                out.results_screenshot = await self._screenshot(page, "no-search")
                return out

            try: await search_el.click()
            except Exception: pass
            try: await search_el.fill("")
            except Exception: pass

            raw_tokens = re.findall(r"[a-z0-9]+", product.lower())
            if not raw_tokens:
                out.status = "NOT_FOUND"
                out.detail = "Empty product query"
                return out
            query_canon = canon(product)

            # Type word-by-word (Retailio needs input events to trigger XHR)
            for i, tok in enumerate(raw_tokens):
                piece = (" " if i > 0 else "") + tok
                try:
                    await search_el.type(piece, delay=90)
                except Exception:
                    try: await page.keyboard.type(piece, delay=90)
                    except Exception: break
                await page.wait_for_timeout(900 if i < len(raw_tokens) - 1 else 3200)

            out.search_screenshot = await self._screenshot(page, "search-open")

            # Retailio renders autocomplete rows as `div.VQ66y` elements
            # (CSS module class — verified via DOM probe). Each row's text
            # follows the pattern:
            #   [Topselling] <Product Name> <Description> <MFR>
            #   <N> Distributors found <In Stock|Out of Stock>
            rows_info = await page.evaluate(r"""() => {
                // Prefer class-based selector; fall back to div containing
                // "Distributors found" text.
                let rows = Array.from(document.querySelectorAll('div.VQ66y'));
                if (!rows.length) {
                    rows = Array.from(document.querySelectorAll('div')).filter(d => {
                        if (!d.offsetParent) return false;
                        const t = (d.innerText || '');
                        if (t.length > 400 || t.length < 20) return false;
                        return /Distributors\s+found/i.test(t) && /(in\s*stock|out\s*of\s*stock)/i.test(t);
                    });
                }
                const out = [];
                for (let idx = 0; idx < rows.length; idx++) {
                    const r = rows[idx];
                    const txt = (r.innerText || '').trim();
                    const lines = txt.split(/\n+/).map(s => s.trim()).filter(Boolean);
                    // Skip "Topselling" badge line if present
                    let cur = 0;
                    if (/^topselling$/i.test(lines[0] || '')) cur = 1;
                    const name = lines[cur] || '';
                    const desc = lines[cur+1] || '';
                    const mfr  = lines[cur+2] || '';
                    // Distributor count + stock
                    const distM = txt.match(/(\d+)\s+Distributors?\s+found/i);
                    const dist_count = distM ? distM[1] : null;
                    const in_stock = /In\s*Stock/i.test(txt) && !/Out\s*of\s*Stock/i.test(txt);
                    // Pack: "15 tablet(s) in strip", "10 ml eye/ear drop in bottle"
                    const packM = desc.match(/^\s*(\d+\s*(?:ml|mg|g|kg|gm|tab|tablet|cap|capsule|no'?s?|nos|s|piece|pcs|drop|drops)[\w'\-\s()]*)/i);
                    const pack = packM ? packM[1].trim() : desc || null;
                    out.push({ index: idx, name, desc, mfr, dist_count, in_stock, pack, txt: txt.slice(0,300) });
                }
                return out;
            }""") or []

            out.debug["dropdown_row_count"] = len(rows_info)

            if not rows_info:
                out.status = "NOT_FOUND"
                out.detail = "No autocomplete suggestions returned by Retailio"
                out.results_screenshot = await self._screenshot(page, "no-suggestions")
                return out

            # Score each row's product name
            scored = []
            for r in rows_info:
                s = score(query_canon, r.get("name") or "")
                scored.append((s, r))
            scored.sort(key=lambda x: -x[0])
            out.debug["candidates"] = [{"name": r.get("name"), "score": s} for s, r in scored[:10]]
            out.debug["query_canon"] = query_canon

            # Manual pick override
            if force_candidate_name:
                f_canon = canon(force_candidate_name)
                for i, (s, r) in enumerate(scored):
                    n = r.get("name") or ""
                    if canon(n) == f_canon or force_candidate_name.lower() in n.lower():
                        scored.insert(0, (55, r))
                        scored.pop(i + 1)
                        break

            best_s, best = (scored[0] if scored else (-1000, None))
            if best is None or best_s < ACCEPT_THRESHOLD:
                out.status = "NOT_FOUND"
                out.detail = f"No matching product variant in Retailio (best score {best_s})"
                out.debug["autocomplete_candidates"] = [r.get("name") for _, r in scored[:15]]
                out.results_screenshot = await self._screenshot(page, "no-match")
                return out

            # Click the best matching autocomplete row to open the DETAIL VIEW.
            # The detail view lists each distributor's Qty, Scheme, MRP, PTR
            # for the selected product — exactly what we want.
            best_index = best.get("index")
            clicked_ok = False
            try:
                clicked_ok = bool(await page.evaluate(
                    """(idx) => {
                        const rows = document.querySelectorAll('div.VQ66y');
                        if (idx < rows.length) {
                            rows[idx].click();
                            return true;
                        }
                        return false;
                    }""",
                    best_index,
                ))
            except Exception:
                clicked_ok = False
            out.debug["detail_clicked"] = clicked_ok
            await page.wait_for_timeout(4500)
            out.results_screenshot = await self._screenshot(page, "detail-view")

            # Parse the per-distributor detail view.
            detail = await page.evaluate(r"""() => {
                const t = (document.body.innerText || '');
                // Find the "Selected Product" or the "N distributor(s) found!"
                // heading and slice from there.
                const anchor = t.search(/\d+\s*distributor\(?s\)?\s*found/i);
                if (anchor < 0) return null;
                // Grab a reasonable chunk after the anchor (2000 chars)
                const chunk = t.slice(anchor, anchor + 4000);
                // Also capture the "Selected Product" block above the anchor
                const abovePos = Math.max(0, anchor - 300);
                const header = t.slice(abovePos, anchor);
                return { header, chunk };
            }""") or {}

            distributors: list[dict] = []
            if detail.get("chunk"):
                chunk = detail["chunk"]
                # Split by MRP occurrences — each seller block ends with MRP/PTR
                # values. We'll walk the text sequentially looking for markers.
                # Simpler: use a regex that captures the seller block.
                # Pattern: seller name (line before "Qty") ... MRP ₹NN ... PTR ₹NN
                lines = [l.strip() for l in chunk.split("\n") if l.strip()]
                cur: dict = {}
                for i, ln in enumerate(lines):
                    m_qty = re.match(r"^Qty\s+(\d+)$", ln, re.I)
                    if m_qty:
                        # Seller name is the most recent non-descriptor line above
                        # (skip "Delivery by ..." lines and generic phrases).
                        for j in range(i - 1, max(-1, i - 8), -1):
                            cand = lines[j]
                            if re.match(r"^delivery by", cand, re.I): continue
                            if re.match(r"^this order may take", cand, re.I): continue
                            if re.match(r"^Add to Cart", cand, re.I): continue
                            if cand in ("MRP", "PTR", "Qty", "MARGIN 20%"): continue
                            if re.match(r"^(No Schemes|Scheme|GST|Dist\.?Discount|MARGIN|₹|\d+\.?\d*%?$)", cand, re.I): continue
                            # Heuristic: seller names contain a comma or Pvt/Pharma
                            if len(cand) > 4 and (',' in cand or re.search(r"pharma|pvt|ltd|medi|distributor|store", cand, re.I)):
                                cur = {"seller": cand}
                                break
                        cur["stock"] = m_qty.group(1)
                        continue

                    if "seller" in cur:
                        # Scheme line
                        if re.match(r"^No\s*Schemes$", ln, re.I):
                            cur["scheme"] = None
                            continue
                        m_sch = re.match(r"^Scheme[:\s]*(.+)$", ln, re.I)
                        if m_sch:
                            v = m_sch.group(1).strip()
                            cur["scheme"] = None if re.match(r"^no", v, re.I) else v
                            continue
                        # If next line is a scheme value like "10+1" alone
                        if re.match(r"^\d+\s*\+\s*\d+$", ln):
                            cur["scheme"] = ln
                            continue
                        # MRP line — value is on the NEXT line
                        if ln.upper() == "MRP":
                            if i + 1 < len(lines):
                                v = lines[i + 1]
                                m_v = re.search(r"([\d.,]+)", v)
                                if m_v:
                                    cur["mrp"] = m_v.group(1).replace(",", "")
                            continue
                        # PTR line — value is on the NEXT line
                        if ln.upper() == "PTR":
                            if i + 1 < len(lines):
                                v = lines[i + 1]
                                m_v = re.search(r"([\d.,]+)", v)
                                if m_v:
                                    cur["ptr"] = m_v.group(1).replace(",", "")
                            continue
                        # End-of-block marker
                        if ln.lower() == "add to cart":
                            if cur.get("seller"):
                                distributors.append(cur)
                            cur = {}
                # Push final if not closed
                if cur.get("seller"):
                    distributors.append(cur)

            items: List[ExtractedItem] = []
            for d in distributors:
                items.append(ExtractedItem(
                    product=product,
                    matched_name=best.get("name") or None,
                    pack=best.get("pack") or None,
                    manufacturer=best.get("mfr") or None,
                    seller=d.get("seller") or None,
                    available_qty=d.get("stock") or None,
                    scheme=d.get("scheme") or None,
                    mrp=d.get("mrp") or None,
                    ptr=d.get("ptr") or None,
                ))

            # Fallback: if drilling failed, still emit the dropdown-level rows
            if not items:
                accepted = [r for s, r in scored if s >= max(ACCEPT_THRESHOLD, best_s - 25)]
                for r in accepted:
                    dc = r.get("dist_count") or "0"
                    aq = dc if r.get("in_stock") else "0"
                    items.append(ExtractedItem(
                        product=product,
                        matched_name=r.get("name") or None,
                        pack=r.get("pack") or None,
                        manufacturer=r.get("mfr") or None,
                        available_qty=aq,
                    ))

            out.items = items
            in_stock = sum(1 for it in items if (it.available_qty or "").isdigit() and int(it.available_qty) > 0)
            out.status = "SUCCESS" if items else "NOT_FOUND"
            out.detail = f"{len(items)} seller(s), {in_stock} in stock"
            if quantity:
                total = sum(int(it.available_qty) for it in items if (it.available_qty or "").isdigit())
                out.can_fulfill = total >= quantity
            return out

        except Exception as e:
            out.status = "ERROR"
            out.detail = f"{e.__class__.__name__}: {e}"
            try: out.results_screenshot = await self._screenshot(page, "error")
            except Exception: pass
            return out
