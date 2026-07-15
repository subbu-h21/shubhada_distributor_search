"""CHETHANA / chiragpharma.in portal adapter.

Verified flow with a live account:
  1. GET  http://www.chiragpharma.in                 (login page)
  2. Fill ctl00$txt_username / ctl00$txt_passwd + click image button ctl00$btn_login
  3. On success, land at /AdminDef.aspx (Home). Menu: Home, Order, Overdue, Invoice.
  4. GET  /userr.aspx                                 (Order Feed page)
  5. Type product name INTO #ctl00_ContentPlaceHolder1_txt_pdt_code word-by-word.
     The ASP.NET AJAX AutoCompleteExtender fires POST /userr.aspx/GetAssetList1
     and populates ul#ctl00_ContentPlaceHolder1_AutoCompleteExtender1_completionListElem
     with <li> items formatted as:  "NAME ~CODE ~PACK ~PRICE"
     Example:  "PROLOMET XL 25 MG $ ~758525 ~15 S ~52.17"
  6. Score suggestions using the shared canonicalization; click the best one.
  7. After selection, the form auto-populates:
       #ctl00_ContentPlaceHolder1_txt_pdt_code   -> code       (e.g. 758525)
       #ctl00_ContentPlaceHolder1_txt_descrptn   -> description (e.g. PROLOMET XL 25 MG $)
       #ctl00_ContentPlaceHolder1_Txtmrp         -> MRP        (e.g. 68.47)
       #ctl00_ContentPlaceHolder1_txt_free       -> free/scheme units
       #ctl00_ContentPlaceHolder1_txt_discount   -> discount
  8. Read these fields; capture screenshots.
"""
from __future__ import annotations
import re
from typing import Optional
from .base import BaseAdapter, ExtractionOutcome, ExtractedItem
from .match import canon, score, ACCEPT_THRESHOLD


LOGIN_USER_SEL = "#ctl00_txt_username"
LOGIN_PASS_SEL = "#ctl00_txt_passwd"
LOGIN_SUBMIT_SEL = "#ctl00_btn_login"

ORDER_URL_PATH = "/userr.aspx"

PDT_CODE_SEL = "#ctl00_ContentPlaceHolder1_txt_pdt_code"
DESC_SEL = "#ctl00_ContentPlaceHolder1_txt_descrptn"
MRP_SEL = "#ctl00_ContentPlaceHolder1_Txtmrp"
FREE_SEL = "#ctl00_ContentPlaceHolder1_txt_free"
DISCOUNT_SEL = "#ctl00_ContentPlaceHolder1_txt_discount"
QTY_SEL = "#ctl00_ContentPlaceHolder1_txt_quanty"
TOTAL_SEL = "#ctl00_ContentPlaceHolder1_txt_total"
AUTOCOMPLETE_UL_SEL = "#ctl00_ContentPlaceHolder1_AutoCompleteExtender1_completionListElem"


def _origin(url: str) -> str:
    m = re.match(r"^(https?://[^/]+)", (url or "").strip())
    return m.group(1) if m else url.rstrip("/")


