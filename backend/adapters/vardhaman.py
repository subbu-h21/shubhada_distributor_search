"""VARDHAMAN / easysol WebOrder portal adapter.

Verified live flow:
  1. GET http://easysol.co.in/WebOrderRedirect/  (login form)
  2. Fill #txtuser + #txtpass + click #btn_login → redirects to
     http://fgtsmg.fortiddns.com:83/OnlineOrder/ItemOrder.aspx (SMG branch).
  3. Type product name char-by-char into
     #ctl00_ContentPlaceHolder1_txt_name  (placeholder: "Enter Item Name").
  4. After each keystroke the page fires
     POST /OnlineOrder/ItemOrder.aspx/GetItems
     which returns a JSON envelope like:
       {"d":["2018689|PROLOMET XL 25MG TAB|15`S|Avl|\u00a0|219063|2872"]}
     Fields (pipe-separated) per item:
        [0] internalId
        [1] product name
        [2] pack
        [3] STOCK STATUS ("Avl" = available, empty/na = not available)
        [4] scheme (may be &nbsp;)
        [5] item code
        [6] rate / MRP
     The suggestion list is rendered inside div.AutoExtendercompletionList
     (a table with Name|Pack|Bal|Scheme columns).
  5. Score using shared canonical matcher, click the best-matching row.
  6. Fill #txt_qty with the requested quantity, press Tab. Read the populated
     read-only fields (txt_pack, txt_Mrp, txt_balqty).
  7. Take the final screenshot showing the "Avl" indicator.
"""
from __future__ import annotations
import re
import json
from typing import List, Optional
from .base import BaseAdapter, ExtractionOutcome, ExtractedItem
from .match import canon, score, ACCEPT_THRESHOLD


LOGIN_URL = "http://easysol.co.in/WebOrderRedirect/"
LOGIN_USER = "#txtuser"
LOGIN_PASS = "#txtpass"
LOGIN_SUBMIT = "#btn_login"

ITEM_NAME_SEL = "#ctl00_ContentPlaceHolder1_txt_name"
QTY_SEL = "#txt_qty"
PACK_SEL = "#ctl00_ContentPlaceHolder1_txt_pack"
MRP_SEL = "#ctl00_ContentPlaceHolder1_txt_Mrp"
BALQTY_SEL = "#ctl00_ContentPlaceHolder1_txt_balqty"
SCHM_SEL = "#ctl00_ContentPlaceHolder1_txt_Schm"
RS_SEL = "#ctl00_ContentPlaceHolder1_txt_Rs"
AUTOCOMPLETE_LIST = ".AutoExtendercompletionList"


