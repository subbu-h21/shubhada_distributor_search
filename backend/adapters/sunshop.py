"""SUNSHOP portal adapter.

Flow (verified with a live account):
  1. Navigate to https://www.sunshop.co.in
  2. Click "Medical Login" -> opens the actual login page
  3. Fill username + password + submit
  4. On dashboard, open BILLING dropdown -> click "Order" (2nd item)
  5. On the Order page, find the row for our distributor (SAROJ PHARMA etc.)
  6. Click the "Order Feed" link/button on that row
  7. Search for the product name (heuristic search-input selectors)
  8. Read the results table (MRP / PTR / Qty / Scheme / Batch / Expiry)
  9. Capture screenshots at each stage
"""
from __future__ import annotations
import re
from typing import List, Optional
from .base import BaseAdapter, ExtractionOutcome, ExtractedItem


SEARCH_INPUT_SELECTORS = [
    'input[name="product" i]',
    'input[name="productname" i]',
    'input[name="search" i]',
    'input[name="q" i]',
    'input[placeholder*="product" i]',
    'input[placeholder*="search" i]',
    'input[placeholder*="item" i]',
    'input[type="search"]',
    'input.search',
    '#search',
    '#product',
    '#txtSearch',
    '#txtProduct',
    '#txtProductName',
    'input.form-control:visible',
]

QTY_INPUT_SELECTORS = [
    'input[name="qty" i]',
    'input[name="quantity" i]',
    'input[placeholder*="qty" i]',
    'input[placeholder*="quantity" i]',
    '#txtQty',
    '#qty',
]

SEARCH_SUBMIT_SELECTORS = [
    'button:has-text("Search")',
    'input[value*="Search" i]',
    'button:has-text("Go")',
    'button:has-text("Add")',
    '.btn-search',
    '#btnSearch',
    'button[type="submit"]',
    'input[type="submit"]',
]

COLUMN_ALIASES = {
    "product": ["product", "productname", "name", "item", "itemname", "description"],
    "pack": ["pack", "packing", "size"],
    "mrp": ["mrp"],
    "ptr": ["ptr", "rate", "price", "net", "nrv"],
    "available_qty": ["stock", "qty", "quantity", "available", "avl", "instock"],
    "scheme": ["scheme", "offer", "free"],
    "batch": ["batch", "batchno", "batchnumber"],
    "expiry": ["exp", "expiry", "expdate"],
    "manufacturer": ["company", "mfr", "manufacturer", "brand", "mfg"],
}


def _match_col(header: str) -> Optional[str]:
    h = re.sub(r"[^a-z0-9]", " ", header.lower()).strip()
    h_squeezed = h.replace(" ", "")
    for key, aliases in COLUMN_ALIASES.items():
        for a in aliases:
            if a in h or a in h_squeezed:
                return key
    return None


async def _extract_table_data(page) -> List[ExtractedItem]:
    """Find the largest visible table and parse rows heuristically."""
    tables = await page.query_selector_all("table")
    best = None
    best_rows = 0
    for t in tables:
        try:
            rows = await t.query_selector_all("tr")
            if len(rows) > best_rows:
                best_rows = len(rows)
                best = t
        except Exception:
            continue
    if not best or best_rows < 2:
        return []

    rows = await best.query_selector_all("tr")

    # Determine header row (prefer <th>; else first <td> row)
    header_cells: List[str] = []
    header_row_idx = 0
    for idx, r in enumerate(rows[:3]):
        ths = await r.query_selector_all("th")
        if ths:
            header_cells = [(await c.inner_text()).strip() for c in ths]
            header_row_idx = idx
            break
    if not header_cells:
        first = rows[0]
        tds = await first.query_selector_all("td")
        header_cells = [(await c.inner_text()).strip() for c in tds]

    col_map = {i: _match_col(h) for i, h in enumerate(header_cells)}

    items: List[ExtractedItem] = []
    for r in rows[header_row_idx + 1:]:
        tds = await r.query_selector_all("td")
        if not tds:
            continue
        cells = []
        for c in tds:
            try:
                cells.append((await c.inner_text()).strip())
            except Exception:
                cells.append("")
        if not any(cells):
            continue
        item = ExtractedItem(product="", raw_row=cells)
        for i, val in enumerate(cells):
            key = col_map.get(i)
            if not key:
                continue
            if key == "product":
                item.matched_name = val
            elif key == "pack":
                item.pack = val
            elif key == "mrp":
                item.mrp = val
            elif key == "ptr":
                item.ptr = val
            elif key == "available_qty":
                item.available_qty = val
            elif key == "scheme":
                item.scheme = val
            elif key == "batch":
                item.batch = val
            elif key == "expiry":
                item.expiry = val
            elif key == "manufacturer":
                item.manufacturer = val
        if not item.matched_name and cells:
            item.matched_name = cells[0]
        item.product = item.matched_name or ""
        items.append(item)
    return items


