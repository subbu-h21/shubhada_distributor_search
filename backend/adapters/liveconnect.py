"""LIVECONNECT aggregator adapter.

Uses the "Search with all sellers" feature on https://www.liveconnect.in to
query all 8+ affiliated distributors (A.K. Pharma, Mahaveer, Venkatesha,
Janatha, Kaveri, Sai Radha, Patel, Ferns, …) in a single call.

Verified flow (with a live session cookie):
  1. Navigate to /orderbook/order-book (cookies already contain session)
  2. Type product name word-by-word into #item-search
  3. Wait for `tr.ui-menu-item` autocomplete rows to populate
  4. Score each row using shared canonicalization; click the best match
  5. Server fires POST /orderbook/getitemsforqtyanddist which returns HTML
     containing one `.dist-list` block per seller with:
        - `.qtydistname`  -> "Seller Name - Buyer Name"
        - `.cardvalues p` -> "Manufacturer - <span>Product</span>"
        - value cells (in order): Pack, Qty(input), Scheme, MRP, Rate/PTR,
          Stock, Tax%
     PTR is also embedded as `data-ptr` on the qty input.
  6. Read each block and emit one ExtractedItem per seller.

Requires: a valid session in `db.liveconnect_session` (see
liveconnect_session.py). If cookies are missing/expired, the adapter returns
status LOGIN_FAILED with detail "SESSION_EXPIRED" so the frontend can prompt
re-verification.
"""
from __future__ import annotations
import re
from typing import List, Optional
from bs4 import BeautifulSoup
from .base import BaseAdapter, ExtractionOutcome, ExtractedItem
from .match import canon, score, ACCEPT_THRESHOLD


LOGIN_URL = "https://www.liveconnect.in/site/login"
ORDER_URL = "https://www.liveconnect.in/orderbook/order-book"
SEARCH_INPUT = "#item-search"
SUGGESTION_ROW = "tr.ui-menu-item"


def _clean(txt: str) -> str:
    return re.sub(r"\s+", " ", (txt or "").strip())


