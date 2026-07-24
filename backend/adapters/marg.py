"""MARG (margcompusoft.com/eRetail) adapter.

Real post-login navigation flow (Feb 2026, verified live):
  1. GET /eRetail/Order/NewOrder?supplier=0   (Place-Order screen)
  2. Ensure #chkSupplierListAll is checked → "All" suppliers
  3. Type product into #txtProduct           (jQuery-UI autocomplete)
  4. Read ul.ui-autocomplete > li entries. Each <li> is 5 lines:
        Line 1: PRODUCT NAME              → matched_name
        Line 2: MANUFACTURER              → manufacturer
        Line 3: SUPPLIER NAME             → seller
        Line 4: Box info ("Box : 10") or blank
        Line 5: "N PCS" or "M:N PCS"      → available_qty (last integer)
  5. Score against the fuzzy canon, emit one ExtractedItem per match.
     MRP/PTR/Deal are shown only after clicking a specific entry; we skip
     those in the aggregate query for speed.

Cookies come from the MARG SESSION dialog (marg_session.py). MARG uses
ASP.NET_SessionId as the auth token — no separate .ASPXAUTH cookie.
"""
from __future__ import annotations
import re
from typing import List, Optional
from .base import BaseAdapter, ExtractionOutcome, ExtractedItem
from .match import canon, score, ACCEPT_THRESHOLD


DASHBOARD_URL = "https://margcompusoft.com/eRetail/Dashboard/Dashboard"
PLACE_ORDER_URL = "https://margcompusoft.com/eRetail/Order/NewOrder?supplier=0"
LOGIN_HINT = "/User/Login"

PRODUCT_INPUT = "#txtProduct"
ALL_SUPPLIERS_CB = "#chkSupplierListAll"
AUTOCOMPLETE_LIST = "ul.ui-autocomplete li"


def _clean(txt: str) -> str:
    return re.sub(r"\s+", " ", (txt or "").strip())


