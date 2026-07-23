"""MARG (margcompusoft.com/eRetail) adapter.

Uses the aggregated "Search Supplier" feature — after cookie-based login,
searches a product across ALL connected suppliers in one call.

Flow (best-effort — refined once we can inspect the authed pages):
  1. Attach saved session cookies (`marg_session.get_saved_cookies()`).
  2. Navigate to the eRetail home / dashboard.
  3. Open "Search Supplier" screen (link/nav item).
  4. Ensure the supplier filter is set to "ALL".
  5. Type the product name into the visible search input; wait for
     autocomplete / result rows.
  6. Score each candidate row using the shared canonicalizer; if quantity
     is supplied, populate the qty field.
  7. Read Stock / MRP / PTR / Scheme cells and emit one ExtractedItem per
     supplier row.

If cookies are missing/expired, returns LOGIN_FAILED with "SESSION_EXPIRED"
so the UI prompts a fresh OTP.
"""
from __future__ import annotations
import re
from typing import List, Optional
from .base import BaseAdapter, ExtractionOutcome, ExtractedItem
from .match import canon, score, ACCEPT_THRESHOLD


HOME_URL = "https://margcompusoft.com/eRetail/Home/Index"
# Common candidate URLs for the Search Supplier screen — first that responds
# 200 with a search UI is used.
SEARCH_URL_CANDIDATES = [
    "https://margcompusoft.com/eRetail/Home/SearchSupplier",
    "https://margcompusoft.com/eRetail/Supplier/Search",
    "https://margcompusoft.com/eRetail/Home/Search",
    "https://margcompusoft.com/eRetail/Product/Search",
]


def _clean(txt: str) -> str:
    return re.sub(r"\s+", " ", (txt or "").strip())


def _extract_money(s: str) -> Optional[str]:
    if not s:
        return None
    m = re.search(r"[\d,]+\.\d{1,2}|[\d,]+", s.replace("₹", " ").replace("Rs.", " "))
    return m.group(0).replace(",", "") if m else None


