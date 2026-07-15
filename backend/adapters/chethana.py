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
        """Progressive-probe strategy (per user request):
          1. Type first 4 chars → snapshot dropdown + screenshot
          2. Type full query   → snapshot dropdown + screenshot
          3. Merge candidate lists, score, boost items present in BOTH probes
          4. Click the best candidate (re-type if needed to make it visible)
        """
        from .probe import progressive_autocomplete, Candidate

        # Prep the input
        el = await page.query_selector(PDT_CODE_SEL)
        if not el:
            return None
        try: await el.click()
        except Exception: pass
        try: await el.fill("")
        except Exception: pass

        query_canon = canon(product)

        # Row-to-name mapper for CHETHANA: rows are "NAME ~CODE ~PACK ~PTR"
        def _row_to_name(full: str) -> str:
            return full.split("~", 1)[0].strip()

        best, merged, dbg = await progressive_autocomplete(
            page,
            input_selector=PDT_CODE_SEL,
            row_selector=f"{AUTOCOMPLETE_UL_SEL} li",
            query=product,
            query_canon=query_canon,
            row_to_name=_row_to_name,
            screenshotter=self._screenshot,
        )
        self._probe_debug = dbg

        # Manual pick override still wins
        forced = getattr(self, "_force_candidate", None)
        if forced:
            f_canon_raw = canon(forced)
            f_canon = tuple(f_canon_raw) if isinstance(f_canon_raw, (list, tuple)) else (str(f_canon_raw),)
            for c in merged:
                if c.canon == f_canon or forced.lower() in c.name.lower():
                    best = c
                    best.score = max(best.score, 55)
                    break

        if best is None:
            return None

        # We need to click on the row that contains this candidate in the
        # CURRENT dropdown. If it's not visible we retype the query so the
        # portal re-shows the same suggestion set.
        async def _find_row(name_canon: tuple):
            items = await page.query_selector_all(f"{AUTOCOMPLETE_UL_SEL} li")
            for it in items:
                try:
                    if not await it.is_visible(): continue
                    txt = ((await it.inner_text()) or "").strip()
                    if not txt: continue
                    name_part = txt.split("~", 1)[0].strip()
                    c = canon(name_part)
                    ck = tuple(c) if isinstance(c, (list, tuple)) else (str(c),)
                    if ck == name_canon:
                        return it, txt
                except Exception:
                    continue
            return None, None

        row_el, row_txt = await _find_row(best.canon)
        if row_el is None:
            # Re-type the full query so the dropdown reappears
            try: await el.click()
            except Exception: pass
            try: await el.fill("")
            except Exception: pass
            try: await el.type(product, delay=90)
            except Exception:
                try: await page.keyboard.type(product, delay=90)
                except Exception: pass
            await page.wait_for_timeout(1400)
            row_el, row_txt = await _find_row(best.canon)

        if row_el is None:
            return None

        try:
            await row_el.click()
        except Exception:
            return None

        return row_txt or best.full_text

    async def _read_selected(self, page):
        """Return dict of populated fields after a suggestion is clicked and
        quantity has been entered. Reads from the committed table row (not the
        top-level "scratch-pad" inputs which get cleared after commit)."""
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(2500)
        try:
            data = await page.evaluate(r"""() => {
                const g = id => (document.getElementById(id) || {}).value || '';
                // Try the top-level scratch pad first (may be pre-commit)
                const pad = {
                    code:  g('ctl00_ContentPlaceHolder1_txt_pdt_code').trim(),
                    desc:  g('ctl00_ContentPlaceHolder1_txt_descrptn').trim(),
                    mrp:   g('ctl00_ContentPlaceHolder1_Txtmrp').trim(),
                    free:  g('ctl00_ContentPlaceHolder1_txt_free').trim(),
                    disc:  g('ctl00_ContentPlaceHolder1_txt_discount').trim(),
                    total: g('ctl00_ContentPlaceHolder1_txt_total').trim(),
                };
                // Now try the committed row inside the products table (data row
                // with a Code + Description + Qty). Any <tr> with 6+ cells and
                // a numeric code in first cell (or the second row after headers).
                const rows = document.querySelectorAll('table tr');
                let row = null;
                for (const r of rows) {
                    const cells = r.querySelectorAll('td');
                    if (cells.length < 6) continue;
                    const cellTxt = (idx) => {
                        const c = cells[idx];
                        if (!c) return '';
                        // Prefer <input> value, fall back to text
                        const inp = c.querySelector('input, textarea');
                        if (inp && (inp.value || '') !== '') return (inp.value || '').trim();
                        return (c.innerText || c.textContent || '').trim();
                    };
                    const code = cellTxt(0);
                    const desc = cellTxt(1);
                    if (!code || !desc) continue;
                    if (!/^\d+$/.test(code)) continue;
                    // description should contain some letters
                    if (!/[A-Za-z]/.test(desc)) continue;
                    row = {
                        code, desc,
                        qty:    cellTxt(2),
                        free:   cellTxt(3),
                        mrp:    cellTxt(4),
                        disc:   cellTxt(5),
                        amount: cellTxt(6) || '',
                    };
                    break;
                }
                // Merge — prefer row values when present, fall back to pad.
                const merged = { ...pad };
                if (row) {
                    if (row.code) merged.code = row.code;
                    if (row.desc) merged.desc = row.desc;
                    if (row.mrp)  merged.mrp  = row.mrp;
                    if (row.free) merged.free = row.free;
                    if (row.disc) merged.disc = row.disc;
                    if (row.qty)  merged.qty  = row.qty;
                    if (row.amount) merged.amount = row.amount;
                }
                return merged;
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
            # Surface progressive-probe debug + screenshots to the UI
            probe_dbg = getattr(self, "_probe_debug", None) or {}
            if probe_dbg:
                out.debug["probe"] = {
                    "prefix_row_count": probe_dbg.get("prefix_row_count"),
                    "full_row_count":   probe_dbg.get("full_row_count"),
                    "prefix_top":       probe_dbg.get("prefix_top"),
                    "full_top":         probe_dbg.get("full_top"),
                    "merged":           probe_dbg.get("merged"),
                }
                if probe_dbg.get("prefix_screenshot"):
                    out.search_screenshot = probe_dbg["prefix_screenshot"]
                if probe_dbg.get("full_screenshot"):
                    # Use the full-typed screenshot as the primary "search" one
                    out.debug["autocomplete_full_screenshot"] = probe_dbg["full_screenshot"]
            if not picked_text:
                out.results_screenshot = await self._screenshot(page, "no-match")
                out.status = "NOT_FOUND"
                out.detail = "No matching product in CHETHANA autocomplete"
                return out

            # After picking a suggestion, the CHETHANA form fires a POSTBACK
            # which re-renders the page. If we immediately run page.evaluate
            # we can hit "Execution context was destroyed". Wait for the
            # network to settle before touching the DOM again.
            try:
                await page.wait_for_load_state("networkidle", timeout=12000)
            except Exception:
                pass
            await page.wait_for_timeout(600)

            # Fill quantity + wait for stock-color paint.
            # Prior iterations tried Enter (postback wiped value) and Tab (didn't
            # trigger portal's stock check). Now: directly SET value via JS +
            # dispatch input/change/keyup/blur events. Then poll for the colored
            # <tr> for up to 5 seconds. Retry the whole block up to 3× if the
            # context is destroyed by another postback in-flight.
            qty_to_fill = quantity if quantity and quantity > 0 else 1
            self._last_error = ""
            filled_ok = False
            for attempt in range(3):
                try:
                    # Ensure the qty input is visible + not disabled
                    await page.wait_for_function(
                        f"() => {{ const e=document.getElementById('{QTY_SEL[1:]}'); return e && !e.disabled && e.offsetParent!==null; }}",
                        timeout=8000,
                    )
                    await page.evaluate(f"""(v) => {{
                        const el = document.getElementById('{QTY_SEL[1:]}');
                        if (!el) return 'no-elem';
                        el.focus();
                        el.value = v;
                        ['input','change','keyup','blur'].forEach(t =>
                            el.dispatchEvent(new Event(t, {{ bubbles: true }}))
                        );
                        return el.value;
                    }}""", str(qty_to_fill))
                    filled_ok = True
                    break
                except Exception as e:
                    msg = str(e)
                    self._last_error = f"qty JS-fill attempt {attempt+1}: {e}"
                    if "Execution context was destroyed" in msg or "navigation" in msg.lower():
                        # A postback destroyed our context — wait for the next
                        # network-idle and retry.
                        try:
                            await page.wait_for_load_state("networkidle", timeout=8000)
                        except Exception:
                            pass
                        await page.wait_for_timeout(800)
                        continue
                    break

            # Poll up to 5s for the colored status row to appear
            stock_status = None
            for _ in range(10):
                await page.wait_for_timeout(500)
                try:
                    stock_status = await page.evaluate("""() => {
                        const wanted = [
                            { rgb: 'rgb(0, 128, 0)',   label: 'AVAILABLE' },
                            { rgb: 'rgb(255, 255, 0)', label: 'INSUFFICIENT' },
                            { rgb: 'rgb(255, 0, 0)',   label: 'UNAVAILABLE' },
                        ];
                        for (const el of document.querySelectorAll('tr, td')) {
                            if (!el.offsetParent) continue;
                            if ((el.className || '').includes('style65')) continue;
                            const bg = window.getComputedStyle(el).backgroundColor;
                            const m = wanted.find(w => w.rgb === bg);
                            if (m) return { color: bg, label: m.label };
                        }
                        return null;
                    }""")
                except Exception as e:
                    # Context destroyed by another postback; wait and continue polling
                    if "Execution context was destroyed" in str(e) or "navigation" in str(e).lower():
                        try:
                            await page.wait_for_load_state("networkidle", timeout=5000)
                        except Exception:
                            pass
                        continue
                    stock_status = None
                if stock_status:
                    break

            data = await self._read_selected(page)
            # The final screenshot MUST be taken AFTER the color indicator has
            # painted, so the user can visually confirm stock status.
            out.results_screenshot = await self._screenshot(page, "results-with-color")

            stock_label = (stock_status or {}).get("label")
            # Parse the picked_text (~-separated: name ~ code ~ pack ~ ptr) —
            # the last field is the PTR (net rate per unit) that the autocomplete
            # surfaced.
            parts = [p.strip() for p in (picked_text or "").split("~")]
            pack_from_pick = parts[2] if len(parts) > 2 else None
            ptr_from_pick = None
            if len(parts) > 3:
                m = re.search(r"\d+(?:\.\d+)?", parts[3])
                if m:
                    ptr_from_pick = m.group(0)

            # PTR fallback: derive from committed row (amount / qty)
            row_qty = (data.get("qty") or "").strip()
            row_amount = (data.get("amount") or "").strip()
            ptr_from_row = None
            try:
                if row_qty and row_amount and row_qty.isdigit() and float(row_qty) > 0:
                    ptr_from_row = f"{float(row_amount) / float(row_qty):.2f}"
            except Exception:
                pass

            item = ExtractedItem(
                product=product,
                matched_name=data.get("desc") or picked_text.split("~", 1)[0].strip(),
                pack=pack_from_pick,
                mrp=data.get("mrp") or None,
                ptr=ptr_from_pick or ptr_from_row,
                available_qty=("in-stock" if stock_label == "AVAILABLE" else
                               ("partial" if stock_label == "INSUFFICIENT" else
                                ("0" if stock_label == "UNAVAILABLE" else None))),
                scheme=data.get("free") or None,
                batch=None,
                expiry=None,
                raw_row=[picked_text, f"stockStatus={stock_label}" if stock_label else "", f"amount={row_amount}", f"qty={row_qty}"],
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
            out.debug.update({"code": data.get("code"), "total": data.get("total"), "stockStatus": stock_label})
            return out
        except Exception as e:
            out.status = "ERROR"
            out.detail = f"{e.__class__.__name__}: {e}"
            try:
                out.results_screenshot = await self._screenshot(page, "error")
            except Exception:
                pass
            return out