class VardhamanAdapter(BaseAdapter):
    portal_type = "VARDHAMAN"

    async def _login(self, page, url: str, username: str, password: str) -> bool:
        try:
            await page.goto(LOGIN_URL, timeout=45000, wait_until="domcontentloaded")
        except Exception:
            pass
        await page.wait_for_timeout(1500)
        # Skip login form if we're already inside
        if "ItemOrder.aspx" in (page.url or ""):
            return True
        try:
            await page.fill(LOGIN_USER, username)
            await page.fill(LOGIN_PASS, password)
            await page.click(LOGIN_SUBMIT)
        except Exception as e:
            self._last_error = f"login fill/click: {e}"
            return False
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=25000)
        except Exception:
            pass
        await page.wait_for_timeout(3500)
        return "ItemOrder.aspx" in (page.url or "")

    async def test_login(self, page, url: str, username: str, password: str):
        self._last_error = ""
        ok = await self._login(page, url, username, password)
        return ok, ("Login OK" if ok else (self._last_error or "Login failed"))

    def _parse_items(self, json_body: str) -> List[dict]:
        """Turn the /GetItems JSON envelope into a list of dicts."""
        try:
            j = json.loads(json_body)
        except Exception:
            return []
        rows = j.get("d") or []
        out = []
        for r in rows:
            parts = str(r).split("|")
            if len(parts) < 3:
                continue
            out.append({
                "internal_id": parts[0].strip(),
                "name": parts[1].strip(),
                "pack": parts[2].strip() if len(parts) > 2 else "",
                "status": parts[3].strip() if len(parts) > 3 else "",
                "scheme": (parts[4].strip() if len(parts) > 4 else "").replace("&nbsp;", "").strip(),
                "code": parts[5].strip() if len(parts) > 5 else "",
                "rate": parts[6].strip() if len(parts) > 6 else "",
            })
        return out

    async def extract(self, page, url: str, username: str, password: str,
                      product: str, quantity: int, distributor_name: str = "",
                      force_candidate_name: Optional[str] = None) -> ExtractionOutcome:
        out = ExtractionOutcome(requested_qty=quantity)
        self._force_candidate = force_candidate_name

        # Intercept /GetItems responses so we can parse the raw JSON — that's
        # more reliable than DOM scraping of the autocomplete list.
        captured_items: List[dict] = []
        async def _on_response(resp):
            try:
                if "/GetItems" in resp.url and resp.status == 200:
                    body = await resp.text()
                    parsed = self._parse_items(body)
                    if parsed:
                        # Keep a running set of unique candidates (by name)
                        seen = {i["name"] for i in captured_items}
                        for p in parsed:
                            if p["name"] not in seen:
                                captured_items.append(p)
                                seen.add(p["name"])
            except Exception:
                pass
        page.on("response", lambda r: _on_response(r))

        try:
            ok = await self._login(page, url, username, password)
            out.login_screenshot = await self._screenshot(page, "post-login")
            if not ok:
                out.status = "LOGIN_FAILED"
                out.detail = getattr(self, "_last_error", None) or "Login failed"
                return out

            out.search_screenshot = await self._screenshot(page, "item-order-page")

            # Type the product name char-by-char (each keystroke fires GetItems)
            el = await page.query_selector(ITEM_NAME_SEL)
            if not el:
                out.status = "ERROR"
                out.detail = "Item name input not found"
                return out
            try:
                await el.click()
                await el.fill("")
            except Exception:
                pass

            raw_tokens = re.findall(r"[a-z0-9]+", product.lower())
            if not raw_tokens:
                out.status = "NOT_FOUND"
                out.detail = "Empty product query"
                return out
            query_canon = canon(product)

            # Multi-stage progressive typing (like SUNSHOP)
            first = raw_tokens[0]
            stages = [first[:min(4, len(first))]]
            if len(first) > 4:
                stages.append(first)
            if len(raw_tokens) >= 2:
                stages.append(f"{first} {raw_tokens[1]}")
            if len(raw_tokens) >= 3:
                stages.append(" ".join(raw_tokens))
            # De-dupe
            seen_s: set = set()
            stages = [s for s in stages if not (s in seen_s or seen_s.add(s))]

            stage_shots: List[str] = []
            for si, s in enumerate(stages):
                try:
                    await el.click()
                    await el.fill("")
                except Exception:
                    pass
                try:
                    await page.keyboard.type(s, delay=90)
                except Exception:
                    break
                await page.wait_for_timeout(1400 if si == 0 else 1100)
                shot = await self._screenshot(page, f"search-stage{si + 1}-{s.replace(' ', '_')[:20]}")
                if shot:
                    stage_shots.append(shot)

            # Score all captured items
            best = None
            best_score = -1000
            for it in captured_items:
                s = score(query_canon, it["name"])
                if s > best_score:
                    best_score = s
                    best = it

            # Manual pick override
            if force_candidate_name:
                for it in captured_items:
                    if canon(it["name"]) == canon(force_candidate_name) or force_candidate_name.lower() in it["name"].lower():
                        best = it
                        best_score = 55
                        break

            self._last_candidate_names = [it["name"] for it in captured_items[:30]]
            out.debug["stageScreenshots"] = stage_shots
            out.debug["candidates"] = self._last_candidate_names

            if not best or best_score < ACCEPT_THRESHOLD:
                out.status = "NOT_FOUND"
                if captured_items:
                    out.detail = f"No exact match. Distributor stocks: {', '.join(self._last_candidate_names[:5])}"
                else:
                    out.detail = "No autocomplete suggestions returned"
                out.results_screenshot = await self._screenshot(page, "no-match")
                return out

            # Click the matching row in the autocomplete list
            picked_name = best["name"]
            try:
                # Retype the last stage to make sure list is visible with our target
                await el.click()
                await el.fill("")
                # Use a prefix that will surface our target
                short = re.findall(r"[a-z0-9]+", picked_name.lower())[0][:6]
                await page.keyboard.type(short, delay=80)
                await page.wait_for_timeout(1500)
                # Find and click the row containing our picked name
                clicked = await page.evaluate("""(name) => {
                    const list = document.querySelector('.AutoExtendercompletionList');
                    if (!list) return false;
                    const rows = list.querySelectorAll('tr, li, div.item, div.result');
                    for (const r of rows) {
                        const t = (r.innerText || '').toUpperCase();
                        if (t.includes(name.toUpperCase().split(' ').slice(0, 2).join(' '))) {
                            r.click();
                            return true;
                        }
                    }
                    return false;
                }""", picked_name)
                if not clicked:
                    # Try selecting via keyboard: ArrowDown + Enter
                    await page.keyboard.press("ArrowDown")
                    await page.wait_for_timeout(200)
                    await page.keyboard.press("Enter")
                await page.wait_for_timeout(2500)
            except Exception:
                pass

            # Read populated fields
            details = await page.evaluate("""() => {
                const g = id => (document.getElementById(id) || {}).value || '';
                return {
                    pack: g('ctl00_ContentPlaceHolder1_txt_pack').trim(),
                    mrp:  g('ctl00_ContentPlaceHolder1_txt_Mrp').trim(),
                    bal:  g('ctl00_ContentPlaceHolder1_txt_balqty').trim(),
                    schm: g('ctl00_ContentPlaceHolder1_txt_Schm').trim(),
                    rs:   g('ctl00_ContentPlaceHolder1_txt_Rs').trim(),
                    hscm: g('ctl00_ContentPlaceHolder1_txt_HScm').trim(),
                };
            }""")

            # Fill quantity if given
            qty_to_fill = quantity if quantity and quantity > 0 else 1
            try:
                q = await page.query_selector(QTY_SEL)
                if q:
                    await q.click()
                    await q.fill(str(qty_to_fill))
                    await page.keyboard.press("Tab")
                    await page.wait_for_timeout(1500)
            except Exception:
                pass

            out.results_screenshot = await self._screenshot(page, "results-with-avl")

            # Determine availability from the AVL string on the autocomplete row
            avl = (best.get("status") or "").strip().lower()
            is_available = avl == "avl"

            item = ExtractedItem(
                product=product,
                matched_name=picked_name,
                pack=details.get("pack") or best.get("pack"),
                mrp=details.get("mrp") or best.get("rate"),
                ptr=details.get("rs") or None,
                available_qty=(details.get("bal") or ("in-stock" if is_available else "0")),
                scheme=(details.get("schm") or best.get("scheme")) or None,
                batch=None,
                expiry=None,
                raw_row=[best.get("internal_id"), best.get("code"), best.get("status")],
            )
            out.items = [item]
            out.debug.update({
                "code": best.get("code"),
                "internalId": best.get("internal_id"),
                "avl": best.get("status"),
            })
            if is_available:
                out.status = "SUCCESS"
                out.detail = f"AVL — Available. {picked_name}"
                out.can_fulfill = True
            elif avl in ("", "&nbsp;", "na", "n/a"):
                out.status = "NOT_FOUND"
                out.detail = f"Not available at VARDHAMAN ({picked_name})"
                out.can_fulfill = False
            else:
                out.status = "SUCCESS"
                out.detail = f"Status: {best.get('status')} — {picked_name}"
            return out
        except Exception as e:
            out.status = "ERROR"
            out.detail = f"{e.__class__.__name__}: {e}"
            try: out.results_screenshot = await self._screenshot(page, "error")
            except Exception: pass
            return out