class MargAdapter(BaseAdapter):
    portal_type = "MARG"

    def __init__(self, cookies: Optional[list] = None, screenshotter=None):
        super().__init__(screenshotter=screenshotter)
        self.cookies = cookies or []

    # ---------- Login (session-cookie only) ----------
    async def test_login(self, page, url: str, username: str, password: str):
        try:
            if self.cookies:
                await page.context.add_cookies(self.cookies)
            await page.goto(HOME_URL, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            if "/User/Login" in (page.url or ""):
                return False, "SESSION_EXPIRED — re-authenticate via MARG SESSION menu"
            return True, "Session OK"
        except Exception as e:
            return False, f"{e.__class__.__name__}: {e}"

    async def _apply_cookies(self, page):
        if self.cookies:
            try:
                await page.context.add_cookies(self.cookies)
            except Exception:
                pass

    async def _open_search_supplier(self, page) -> bool:
        """Attempt to reach the Search Supplier screen. Returns True on
        success. Uses (a) direct URLs (b) sidebar link fallback."""
        # (a) Try direct URLs first
        for u in SEARCH_URL_CANDIDATES:
            try:
                await page.goto(u, timeout=25000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                cur = (page.url or "").lower()
                if "/user/login" in cur:
                    return False  # session expired
                # Heuristic: page contains a search field and 'supplier' or 'search' text
                body = ""
                try:
                    body = (await page.inner_text("body"))[:2000].lower()
                except Exception:
                    pass
                if ("search supplier" in body or "search product" in body
                        or "supplier" in body and await page.query_selector("input[type='search'], input[type='text']:visible")):
                    return True
            except Exception:
                continue

        # (b) Fallback: on Home, click a nav link whose text matches
        try:
            await page.goto(HOME_URL, timeout=25000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            clicked = await page.evaluate("""() => {
                const rx = /search\\s*supplier|search\\s*product|search/i;
                for (const a of document.querySelectorAll('a, button, li')) {
                    if (!a.offsetParent) continue;
                    const t = (a.innerText || a.textContent || '').trim();
                    if (t.length > 60) continue;
                    if (rx.test(t)) { a.click(); return t; }
                }
                return null;
            }""")
            if clicked:
                await page.wait_for_timeout(3000)
                return "/user/login" not in (page.url or "").lower()
        except Exception:
            pass
        return False

    async def _select_all_suppliers(self, page):
        """Ensure the supplier picker is set to ALL. MARG's exact UI varies
        (dropdown/multiselect/chips); we try a few strategies idempotently."""
        try:
            # Strategy 1: a select with an "ALL" option
            for sel in await page.query_selector_all("select"):
                try:
                    if not await sel.is_visible():
                        continue
                    opts = await sel.query_selector_all("option")
                    for o in opts:
                        val = (await o.text_content() or "").strip().lower()
                        if val in ("all", "all suppliers", "all supplier"):
                            v = await o.get_attribute("value")
                            if v is not None:
                                await sel.select_option(v)
                                return True
                except Exception:
                    continue
            # Strategy 2: a chip/button labelled ALL
            clicked = await page.evaluate("""() => {
                const rx = /^\\s*all(\\s+suppliers?)?\\s*$/i;
                for (const el of document.querySelectorAll('button, a, li, span, div')) {
                    if (!el.offsetParent) continue;
                    const t = (el.innerText || '').trim();
                    if (rx.test(t)) { el.click(); return t; }
                }
                return null;
            }""")
            return bool(clicked)
        except Exception:
            return False

    # ---------- Extract ----------
    async def extract(self, page, url: str, username: str, password: str,
                      product: str, quantity: int, distributor_name: str = "",
                      force_candidate_name: Optional[str] = None) -> ExtractionOutcome:
        out = ExtractionOutcome()
        out.requested_qty = quantity or None

        if not self.cookies:
            out.status = "LOGIN_FAILED"
            out.detail = "SESSION_EXPIRED — please authenticate via MARG SESSION menu"
            return out

        await self._apply_cookies(page)

        try:
            # 1) Home / dashboard
            await page.goto(HOME_URL, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            if "/User/Login" in (page.url or ""):
                out.status = "LOGIN_FAILED"
                out.detail = "SESSION_EXPIRED — please authenticate via MARG SESSION menu"
                out.login_screenshot = await self._screenshot(page, "session-expired")
                return out
            out.login_screenshot = await self._screenshot(page, "logged-in")

            # 2) Search Supplier screen
            ok = await self._open_search_supplier(page)
            if not ok:
                out.status = "ERROR"
                out.detail = "Could not open 'Search Supplier' screen on MARG"
                out.results_screenshot = await self._screenshot(page, "no-search-supplier")
                return out

            # 3) Force supplier filter → ALL
            await self._select_all_suppliers(page)
            await page.wait_for_timeout(700)

            # 4) Locate the product search input
            search_selectors = [
                'input[placeholder*="search" i]',
                'input[placeholder*="product" i]',
                'input[type="search"]',
                'input[name*="search" i]',
                'input[id*="search" i]',
                'input[type="text"]:visible',
            ]
            el = None
            used_selector = None
            for sel in search_selectors:
                try:
                    e = await page.query_selector(sel)
                    if e and await e.is_visible():
                        el = e
                        used_selector = sel
                        break
                except Exception:
                    continue
            if not el:
                out.status = "ERROR"
                out.detail = "Product search input not found on MARG"
                out.results_screenshot = await self._screenshot(page, "no-search-input")
                return out
            out.debug["search_selector"] = used_selector

            try: await el.scroll_into_view_if_needed(timeout=3000)
            except Exception: pass
            try: await el.click()
            except Exception: pass
            try: await el.fill("")
            except Exception: pass

            # 5) Type product word-by-word to trigger autocomplete/live search
            raw_tokens = re.findall(r"[a-z0-9]+", product.lower())
            if not raw_tokens:
                out.status = "NOT_FOUND"
                out.detail = "Empty product query"
                return out
            typed_so_far = ""
            for i, tok in enumerate(raw_tokens):
                piece = (" " if i > 0 else "") + tok
                try:
                    await el.type(piece, delay=90)
                except Exception:
                    try: await page.keyboard.type(piece, delay=90)
                    except Exception: break
                typed_so_far += piece
                try:
                    await el.evaluate(
                        """(node, val) => {
                            try {
                                node.value = val;
                                for (const t of ['input','keyup','change','keydown']) {
                                    node.dispatchEvent(new Event(t, {bubbles:true}));
                                }
                                if (window.jQuery) {
                                    try { window.jQuery(node).trigger('input').trigger('keyup').trigger('change'); } catch(e){}
                                }
                            } catch(e){}
                        }""",
                        typed_so_far,
                    )
                except Exception:
                    pass
                await page.wait_for_timeout(950 if i < len(raw_tokens) - 1 else 3200)

            # If the site requires an Enter/Search button, click it
            try:
                await page.evaluate("""() => {
                    const rx = /^(search|find|go)$/i;
                    for (const b of document.querySelectorAll('button, input[type=submit]')) {
                        if (!b.offsetParent) continue;
                        const t = (b.innerText || b.value || '').trim();
                        if (rx.test(t)) { b.click(); return; }
                    }
                }""")
                await page.wait_for_timeout(3000)
            except Exception:
                pass

            out.search_screenshot = await self._screenshot(page, "search-done")

            # 6) Collect result rows. MARG typically renders a results table
            # with one row per (product × supplier). We try several common
            # selectors and pick whichever returns visible rows.
            row_selectors = [
                'table.table tbody tr',
                'table tbody tr',
                'div.card.result',
                'div.supplier-row',
                'div.product-row',
                'li.result-item',
                '[role="row"]',
            ]
            rows = []
            used_row_sel = None
            for rs in row_selectors:
                try:
                    els = await page.query_selector_all(rs)
                    vis = []
                    for e in els:
                        try:
                            if await e.is_visible():
                                vis.append(e)
                        except Exception:
                            continue
                    if vis:
                        rows = vis
                        used_row_sel = rs
                        break
                except Exception:
                    continue
            out.debug["row_selector"] = used_row_sel
            out.debug["row_count"] = len(rows)

            if not rows:
                out.status = "NOT_FOUND"
                out.detail = "MARG: no supplier rows returned for query"
                out.results_screenshot = await self._screenshot(page, "no-rows")
                return out

            query_canon = canon(product)
            items: List[ExtractedItem] = []
            for r in rows:
                try:
                    txt = _clean(await r.inner_text()) if await r.inner_text() else ""
                    if not txt:
                        continue
                    # Try to read cells for tables; else split by newlines
                    cell_texts: List[str] = []
                    cells = await r.query_selector_all("td, div.cell, span.cell")
                    if cells:
                        for c in cells:
                            try:
                                cell_texts.append(_clean(await c.text_content() or ""))
                            except Exception:
                                continue
                    if not cell_texts:
                        cell_texts = [_clean(x) for x in txt.split("\n") if _clean(x)]

                    # Score row against the product query
                    row_score = score(query_canon, txt)
                    if row_score < ACCEPT_THRESHOLD - 15:
                        continue

                    # Best-effort field extraction from row text
                    joined = " | ".join(cell_texts)
                    supplier = None
                    matched_name = None
                    mrp = ptr = scheme = stock = pack = mfr = None
                    # 1st non-empty cell is usually the supplier name; 2nd product
                    if len(cell_texts) >= 2:
                        supplier = cell_texts[0] or None
                        matched_name = cell_texts[1] or None

                    # Field patterns
                    m_mrp = re.search(r"(?:mrp|m\\.r\\.p\\.?)\\s*[:\\-]?\\s*([₹]?\\s*[\\d,]+(?:\\.\\d+)?)", joined, re.I)
                    m_ptr = re.search(r"(?:ptr|rate|net\\s*rate|price)\\s*[:\\-]?\\s*([₹]?\\s*[\\d,]+(?:\\.\\d+)?)", joined, re.I)
                    m_sch = re.search(r"(?:scheme|offer|disc(?:ount)?)\\s*[:\\-]?\\s*([\\d\\+/\\.\\s%A-Za-z]+?)(?:\\||$)", joined, re.I)
                    m_stk = re.search(r"(?:stock|qty|available)\\s*[:\\-]?\\s*(\\d+)", joined, re.I)
                    m_pk  = re.search(r"(?:pack|packing)\\s*[:\\-]?\\s*([\\w\\-\\.]+)", joined, re.I)
                    if m_mrp: mrp = _extract_money(m_mrp.group(1))
                    if m_ptr: ptr = _extract_money(m_ptr.group(1))
                    if m_sch: scheme = _clean(m_sch.group(1))
                    if m_stk: stock = m_stk.group(1)
                    if m_pk:  pack = m_pk.group(1)

                    items.append(ExtractedItem(
                        product=product,
                        matched_name=matched_name,
                        pack=pack,
                        mrp=mrp,
                        ptr=ptr,
                        available_qty=stock,
                        scheme=scheme,
                        manufacturer=mfr,
                        seller=supplier,
                        raw_row=cell_texts or [txt],
                    ))
                except Exception:
                    continue

            out.results_screenshot = await self._screenshot(page, "results")

            if not items:
                out.status = "NOT_FOUND"
                out.detail = "MARG: rows found but no product matches after scoring"
                return out

            out.items = items
            out.status = "SUCCESS"
            in_stock = sum(1 for it in items if (it.available_qty or "").isdigit() and int(it.available_qty) > 0)
            out.detail = f"{len(items)} supplier(s), {in_stock} in stock"
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