class ChethanaAdapter(BaseAdapter):
    portal_type = "CHETHANA"

    # ---------- Login ----------
    async def _login(self, page, url: str, username: str, password: str) -> bool:
        """Fill the login form. Returns True if we land on AdminDef.aspx."""
        target = _origin(url)
        try:
            await page.goto(target, timeout=60000, wait_until="domcontentloaded")
        except Exception:
            pass
        await page.wait_for_timeout(1500)
        await self._screenshot(page, "login-open")

        # If we're already past the login (session restored), skip
        try:
            user_el = await page.query_selector(LOGIN_USER_SEL)
            if not user_el:
                return "AdminDef.aspx" in (page.url or "") or "userr.aspx" in (page.url or "")
        except Exception:
            pass

        try:
            await page.fill(LOGIN_USER_SEL, username)
            await page.fill(LOGIN_PASS_SEL, password)
        except Exception as e:
            self._last_error = f"fill error: {e}"
            return False

        try:
            await page.click(LOGIN_SUBMIT_SEL)
        except Exception:
            # image button click can fail — try keyboard Enter
            try:
                await page.keyboard.press("Enter")
            except Exception:
                return False

        try:
            await page.wait_for_load_state("domcontentloaded", timeout=20000)
        except Exception:
            pass
        await page.wait_for_timeout(1800)
        await self._screenshot(page, "login-done")

        cur = (page.url or "").lower()
        # Success signals: URL changed away from Home_def.aspx OR menu contains Order
        if "admindef.aspx" in cur or "userr.aspx" in cur:
            return True
        # Some ASP.NET flows leave URL as Home_def.aspx but page shows Home menu
        try:
            body = (await page.inner_text("body"))[:2000].lower()
            if "order" in body and "logout" in body:
                return True
            if "invalid" in body or "wrong" in body or "not registered" in body:
                self._last_error = "invalid credentials"
                return False
        except Exception:
            pass
        return False

    async def test_login(self, page, url: str, username: str, password: str):
        self._last_error = ""
        ok = await self._login(page, url, username, password)
        detail = "Login OK" if ok else (self._last_error or "Login failed (check credentials)")
        return ok, detail

    # ---------- Extract ----------
    async def _open_order_page(self, page, url: str):
        target = _origin(url) + ORDER_URL_PATH
        try:
            await page.goto(target, timeout=60000, wait_until="domcontentloaded")
        except Exception:
            pass
        await page.wait_for_timeout(2500)
        await self._screenshot(page, "order-page")

    async def _type_and_pick(self, page, product: str) -> Optional[str]:
        """Type product word-by-word into pdt_code; return the raw suggestion
        text that was clicked, or None if no acceptable match found."""
        el = await page.query_selector(PDT_CODE_SEL)
        if not el:
            return None
        try:
            await el.click()
        except Exception:
            pass
        try:
            await el.fill("")
        except Exception:
            pass

        raw_tokens = re.findall(r"[a-z0-9]+", product.lower())
        if not raw_tokens:
            return None
        query_canon = canon(product)

        # Type each token with a small delay; wait for AJAX after each
        for i, tok in enumerate(raw_tokens):
            if i > 0:
                try:
                    await page.keyboard.type(" ", delay=60)
                except Exception:
                    pass
            try:
                await page.keyboard.type(tok, delay=90)
            except Exception:
                break
            await page.wait_for_timeout(800 if i < len(raw_tokens) - 1 else 1400)

        await self._screenshot(page, "autocomplete-open")

        # Collect suggestions from the ASP.NET AJAX completion list
        items = await page.query_selector_all(f"{AUTOCOMPLETE_UL_SEL} li")
        candidates = []
        for it in items:
            try:
                txt = ((await it.inner_text()) or "").strip()
                if not txt:
                    continue
                # Format: "NAME ~CODE ~PACK ~PRICE" — take the NAME part for scoring
                name_part = txt.split("~", 1)[0].strip()
                candidates.append((it, txt, name_part))
            except Exception:
                continue

        if not candidates:
            return None

        best_el, best_score, best_txt = None, -1000, None
        for el_i, full_txt, name_part in candidates:
            s = score(query_canon, name_part)
            if s > best_score:
                best_score, best_el, best_txt = s, el_i, full_txt

        # Manual pick override: force-select the candidate whose name matches
        forced = getattr(self, "_force_candidate", None)
        if forced:
            from .match import canon as _c
            f_canon = _c(forced)
            for el_i, full_txt, name_part in candidates:
                if _c(name_part) == f_canon or forced.lower() in name_part.lower():
                    best_el, best_score, best_txt = el_i, 55, full_txt
                    break

        if best_el is None or best_score < ACCEPT_THRESHOLD:
            return None
        try:
            await best_el.click()
        except Exception:
            return None
        return best_txt

    async def _read_selected(self, page):
        """Return dict of populated fields after a suggestion is clicked."""
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(2500)
        try:
            data = await page.evaluate("""() => {
                const g = id => (document.getElementById(id) || {}).value || '';
                return {
                    code:  g('ctl00_ContentPlaceHolder1_txt_pdt_code').trim(),
                    desc:  g('ctl00_ContentPlaceHolder1_txt_descrptn').trim(),
                    mrp:   g('ctl00_ContentPlaceHolder1_Txtmrp').trim(),
                    free:  g('ctl00_ContentPlaceHolder1_txt_free').trim(),
                    disc:  g('ctl00_ContentPlaceHolder1_txt_discount').trim(),
                    total: g('ctl00_ContentPlaceHolder1_txt_total').trim(),
                };
            }""")
            return data
        except Exception:
            return {}

    async def extract(self, page, url: str, username: str, password: str,
                      product: str, quantity: int, distributor_name: str = "",
                      force_candidate_name: Optional[str] = None) -> ExtractionOutcome:
        out = ExtractionOutcome()
        out.requested_qty = quantity or None
        self._force_candidate = force_candidate_name
        try:
            ok = await self._login(page, url, username, password)
            out.login_screenshot = await self._screenshot(page, "post-login")
            if not ok:
                out.status = "LOGIN_FAILED"
                out.detail = getattr(self, "_last_error", None) or "Login failed"
                return out

            await self._open_order_page(page, url)
            out.search_screenshot = await self._screenshot(page, "search-page")

            picked_text = await self._type_and_pick(page, product)
            if not picked_text:
                out.results_screenshot = await self._screenshot(page, "no-match")
                out.status = "NOT_FOUND"
                out.detail = "No matching product in CHETHANA autocomplete"
                return out

            # Fill quantity + press Enter — this triggers the portal's stock-check
            # which paints a colored <tr> next to the row:
            #   rgb(0,128,0)     = GREEN   → Stock Available
            #   rgb(255,255,0)   = YELLOW  → Insufficient Stock
            #   rgb(255,0,0)     = RED     → Stock Unavailable
            # We always fill qty (default 1 if user didn't specify) so the color
            # indicator activates.
            qty_to_fill = quantity if quantity and quantity > 0 else 1
            try:
                q = await page.query_selector(QTY_SEL)
                if q:
                    await q.click()
                    await q.fill(str(qty_to_fill))
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(2500)
            except Exception:
                pass

            # Read the color-coded stock status
            stock_status = await page.evaluate("""() => {
                // Look for a small colored element that is NOT part of the
                // bottom legend (legend uses class 'style65').
                const wanted = [
                    { rgb: 'rgb(0, 128, 0)',   label: 'AVAILABLE' },
                    { rgb: 'rgb(255, 255, 0)', label: 'INSUFFICIENT' },
                    { rgb: 'rgb(255, 0, 0)',   label: 'UNAVAILABLE' },
                ];
                for (const el of document.querySelectorAll('tr, td')) {
                    if (!el.offsetParent) continue;
                    if ((el.className || '').includes('style65')) continue;
                    const bg = window.getComputedStyle(el).backgroundColor;
                    const match = wanted.find(w => w.rgb === bg);
                    if (match) {
                        return { color: bg, label: match.label };
                    }
                }
                return null;
            }""")

            data = await self._read_selected(page)
            # The final screenshot MUST be taken AFTER the color indicator has
            # painted, so the user can visually confirm stock status.
            out.results_screenshot = await self._screenshot(page, "results-with-color")

            stock_label = (stock_status or {}).get("label")
            item = ExtractedItem(
                product=product,
                matched_name=data.get("desc") or picked_text.split("~", 1)[0].strip(),
                pack=(picked_text.split("~")[2].strip() if picked_text.count("~") >= 2 else None),
                mrp=data.get("mrp") or None,
                ptr=None,  # CHETHANA doesn't expose PTR directly on this form
                available_qty=("in-stock" if stock_label == "AVAILABLE" else
                               ("partial" if stock_label == "INSUFFICIENT" else
                                ("0" if stock_label == "UNAVAILABLE" else None))),
                scheme=data.get("free") or None,
                batch=None,
                expiry=None,
                raw_row=[picked_text, f"stockStatus={stock_label}" if stock_label else ""],
            )
            out.items = [item]
            # If stock indicator says UNAVAILABLE, downgrade to NOT_FOUND-with-price
            if stock_label == "UNAVAILABLE":
                out.status = "NOT_FOUND"
                out.detail = f"Stock UNAVAILABLE for {item.matched_name} (MRP {item.mrp})"
                out.can_fulfill = False
            elif stock_label == "INSUFFICIENT":
                out.status = "SUCCESS"
                out.detail = f"Insufficient stock for qty {qty_to_fill} of {item.matched_name}"
                out.can_fulfill = False
            elif stock_label == "AVAILABLE":
                out.status = "SUCCESS"
                out.detail = f"Stock AVAILABLE for {item.matched_name}"
                out.can_fulfill = True
            else:
                out.status = "SUCCESS"
                out.detail = f"Matched: {item.matched_name}"
            out.debug = {"code": data.get("code"), "total": data.get("total"), "stockStatus": stock_label}
            return out
        except Exception as e:
            out.status = "ERROR"
            out.detail = f"{e.__class__.__name__}: {e}"
            try:
                out.results_screenshot = await self._screenshot(page, "error")
            except Exception:
                pass
            return out