class LiveconnectAdapter(BaseAdapter):
    portal_type = "LIVECONNECT"

    def __init__(self, cookies: Optional[list] = None, screenshotter=None):
        super().__init__(screenshotter=screenshotter)
        self.cookies = cookies or []
        self._captured_html: Optional[str] = None

    # ---------- Login (no-op — cookies handled at browser context) ----------
    async def test_login(self, page, url: str, username: str, password: str):
        # For LIVECONNECT the session is managed globally via cookies.
        try:
            await page.goto(ORDER_URL, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            if "/site/login" in (page.url or ""):
                return False, "SESSION_EXPIRED — re-authenticate via LIVECONNECT SESSION menu"
            return True, "Session OK"
        except Exception as e:
            return False, f"{e.__class__.__name__}: {e}"

    async def _apply_cookies(self, page):
        """Add cookies to the browser context (called from extract())."""
        if self.cookies:
            try:
                await page.context.add_cookies(self.cookies)
            except Exception:
                pass

    # ---------- Extract ----------
    async def extract(self, page, url: str, username: str, password: str,
                      product: str, quantity: int, distributor_name: str = "") -> ExtractionOutcome:
        out = ExtractionOutcome()
        out.requested_qty = quantity or None

        if not self.cookies:
            out.status = "LOGIN_FAILED"
            out.detail = "SESSION_EXPIRED — please re-authenticate via LIVECONNECT SESSION menu"
            return out

        await self._apply_cookies(page)

        try:
            await page.goto(ORDER_URL, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3500)

            if "/site/login" in (page.url or ""):
                out.status = "LOGIN_FAILED"
                out.detail = "SESSION_EXPIRED — please re-authenticate via LIVECONNECT SESSION menu"
                out.login_screenshot = await self._screenshot(page, "session-expired")
                return out
            out.login_screenshot = await self._screenshot(page, "logged-in")

            # Capture the POST /getitemsforqtyanddist HTML response
            captured = {"html": None}
            async def _on_response(resp):
                try:
                    if "getitemsforqtyanddist" in resp.url and resp.status == 200:
                        captured["html"] = await resp.text()
                except Exception:
                    pass
            page.on("response", lambda r: _on_response(r))

            # Type product word-by-word into the search input
            el = await page.query_selector(SEARCH_INPUT)
            if not el:
                out.status = "ERROR"
                out.detail = "Search input not found on page"
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

            for i, tok in enumerate(raw_tokens):
                if i > 0:
                    try: await page.keyboard.type(" ", delay=60)
                    except Exception: pass
                try:
                    await page.keyboard.type(tok, delay=90)
                except Exception:
                    break
                await page.wait_for_timeout(900 if i < len(raw_tokens) - 1 else 2200)

            out.search_screenshot = await self._screenshot(page, "autocomplete-open")

            # Collect autocomplete rows — first <td> in each row is the product name
            rows = await page.query_selector_all(SUGGESTION_ROW)
            candidates = []
            for r in rows:
                try:
                    name_td = await r.query_selector("td:nth-child(1)")
                    name_col = _clean(await name_td.text_content()) if name_td else ""
                    if not name_col:
                        continue
                    full = _clean(await r.text_content()) or name_col
                    candidates.append((r, full, name_col))
                except Exception:
                    continue

            if not candidates:
                out.status = "NOT_FOUND"
                out.detail = "No autocomplete suggestions returned by LIVECONNECT"
                out.results_screenshot = await self._screenshot(page, "no-suggestions")
                return out

            best_el, best_score, best_txt = None, -1000, None
            for r, full, name in candidates:
                s = score(query_canon, name)
                if s > best_score:
                    best_score, best_el, best_txt = s, r, full
            out.debug["candidates"] = [{"name": n, "score": score(query_canon, n)} for _, _, n in candidates[:10]]
            out.debug["query_canon"] = query_canon

            if best_el is None or best_score < ACCEPT_THRESHOLD:
                out.status = "NOT_FOUND"
                out.detail = f"No matching product variant in LIVECONNECT (best score {best_score})"
                out.results_screenshot = await self._screenshot(page, "no-match")
                return out

            try:
                await best_el.click()
            except Exception as e:
                out.status = "ERROR"
                out.detail = f"Click failed: {e}"
                return out

            # Wait for the seller table to populate
            try:
                await page.wait_for_selector(".dist-list", timeout=25000)
            except Exception:
                pass
            await page.wait_for_timeout(2500)
            out.results_screenshot = await self._screenshot(page, "all-sellers-result")

            # Prefer the captured XHR HTML; fallback to reading from DOM
            html = captured.get("html")
            if html and '"result"' in html:
                # It's a JSON envelope with escaped HTML in .result
                import json
                try:
                    j = json.loads(html)
                    seller_html = j.get("result") or ""
                except Exception:
                    seller_html = html
            else:
                seller_html = html or (await page.content())

            items = self._parse_sellers(seller_html, product)
            if not items:
                out.status = "NOT_FOUND"
                out.detail = "Product matched but no seller data returned"
                return out

            out.items = items
            out.status = "SUCCESS"
            in_stock = sum(1 for it in items if (it.available_qty or "").isdigit() and int(it.available_qty) > 0)
            out.detail = f"{len(items)} seller(s), {in_stock} in stock"
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

    # ---------- HTML parsing ----------
    def _parse_sellers(self, html: str, product_query: str) -> List[ExtractedItem]:
        """Parse the .dist-list blocks and return one ExtractedItem per seller."""
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        items: List[ExtractedItem] = []
        for block in soup.select(".dist-list"):
            try:
                # Seller name is in .qtydistname (before " - ")
                qname = block.select_one(".qtydistname")
                seller = ""
                if qname:
                    parts = qname.get_text(" ", strip=True).split(" - ")
                    seller = parts[0].strip() if parts else ""

                # First .cardvalues p contains "Mfr - Product"
                mfr = ""
                matched_name = ""
                first_p = block.select_one(".cardvalues p")
                if first_p:
                    txt = first_p.get_text(" ", strip=True)
                    if " - " in txt:
                        mfr, matched_name = txt.split(" - ", 1)
                        mfr, matched_name = mfr.strip(), matched_name.strip()
                    else:
                        matched_name = txt

                # The value cells follow the label cells (Pack, Qty, Scheme, MRP, Rate, Stock, Tax%)
                # Structure: labels row then values row inside the block.
                # Simpler: pick the .cardvalues cells excluding the first (name) p element.
                values = block.select(".cardvalues")
                # Skip the first .cardvalues (contains the name p) and gather text of the rest
                cell_texts: List[str] = []
                # The labels are inside `.card-label`; values inside `.cardvalues` immediately after.
                # We rely on document order: labels come before values.
                labels = [_clean(el.get_text()) for el in block.select(".card-label")]
                value_cells = [el for el in block.select(".cardvalues") if not el.select_one("p") or (el is not first_p)]
                # value_cells still includes the first_p container; filter more precisely by taking
                # every .cardvalues that appears AFTER the labels row
                # Simpler heuristic: pick the .cardvalues cells that have no <p> matching mfr pattern
                clean_values = []
                for v in value_cells:
                    txt = v.get_text(" ", strip=True)
                    # Skip the header-ish cardvalues that contain " - " (mfr line) or a qty input
                    inp = v.select_one("input.qtyinput, input.qty")
                    if inp is not None:
                        clean_values.append(("qty", inp))
                        continue
                    if " - " in txt and v.select_one("span"):
                        continue  # This is the manufacturer/product header row
                    clean_values.append(("text", txt))

                # Map labels -> values by index (skip the qty input which stands where labels[1]=Qty is)
                # Expected label order: ['Pack','Qty','Scheme','MRP','Rate','Stock','Tax%']
                pack = mrp = ptr = stock = scheme = tax = None
                idx = 0
                for lbl in labels:
                    if idx >= len(clean_values):
                        break
                    kind, val = clean_values[idx]
                    label = lbl.strip().lower().rstrip("%").strip()
                    if kind == "qty":
                        # Extract data-* attrs from the qty input
                        idx += 1
                        continue
                    if label == "pack":
                        pack = val
                    elif label == "scheme":
                        scheme = val
                    elif label == "mrp":
                        mrp = val
                    elif label in ("rate", "ptr"):
                        ptr = val
                    elif label == "stock":
                        stock = val
                    elif label in ("tax", "tax%"):
                        tax = val
                    idx += 1

                # Also read data-ptr / data-discount from the qty input, if present
                qty_input = block.select_one("input.qtyinput, input.qty")
                if qty_input:
                    if not ptr:
                        ptr = qty_input.get("data-ptr")
                    scheme_from_data = qty_input.get("data-discount")
                    if scheme_from_data and not scheme:
                        scheme = f"{scheme_from_data}% off"

                items.append(ExtractedItem(
                    product=product_query,
                    matched_name=matched_name or None,
                    pack=pack,
                    mrp=mrp,
                    ptr=ptr,
                    available_qty=stock,
                    scheme=scheme,
                    manufacturer=mfr or None,
                    seller=seller or None,
                    raw_row=[seller] + (labels or []) + [v for _, v in [(k, w) for k, w in clean_values if k == "text"]],
                ))
                # Store the seller name in raw_row[0] for now (we don't have a dedicated field)
            except Exception:
                continue
        return items