class MargAdapter(BaseAdapter):
    portal_type = "MARG"

    def __init__(self, cookies: Optional[list] = None, screenshotter=None):
        super().__init__(screenshotter=screenshotter)
        self.cookies = cookies or []

    async def _apply_cookies(self, page):
        if self.cookies:
            try:
                await page.context.add_cookies(self.cookies)
            except Exception:
                pass

    async def test_login(self, page, url: str, username: str, password: str):
        try:
            await self._apply_cookies(page)
            await page.goto(DASHBOARD_URL, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            if LOGIN_HINT in (page.url or ""):
                return False, "SESSION_EXPIRED — re-authenticate via MARG SESSION menu"
            return True, "Session OK"
        except Exception as e:
            return False, f"{e.__class__.__name__}: {e}"

    async def _tick_all_suppliers(self, page):
        try:
            await page.evaluate(
                """() => {
                    const cb = document.querySelector('#chkSupplierListAll');
                    if (cb && !cb.checked) { cb.click(); }
                }"""
            )
        except Exception:
            pass
        await page.wait_for_timeout(600)

    async def _type_product(self, page, product: str) -> bool:
        """Type into #txtProduct and wait for autocomplete to populate."""
        try:
            el = await page.query_selector(PRODUCT_INPUT)
            if not el:
                return False
            await el.scroll_into_view_if_needed(timeout=3000)
            await el.click()
            await el.fill("")
        except Exception:
            return False

        tokens = re.findall(r"[a-z0-9]+", product.lower())
        if not tokens:
            return False
        typed = ""
        for i, tok in enumerate(tokens):
            piece = (" " if i > 0 else "") + tok
            try:
                await el.type(piece, delay=100)
            except Exception:
                try: await page.keyboard.type(piece, delay=100)
                except Exception: return False
            typed += piece
            try:
                await el.evaluate(
                    """(node, val) => {
                        node.value = val;
                        for (const t of ['input','keyup','change','keydown']) {
                            node.dispatchEvent(new Event(t, {bubbles:true}));
                        }
                        if (window.jQuery) {
                            try { window.jQuery(node).trigger('input').trigger('keyup').trigger('change'); } catch(e){}
                        }
                    }""",
                    typed,
                )
            except Exception:
                pass
            # Longer wait after the last token so the autocomplete resolves
            await page.wait_for_timeout(900 if i < len(tokens) - 1 else 3500)
        return True

    async def _read_autocomplete(self, page) -> list:
        """Return the visible autocomplete rows as a list of dicts:
        { name, manufacturer, supplier, box_info, stock }"""
        try:
            items = await page.evaluate(
                """() => {
                    const out = [];
                    const els = document.querySelectorAll('ul.ui-autocomplete li');
                    els.forEach(li => {
                        if (li.offsetParent === null) return;
                        const t = (li.innerText || '').trim();
                        if (!t) return;
                        out.push({ text: t });
                    });
                    return out;
                }"""
            )
        except Exception:
            items = []
        return items or []

    # ---------- Main extract ----------
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
            await page.goto(PLACE_ORDER_URL, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)
            if LOGIN_HINT in (page.url or ""):
                out.status = "LOGIN_FAILED"
                out.detail = "SESSION_EXPIRED — please authenticate via MARG SESSION menu"
                out.login_screenshot = await self._screenshot(page, "session-expired")
                return out
            out.login_screenshot = await self._screenshot(page, "new-order")

            # 1) Select ALL suppliers
            await self._tick_all_suppliers(page)
            out.search_screenshot = await self._screenshot(page, "suppliers-all")

            # 2) Type product and pull autocomplete
            ok = await self._type_product(page, product)
            if not ok:
                out.status = "ERROR"
                out.detail = "MARG: Product Name input not found on New Order page"
                out.results_screenshot = await self._screenshot(page, "no-input")
                return out

            entries = await self._read_autocomplete(page)
            out.debug["autocomplete_count"] = len(entries)
            out.results_screenshot = await self._screenshot(page, "autocomplete")

            if not entries:
                out.status = "NOT_FOUND"
                out.detail = "MARG: autocomplete returned no rows for query"
                return out

            # 3) Parse & score each entry
            query_canon = canon(product)
            items: List[ExtractedItem] = []
            debug_rows: List[dict] = []
            for e in entries:
                txt = _clean(e.get("text", ""))
                if not txt:
                    continue
                lines = [_clean(x) for x in (e.get("text") or "").split("\n") if _clean(x)]
                if len(lines) < 2:
                    continue
                matched_name = lines[0]
                manufacturer = lines[1] if len(lines) > 1 else None
                seller = lines[2] if len(lines) > 2 else None
                box_info = lines[3] if len(lines) > 3 else None
                stock_line = lines[-1]  # last non-empty line usually "N PCS"

                # Parse stock: "63 PCS" | "26:8 PCS" | "0 PCS"
                stock = None
                m = re.search(r"(\d+)\s*(?::\s*(\d+))?\s*PCS", stock_line, re.I)
                if m:
                    # If pattern is "M:N PCS", take N (loose stock). Else take M.
                    stock = m.group(2) or m.group(1)

                # Parse pack from Box info if present
                pack = None
                if box_info:
                    mp = re.search(r"Box\s*[:\-]?\s*(\d+)", box_info, re.I)
                    if mp:
                        pack = mp.group(1)

                s = score(query_canon, matched_name)
                debug_rows.append({"name": matched_name, "seller": seller, "score": s, "stock": stock})
                if s < ACCEPT_THRESHOLD - 5:
                    continue

                items.append(ExtractedItem(
                    product=product,
                    matched_name=matched_name,
                    pack=pack,
                    available_qty=stock,
                    manufacturer=manufacturer,
                    seller=seller,
                    raw_row=lines,
                ))

            out.debug["scored"] = debug_rows[:15]

            if not items:
                out.status = "NOT_FOUND"
                out.detail = f"MARG: {len(entries)} autocomplete rows but none matched the query (best score below threshold)"
                return out

            out.items = items
            out.status = "SUCCESS"
            in_stock = sum(1 for it in items if (it.available_qty or "").isdigit() and int(it.available_qty) > 0)
            out.detail = f"{len(items)} supplier(s), {in_stock} in stock"
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
