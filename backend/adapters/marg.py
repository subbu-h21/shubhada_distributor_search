"""MARG (margcompusoft.com/eRetail) adapter.

Post-login navigation flow (from user-verified UI, Feb 2026):
  1. Dashboard  →  https://margcompusoft.com/eRetail/Dashboard/Dashboard
  2. Sidebar menu "Order" (expandable)  →  submenu "Place Order"
  3. On Place-Order screen, click the "+" next to "Supplier List"
  4. Tick the "select all suppliers" checkbox → confirm
  5. Type the product name in the search field
  6. Read stock rows: MRP, PTR, Scheme, Available Stock, per supplier

If cookies are missing/expired the adapter returns LOGIN_FAILED so the UI
prompts a fresh OTP.
"""
from __future__ import annotations
import re
from typing import List, Optional
from .base import BaseAdapter, ExtractionOutcome, ExtractedItem
from .match import canon, score, ACCEPT_THRESHOLD


DASHBOARD_URL = "https://margcompusoft.com/eRetail/Dashboard/Dashboard"
LOGIN_HINT = "/User/Login"


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

    # ---------- Navigation helpers ----------
    async def _open_place_order(self, page) -> bool:
        """Click the Order menu in the sidebar, then the Place Order submenu.
        Returns True if a Place-Order screen loaded."""
        # Try clicking "Order" (may expand a submenu)
        try:
            await page.evaluate(
                """() => {
                    for (const el of document.querySelectorAll('a, li, span, div, button')) {
                        if (!el.offsetParent) continue;
                        const t = (el.innerText || el.textContent || '').trim();
                        if (/^order$/i.test(t)) { el.click(); return t; }
                    }
                    return null;
                }"""
            )
        except Exception:
            pass
        await page.wait_for_timeout(1200)

        # Now click Place Order
        try:
            clicked = await page.evaluate(
                """() => {
                    for (const el of document.querySelectorAll('a, li, span, div, button')) {
                        if (!el.offsetParent) continue;
                        const t = (el.innerText || el.textContent || '').trim();
                        if (/place\\s*order/i.test(t) && t.length < 40) { el.click(); return t; }
                    }
                    return null;
                }"""
            )
            if clicked:
                await page.wait_for_timeout(3500)
                return LOGIN_HINT not in (page.url or "")
        except Exception:
            pass

        # Fallback: direct URL guesses
        for u in ("https://margcompusoft.com/eRetail/Order/PlaceOrder",
                  "https://margcompusoft.com/eRetail/Order/Place",
                  "https://margcompusoft.com/eRetail/Retailer/PlaceOrder"):
            try:
                await page.goto(u, timeout=20000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2500)
                if LOGIN_HINT in (page.url or ""):
                    return False
                body = ""
                try:
                    body = (await page.inner_text("body"))[:2000].lower()
                except Exception:
                    pass
                if "supplier" in body or "place order" in body:
                    return True
            except Exception:
                continue
        return False

    async def _open_supplier_picker_and_select_all(self, page) -> bool:
        """On the Place-Order screen, click the + next to Supplier List and
        tick the master 'select all' checkbox. Then confirm/apply."""
        # Find and click "+" near Supplier List
        try:
            await page.evaluate(
                """() => {
                    // Look for the 'Supplier List' label and click a nearby
                    // + button / add-icon.
                    const labels = Array.from(document.querySelectorAll('*'))
                        .filter(el => {
                            if (!el.offsetParent) return false;
                            const t = (el.innerText || '').trim();
                            return /supplier\\s*list/i.test(t) && t.length < 40;
                        });
                    for (const lab of labels) {
                        // walk up 3 ancestors, look inside for a + button
                        let node = lab;
                        for (let i = 0; i < 4 && node; i++) {
                            const btn = node.querySelector && node.querySelector(
                                'button, a, i.fa-plus, i.fa-plus-circle, span.add, [class*="add"], [class*="plus"]');
                            if (btn && btn.offsetParent) {
                                const t = (btn.innerText || btn.title || btn.className || '').toLowerCase();
                                if (t.includes('+') || t.includes('plus') || t.includes('add') || btn.innerText.trim() === '+') {
                                    btn.click();
                                    return t;
                                }
                            }
                            node = node.parentElement;
                        }
                    }
                    // fallback: any visible '+' button on the page
                    for (const b of document.querySelectorAll('button, a, span, i')) {
                        if (!b.offsetParent) continue;
                        const t = (b.innerText || '').trim();
                        if (t === '+') { b.click(); return 'bare +'; }
                    }
                    return null;
                }"""
            )
        except Exception:
            pass
        await page.wait_for_timeout(2000)

        # In the opened supplier picker dialog, tick the "select all" checkbox
        try:
            await page.evaluate(
                """() => {
                    // Prefer a checkbox labelled 'Select All' / 'All' in the modal
                    const boxes = Array.from(document.querySelectorAll('input[type=checkbox]'));
                    // 1) Look for label text 'select all' / 'all'
                    for (const cb of boxes) {
                        if (!cb.offsetParent) continue;
                        const lbl = cb.closest('label')?.innerText
                                  || cb.parentElement?.innerText
                                  || '';
                        if (/select\\s*all|^\\s*all\\s*$/i.test(lbl) && !cb.checked) {
                            cb.click(); return 'select-all-labelled';
                        }
                    }
                    // 2) Fallback: the FIRST visible checkbox in a header row
                    for (const cb of boxes) {
                        if (!cb.offsetParent) continue;
                        // header/thead checkbox usually appears earliest
                        if (!cb.checked) { cb.click(); return 'first-visible'; }
                    }
                    return null;
                }"""
            )
        except Exception:
            pass
        await page.wait_for_timeout(1200)

        # Click Apply / Save / OK to confirm the picker
        try:
            await page.evaluate(
                """() => {
                    const rx = /^(apply|save|ok|confirm|done|proceed|add)$/i;
                    for (const b of document.querySelectorAll('button, input[type=submit], a')) {
                        if (!b.offsetParent) continue;
                        const t = (b.innerText || b.value || '').trim();
                        if (rx.test(t)) { b.click(); return t; }
                    }
                    return null;
                }"""
            )
        except Exception:
            pass
        await page.wait_for_timeout(2500)
        return True

    async def _search_product(self, page, product: str, quantity: int) -> Optional[str]:
        """Locate the product search input, type the product, wait for results."""
        # Candidate selectors — MARG's Place-Order screen uses a search box
        candidates = [
            'input[placeholder*="search" i]',
            'input[placeholder*="product" i]',
            'input[placeholder*="item" i]',
            'input[type="search"]',
            'input[name*="search" i]',
            'input[id*="search" i]',
            'input.form-control[type="text"]',
            'input[type="text"]:visible',
        ]
        el = None
        used = None
        for sel in candidates:
            try:
                e = await page.query_selector(sel)
                if e and await e.is_visible():
                    el = e; used = sel; break
            except Exception:
                continue
        if not el:
            return None

        try: await el.scroll_into_view_if_needed(timeout=3000)
        except Exception: pass
        try: await el.click()
        except Exception: pass
        try: await el.fill("")
        except Exception: pass

        tokens = re.findall(r"[a-z0-9]+", product.lower())
        if not tokens:
            return used
        typed = ""
        for i, tok in enumerate(tokens):
            piece = (" " if i > 0 else "") + tok
            try: await el.type(piece, delay=90)
            except Exception:
                try: await page.keyboard.type(piece, delay=90)
                except Exception: break
            typed += piece
            try:
                await el.evaluate(
                    """(node, val) => {
                        node.value = val;
                        for (const t of ['input','keyup','change','keydown']) {
                            node.dispatchEvent(new Event(t, {bubbles:true}));
                        }
                    }""",
                    typed,
                )
            except Exception:
                pass
            await page.wait_for_timeout(900 if i < len(tokens) - 1 else 3200)
        return used

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
            await page.goto(DASHBOARD_URL, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            if LOGIN_HINT in (page.url or ""):
                out.status = "LOGIN_FAILED"
                out.detail = "SESSION_EXPIRED — please authenticate via MARG SESSION menu"
                out.login_screenshot = await self._screenshot(page, "session-expired")
                return out
            out.login_screenshot = await self._screenshot(page, "dashboard")

            # 1) Navigate: Order → Place Order
            ok = await self._open_place_order(page)
            if not ok:
                out.status = "ERROR"
                out.detail = "Could not open Order → Place Order on MARG"
                out.results_screenshot = await self._screenshot(page, "no-place-order")
                return out
            out.debug["place_order_url"] = page.url

            # 2) Supplier List → + → tick Select All → confirm
            await self._open_supplier_picker_and_select_all(page)
            out.search_screenshot = await self._screenshot(page, "suppliers-all")

            # 3) Type product and wait for results
            used_input = await self._search_product(page, product, quantity or 0)
            if not used_input:
                out.status = "ERROR"
                out.detail = "MARG: product search input not found on Place-Order page"
                out.results_screenshot = await self._screenshot(page, "no-search-input")
                return out
            out.debug["search_selector"] = used_input

            out.results_screenshot = await self._screenshot(page, "results")

            # 4) Parse result rows. MARG shows a per-supplier stock table.
            row_selectors = [
                'table.table tbody tr',
                'table tbody tr',
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
                        rows = vis; used_row_sel = rs; break
                except Exception:
                    continue
            out.debug["row_selector"] = used_row_sel
            out.debug["row_count"] = len(rows)

            if not rows:
                out.status = "NOT_FOUND"
                out.detail = "MARG: no supplier rows returned for query"
                return out

            query_canon = canon(product)
            items: List[ExtractedItem] = []
            for r in rows:
                try:
                    txt = _clean(await r.inner_text()) if await r.inner_text() else ""
                    if not txt:
                        continue
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

                    row_score = score(query_canon, txt)
                    if row_score < ACCEPT_THRESHOLD - 15:
                        continue

                    joined = " | ".join(cell_texts)
                    supplier = cell_texts[0] if cell_texts else None
                    matched_name = cell_texts[1] if len(cell_texts) > 1 else None

                    m_mrp = re.search(r"(?:mrp|m\\.r\\.p\\.?)\\s*[:\\-]?\\s*([₹]?\\s*[\\d,]+(?:\\.\\d+)?)", joined, re.I)
                    m_ptr = re.search(r"(?:ptr|rate|net\\s*rate|price)\\s*[:\\-]?\\s*([₹]?\\s*[\\d,]+(?:\\.\\d+)?)", joined, re.I)
                    m_sch = re.search(r"(?:scheme|offer|disc(?:ount)?)\\s*[:\\-]?\\s*([\\d\\+/\\.\\s%A-Za-z]+?)(?:\\||$)", joined, re.I)
                    m_stk = re.search(r"(?:stock|qty|available)\\s*[:\\-]?\\s*(\\d+)", joined, re.I)
                    m_pk  = re.search(r"(?:pack|packing)\\s*[:\\-]?\\s*([\\w\\-\\.]+)", joined, re.I)

                    items.append(ExtractedItem(
                        product=product,
                        matched_name=matched_name,
                        pack=m_pk.group(1) if m_pk else None,
                        mrp=_extract_money(m_mrp.group(1)) if m_mrp else None,
                        ptr=_extract_money(m_ptr.group(1)) if m_ptr else None,
                        available_qty=m_stk.group(1) if m_stk else None,
                        scheme=_clean(m_sch.group(1)) if m_sch else None,
                        seller=supplier,
                        raw_row=cell_texts or [txt],
                    ))
                except Exception:
                    continue

            if not items:
                out.status = "NOT_FOUND"
                out.detail = "MARG: rows found but no product matches after scoring"
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
