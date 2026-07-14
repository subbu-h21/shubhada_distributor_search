"""Base adapter interface for distributor portal scrapers.

All concrete adapters (SunshopAdapter, ChethanaAdapter, etc.) implement:
  - test_login(page, url, username, password) -> (ok: bool, detail: str)
  - extract(page, url, username, password, product, quantity) -> ExtractionOutcome

The framework (server.py) handles: launching a browser, screenshots per stage,
saving HTML dumps on failure, retention cleanup, and DB persistence.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ExtractedItem:
    product: str
    matched_name: Optional[str] = None
    pack: Optional[str] = None
    mrp: Optional[str] = None
    ptr: Optional[str] = None
    available_qty: Optional[str] = None
    scheme: Optional[str] = None
    batch: Optional[str] = None
    expiry: Optional[str] = None
    manufacturer: Optional[str] = None
    seller: Optional[str] = None            # For aggregators (LIVECONNECT): the seller/distributor name
    raw_row: Optional[List[str]] = None  # For debug: full row cells


@dataclass
class ExtractionOutcome:
    """Per-distributor result of a run."""
    status: str = "PENDING"  # SUCCESS | NOT_FOUND | LOGIN_FAILED | ERROR
    detail: str = ""
    items: List[ExtractedItem] = field(default_factory=list)
    requested_qty: Optional[int] = None
    can_fulfill: Optional[bool] = None  # True if aggregate available_qty >= requested_qty
    login_screenshot: Optional[str] = None
    search_screenshot: Optional[str] = None
    results_screenshot: Optional[str] = None
    debug: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "detail": self.detail,
            "items": [it.__dict__ for it in self.items],
            "requestedQty": self.requested_qty,
            "canFulfill": self.can_fulfill,
            "loginScreenshot": self.login_screenshot,
            "searchScreenshot": self.search_screenshot,
            "resultsScreenshot": self.results_screenshot,
            "debug": self.debug,
        }


class BaseAdapter:
    portal_type: str = "BASE"

    def __init__(self, screenshotter=None):
        # screenshotter: async callable (page, tag) -> str (filename) OR None
        self.screenshotter = screenshotter

    async def _screenshot(self, page, tag: str):
        if self.screenshotter is None:
            return None
        try:
            return await self.screenshotter(page, tag)
        except Exception:
            return None

    # Selector candidates — subclasses override.
    LOGIN_USER_SELECTORS: List[str] = [
        'input[name="username" i]',
        'input[name="user" i]',
        'input[name="userid" i]',
        'input[name="userId" i]',
        'input[name="login" i]',
        'input[name="email" i]',
        'input[id*="user" i]',
        'input[type="text"]:visible',
    ]
    LOGIN_PASS_SELECTORS: List[str] = [
        'input[type="password"]',
        'input[name="password" i]',
        'input[name="pass" i]',
    ]
    LOGIN_SUBMIT_SELECTORS: List[str] = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Login")',
        'button:has-text("Sign in")',
        'input[value*="Login" i]',
        'input[value*="Sign" i]',
    ]

    async def fill_login(self, page, username: str, password: str) -> bool:
        """Best-effort login form filler. Returns True if submit was clicked."""
        user_filled = False
        for sel in self.LOGIN_USER_SELECTORS:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.fill(username)
                    user_filled = True
                    break
            except Exception:
                continue

        pass_filled = False
        for sel in self.LOGIN_PASS_SELECTORS:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.fill(password)
                    pass_filled = True
                    break
            except Exception:
                continue

        if not (user_filled and pass_filled):
            return False

        for sel in self.LOGIN_SUBMIT_SELECTORS:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    return True
            except Exception:
                continue
        # Fallback: press Enter on password field
        try:
            await page.keyboard.press("Enter")
            return True
        except Exception:
            return False

    async def is_logged_in(self, page) -> bool:
        """Heuristic: password field gone AND page doesn't show a WAF/error banner.

        Common WAF/error banners that indicate we did NOT log in successfully.
        """
        try:
            # Any WAF/error signature on the page means it's NOT a successful login
            body_text = ""
            try:
                body_text = (await page.inner_text("body"))[:2000].lower()
            except Exception:
                pass
            failure_signals = [
                "not acceptable",
                "mod_security",
                "access denied",
                "forbidden",
                "invalid username",
                "invalid password",
                "incorrect password",
                "login failed",
                "wrong credentials",
                "user not found",
            ]
            for sig in failure_signals:
                if sig in body_text:
                    return False

            pw = await page.query_selector('input[type="password"]')
            if not pw:
                return True
            visible = await pw.is_visible()
            return not visible
        except Exception:
            return True

    async def test_login(self, page, url: str, username: str, password: str):
        raise NotImplementedError

    async def extract(self, page, url: str, username: str, password: str, product: str, quantity: int) -> ExtractionOutcome:
        raise NotImplementedError
