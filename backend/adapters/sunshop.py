"""SUNSHOP portal adapter.

NOTE: This adapter uses generic heuristics because the real DOM was not
inspected yet. It will:
  - open the login URL
  - fill username/password using common field selectors
  - submit
  - after login, look for a product-search input, type the product
  - capture screenshots at each step (login, search, results)
  - attempt to parse the results table into structured rows (MRP, PTR, Qty)

Once the user shares the real DOM (or after a first live run), the selectors
below should be tuned to hit the exact fields on sunshop.co.in.
"""
from __future__ import annotations
import re
import asyncio
from typing import List, Optional
from .base import BaseAdapter, ExtractionOutcome, ExtractedItem


SEARCH_INPUT_SELECTORS = [
    'input[name="product" i]',
    'input[name="search" i]',
    'input[name="q" i]',
    'input[placeholder*="product" i]',
    'input[placeholder*="search" i]',
    'input[type="search"]',
    'input.search',
    '#search',
    '#product',
    '#txtSearch',
    '#txtProduct',
]

SEARCH_SUBMIT_SELECTORS = [
    'button[type="submit"]',
    'input[type="submit"]',
    'button:has-text("Search")',
    'input[value*="Search" i]',
    'button:has-text("Go")',
    '.btn-search',
    '#btnSearch',
]

COLUMN_ALIASES = {
    "product": ["product", "name", "item", "description"],
    "pack": ["pack", "packing", "size"],
    "mrp": ["mrp"],
    "ptr": ["ptr", "rate", "price", "net", "nrv"],
    "available_qty": ["stock", "qty", "quantity", "available", "avl"],
    "scheme": ["scheme", "offer"],
    "batch": ["batch", "batch no", "batchno"],
    "expiry": ["exp", "expiry", "exp date"],
    "manufacturer": ["company", "mfr", "manufacturer", "brand"],
}


def _match_col(header: str) -> Optional[str]:
    h = re.sub(r"[^a-z0-9]", " ", header.lower()).strip()
    for key, aliases in COLUMN_ALIASES.items():
        for a in aliases:
            if a in h:
                return key
    return None


async def _extract_table_data(page) -> List[ExtractedItem]:
    """Look for the largest visible table on the page and parse it."""
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
    # Find header row
    header_cells = []
    header_row_idx = 0
    for idx, r in enumerate(rows[:3]):
        ths = await r.query_selector_all("th")
        if ths:
            header_cells = [(await c.inner_text()).strip() for c in ths]
            header_row_idx = idx
            break
    if not header_cells:
        # First row as header (td-based)
        first = rows[0]
        tds = await first.query_selector_all("td")
        header_cells = [(await c.inner_text()).strip() for c in tds]

    col_map = {i: _match_col(h) for i, h in enumerate(header_cells)}

    items: List[ExtractedItem] = []
    for r in rows[header_row_idx + 1 :]:
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
        # Fallback: if no product column matched, use first cell
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

    async def _open_login(self, page, url: str):
        """Navigate to the SUNSHOP portal and click 'Medical Login' if the login form isn't on the landing page."""
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(800)

        # If there is already a visible password field, we are on a login page.
        pw = await page.query_selector('input[type="password"]')
        if pw and await pw.is_visible():
            return

        # Otherwise, click the "Medical Login" CTA (falls back to any *Login link).
        candidates = [
            'a:has-text("Medical Login")',
            'button:has-text("Medical Login")',
            'a:has-text("Medical login")',
            'a:has-text("Login")',
            'button:has-text("Login")',
        ]
        for sel in candidates:
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

    async def extract(self, page, url, username, password, product, quantity):
        outcome = ExtractionOutcome(requested_qty=quantity)
        try:
            await self._open_login(page, url)
            outcome.login_screenshot = await self._screenshot(page, "login")

            filled = await self.fill_login(page, username, password)
            if not filled:
                outcome.status = "LOGIN_FAILED"
                outcome.detail = "Login form fields not found on the page"
                return outcome
            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                pass
            if not await self.is_logged_in(page):
                outcome.status = "LOGIN_FAILED"
                outcome.detail = "Login was submitted but password field still visible — credentials likely wrong or captcha required"
                outcome.search_screenshot = await self._screenshot(page, "post-login")
                return outcome

            outcome.search_screenshot = await self._screenshot(page, "logged-in")

            # Locate search input
            search_el = None
            for sel in SEARCH_INPUT_SELECTORS:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        search_el = el
                        break
                except Exception:
                    continue
            if not search_el:
                outcome.status = "ERROR"
                outcome.detail = "Search input not found after login"
                return outcome

            await search_el.fill(product)
            # Try clicking a search button, else press Enter
            submitted = False
            for sel in SEARCH_SUBMIT_SELECTORS:
                try:
                    btn = await page.query_selector(sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        submitted = True
                        break
                except Exception:
                    continue
            if not submitted:
                await page.keyboard.press("Enter")

            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                pass
            await page.wait_for_timeout(500)
            outcome.results_screenshot = await self._screenshot(page, "results")

            items = await _extract_table_data(page)
            outcome.items = items
            if not items:
                outcome.status = "NOT_FOUND"
                outcome.detail = "Search complete but no result rows detected in DOM (see screenshot)"
                return outcome

            total_qty = 0
            for it in items:
                v = _parse_int(it.available_qty)
                if v:
                    total_qty += v
            outcome.debug["totalAvailableQty"] = total_qty
            outcome.can_fulfill = total_qty >= (quantity or 0) if quantity else None
            outcome.status = "SUCCESS"
            outcome.detail = f"Parsed {len(items)} row(s)"
            return outcome
        except Exception as e:
            outcome.status = "ERROR"
            outcome.detail = f"{e.__class__.__name__}: {e}"
            try:
                outcome.results_screenshot = await self._screenshot(page, "error")
            except Exception:
                pass
            return outcome