def _parse_int(s: Optional[str]) -> Optional[int]:
    if not s:
        return None
    m = re.search(r"\d+", s.replace(",", ""))
    return int(m.group()) if m else None


class SunshopAdapter(BaseAdapter):
    portal_type = "SUNSHOP"

    # ---------- Login navigation ----------
    async def _open_login(self, page, url: str):
        """Landing page → 'Medical Login' → real login form."""
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(800)

        pw = await page.query_selector('input[type="password"]')
        if pw and await pw.is_visible():
            return

        for sel in [
            'a:has-text("Medical Login")',
            'button:has-text("Medical Login")',
            'a:has-text("Medical login")',
            'a:has-text("Login")',
            'button:has-text("Login")',
        ]:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    try:
                        await page.wait_for_load_state("networkidle", timeout=15000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(400)
                    return
            except Exception:
                continue

    # ---------- Post-login: BILLING → Order → Order Feed ----------
    async def _open_billing_order(self, page):
        """Open the BILLING dropdown and click Order (2nd item)."""
        # Open BILLING dropdown
        opened = False
        for sel in [
            'a.dropdown-toggle:has-text("BILLING")',
            'a:has-text("BILLING")',
            'button:has-text("BILLING")',
            'a:has-text("Billing")',
        ]:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.hover()
                    await page.wait_for_timeout(200)
                    await el.click()
                    await page.wait_for_timeout(500)
                    opened = True
                    break
            except Exception:
                continue
        if not opened:
            return False

        # Debug snapshot of the open dropdown so we can inspect exact item labels
        await self._screenshot(page, "billing-dropdown-open")

        # Prefer strong matches for a purchase-order style menu item first,
        # avoid "Sale" or "Bill" style options.
        # NOTE: user said the 2nd item in the dropdown is the correct "Order".
        specific_selectors = [
            '.dropdown-menu:visible a:has-text("Order Entry")',
            '.dropdown-menu:visible a:has-text("Purchase Order")',
            '.dropdown-menu:visible a:has-text("Purchase Bill")',
            '.dropdown-menu:visible a:has-text("Purchase")',
            'ul.dropdown-menu li a:has-text("Order Entry")',
            'ul.dropdown-menu li a:has-text("Purchase")',
            # href-based hints (avoid "salebill")
            'a[href*="purchase" i]:visible',
            'a[href*="order_entry" i]:visible',
            'a[href*="/order" i]:not([href*="salebill" i]):not([href*="bill" i]):visible',
        ]
        for sel in specific_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    try:
                        await page.wait_for_load_state("networkidle", timeout=20000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(500)
                    return True
            except Exception:
                continue

        # Fallback: pick the 2nd visible <a> item inside the visible dropdown menu.
        try:
            items = await page.query_selector_all('.dropdown-menu:visible li a, ul.dropdown-menu li a')
            visible_items = []
            for a in items:
                try:
                    if await a.is_visible():
                        visible_items.append(a)
                except Exception:
                    continue
            if len(visible_items) >= 2:
                await visible_items[1].click()
                try:
                    await page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    pass
                await page.wait_for_timeout(500)
                return True
        except Exception:
            pass

        # Last resort: plain "Order" link that's NOT a Sale Bill
        for sel in [
            'a:has-text("Order"):not(:has-text("Sale")):visible',
            'a:has-text("Order"):visible',
        ]:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    try:
                        await page.wait_for_load_state("networkidle", timeout=20000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(500)
                    return True
            except Exception:
                continue
        return False

    async def _click_order_feed(self, page, distributor_name: str) -> bool:
        """On the Order page, find the row matching the distributor and click Order Feed."""
        dist = (distributor_name or "").strip().upper()
        # Try to find a row whose text contains the distributor name
        rows = await page.query_selector_all("tr")
        target_row = None
        for row in rows:
            try:
                text = ((await row.inner_text()) or "").upper()
                if dist and dist in text:
                    target_row = row
                    break
            except Exception:
                continue

        # If we didn't find a match, try more loosely: look for cells containing the first word
        if not target_row and dist:
            first_word = dist.split()[0]
            for row in rows:
                try:
                    text = ((await row.inner_text()) or "").upper()
                    if first_word in text:
                        target_row = row
                        break
                except Exception:
                    continue

        if not target_row:
            return False

        for sel in [
            'a:has-text("Order Feed")',
            'button:has-text("Order Feed")',
            'a:has-text("Orderfeed")',
            'a:has-text("Feed")',
            'a:has-text("Order")',
            'button:has-text("Order")',
            'a.btn',
            'button',
            'a',
        ]:
            try:
                btn = await target_row.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    try:
                        await page.wait_for_load_state("networkidle", timeout=20000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(500)
                    return True
            except Exception:
                continue
        return False

    # ---------- Search product ----------
    async def _search_product(self, page, product: str, quantity: int) -> bool:
        """On the Order Feed page, type into the Product autocomplete, pick the first suggestion,
        then read the Stock value. Returns True if a suggestion was selected."""
        # Find the product autocomplete input
        search_el = None
        for sel in [
            'input[placeholder*="Enter Product" i]',
            'input[placeholder*="product" i]',
            'input[name="product" i]',
            'input[name="productname" i]',
            '#product',
            '#txtProduct',
            '#txtProductName',
        ] + SEARCH_INPUT_SELECTORS:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    search_el = el
                    break
            except Exception:
                continue
        if not search_el:
            return False

        try:
            await search_el.click()
        except Exception:
            pass
        # Clear any existing value, then type char-by-char to trigger autocomplete
        try:
            await search_el.fill("")
        except Exception:
            pass
        await search_el.type(product, delay=50)
        await page.wait_for_timeout(1200)  # give autocomplete time

        # Capture the autocomplete state for diagnostics
        await self._screenshot(page, "autocomplete-open")

        # Try to click the first visible autocomplete suggestion
        picked = False
        for sel in [
            'ul.ui-autocomplete li:visible',
            'ul.ui-autocomplete .ui-menu-item:visible',
            '.autocomplete-suggestion:visible',
            '.tt-suggestion:visible',
            'li.select2-results__option:visible',
            'ul.dropdown-menu.show li a',
            'ul.dropdown-menu:visible li a',
            'div[role="listbox"] div[role="option"]',
        ]:
            try:
                sug = await page.query_selector(sel)
                if sug and await sug.is_visible():
                    await sug.click()
                    picked = True
                    break
            except Exception:
                continue

        # If no suggestion element matched, fall back to keyboard: Down + Enter
        if not picked:
            try:
                await page.keyboard.press("ArrowDown")
                await page.wait_for_timeout(200)
                await page.keyboard.press("Enter")
                picked = True
            except Exception:
                pass

        # Give the form time to populate Stock / other fields
        await page.wait_for_timeout(1000)

        # Optionally fill quantity
        if quantity:
            for sel in QTY_INPUT_SELECTORS:
                try:
                    q = await page.query_selector(sel)
                    if q and await q.is_visible():
                        try:
                            await q.fill(str(quantity))
                        except Exception:
                            pass
                        break
                except Exception:
                    continue

        return picked

    # ---------- Read Order Feed page fields (Stock, matched product name) ----------
    async def _read_order_feed(self, page) -> Optional[ExtractedItem]:
        """Read the Product, Stock, Remarks/Scheme, and Quantity fields on the Order Feed form."""
        async def _read_field(labels, is_input=True):
            for label in labels:
                # Try to find an input whose preceding label / placeholder contains the label text
                try:
                    xpath = (
                        f'//label[contains(translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{label.lower()}")]'
                    )
                    label_el = await page.query_selector(f'xpath={xpath}')
                    if label_el:
                        # find the sibling input/span
                        sib = await label_el.evaluate_handle(
                            'el => { let n = el.nextElementSibling; while(n && !(n.tagName==="INPUT"||n.tagName==="SPAN"||n.tagName==="DIV")) { n = n.nextElementSibling; } return n; }'
                        )
                        try:
                            val = await sib.evaluate('n => n && (n.value !== undefined ? n.value : n.innerText)')
                            if val and str(val).strip():
                                return str(val).strip()
                        except Exception:
                            pass
                except Exception:
                    pass
                # Try placeholder-based lookup
                try:
                    el = await page.query_selector(f'input[placeholder*="{label}" i]')
                    if el:
                        val = await el.input_value()
                        if val:
                            return val.strip()
                except Exception:
                    pass
            return None

        matched_name = await _read_field(["Product"])
        stock = await _read_field(["Stock"])
        scheme = await _read_field(["Remarks/Scheme", "Remarks", "Scheme"])

        if not (matched_name or stock):
            return None

        return ExtractedItem(
            product=matched_name or "",
            matched_name=matched_name,
            available_qty=stock,
            scheme=scheme,
        )

    # ---------- Public interface ----------
    async def test_login(self, page, url: str, username: str, password: str):
        try:
            await self._open_login(page, url)
            filled = await self.fill_login(page, username, password)
            if not filled:
                return False, "Could not locate login form fields after opening login page"
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            ok = await self.is_logged_in(page)
            return ok, "Logged in" if ok else "Login form still present after submit"
        except Exception as e:
            return False, f"Login error: {e.__class__.__name__}: {e}"

    async def extract(self, page, url, username, password, product, quantity, distributor_name: str = ""):
        outcome = ExtractionOutcome(requested_qty=quantity)
        try:
            # 1. Open login
            await self._open_login(page, url)
            outcome.login_screenshot = await self._screenshot(page, "login")

            # 2. Submit credentials
            filled = await self.fill_login(page, username, password)
            if not filled:
                outcome.status = "LOGIN_FAILED"
                outcome.detail = "Login form fields not found"
                return outcome
            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                pass
            if not await self.is_logged_in(page):
                outcome.status = "LOGIN_FAILED"
                outcome.detail = "Login was submitted but form still visible — credentials likely wrong"
                outcome.search_screenshot = await self._screenshot(page, "post-login")
                return outcome

            outcome.search_screenshot = await self._screenshot(page, "dashboard")

            # 3. BILLING → Order
            if not await self._open_billing_order(page):
                outcome.status = "ERROR"
                outcome.detail = "Could not navigate BILLING → Order"
                outcome.results_screenshot = await self._screenshot(page, "no-order-menu")
                return outcome

            await self._screenshot(page, "order-page")

            # 4. Click Order Feed next to the distributor row
            if not await self._click_order_feed(page, distributor_name):
                outcome.status = "ERROR"
                outcome.detail = f'Could not find "Order Feed" for distributor: {distributor_name}'
                outcome.results_screenshot = await self._screenshot(page, "no-feed-btn")
                return outcome

            await self._screenshot(page, "order-feed-open")

            # 5. Search product (types in Product autocomplete, picks first suggestion)
            picked = await self._search_product(page, product, quantity or 0)
            outcome.results_screenshot = await self._screenshot(page, "results")

            if not picked:
                outcome.status = "NOT_FOUND"
                outcome.detail = "No autocomplete suggestion appeared for that product name"
                return outcome

            # 6. Read the populated Order Feed form (Stock, matched product name)
            item = await self._read_order_feed(page)
            if not item or (not item.matched_name and not item.available_qty):
                # Fall back to generic table parsing in case a table did render
                items = await _extract_table_data(page)
                outcome.items = items
                if not items:
                    outcome.status = "NOT_FOUND"
                    outcome.detail = "Product picked but Stock field was empty"
                    return outcome
            else:
                outcome.items = [item]

            total_qty = 0
            for it in outcome.items:
                v = _parse_int(it.available_qty)
                if v:
                    total_qty += v
            outcome.debug["totalAvailableQty"] = total_qty
            outcome.can_fulfill = total_qty >= (quantity or 0) if quantity else None
            outcome.status = "SUCCESS"
            outcome.detail = f"Parsed {len(outcome.items)} row(s)"
            return outcome
        except Exception as e:
            outcome.status = "ERROR"
            outcome.detail = f"{e.__class__.__name__}: {e}"
            try:
                outcome.results_screenshot = await self._screenshot(page, "error")
            except Exception:
                pass
            return outcome
