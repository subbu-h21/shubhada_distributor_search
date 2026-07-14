"""LIVECONNECT OTP session manager.

Handles the two-step SMS-OTP login flow of https://www.liveconnect.in :
  1) begin(mobile)   -> opens Playwright, fills mobile, clicks Next, sends OTP.
     Returns a pendingId; the Playwright page is kept in memory (5 min TTL).
  2) verify(pendingId, otp) -> types OTP, clicks Verify, extracts cookies,
     persists them into MongoDB (`liveconnect_session` collection).

Persistent cookies survive backend restarts and are re-used by
LiveconnectAdapter to skip the OTP step on subsequent extractions.

A single session document is used per app instance (keyed by the mobile
number). Cookies typically remain valid for 7-30 days on liveconnect.in.
"""
from __future__ import annotations
import asyncio
import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger("liveconnect")

LOGIN_URL = "https://www.liveconnect.in/site/login"
PENDING_TTL = 300  # 5 minutes
MOBILE_INPUT = "#mob"
SEND_OTP_BTN = "#otpsend"
OTP_INPUT = "#otp"
VERIFY_BTN = "#verifyotp"


class LiveconnectSessionManager:
    def __init__(self, mongo_db, get_browser):
        self.db = mongo_db
        self._get_browser = get_browser
        self._pending: Dict[str, Dict[str, Any]] = {}  # pendingId -> {ctx, page, mobile, exp}
        self._lock = asyncio.Lock()

    # -------- session persistence --------
    async def get_saved_cookies(self) -> Optional[list]:
        doc = await self.db.liveconnect_session.find_one({"_id": "default"})
        if not doc:
            return None
        return doc.get("cookies")

    async def get_status(self) -> dict:
        doc = await self.db.liveconnect_session.find_one({"_id": "default"})
        if not doc:
            return {"active": False}
        return {
            "active": True,
            "mobile": doc.get("mobile"),
            "since": doc.get("since"),
            "cookieCount": len(doc.get("cookies") or []),
        }

    async def clear_session(self) -> None:
        await self.db.liveconnect_session.delete_one({"_id": "default"})

    async def _save_cookies(self, ctx, mobile: str):
        cookies = await ctx.cookies()
        await self.db.liveconnect_session.update_one(
            {"_id": "default"},
            {"$set": {
                "cookies": cookies,
                "mobile": mobile,
                "since": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
        logger.info(f"Saved {len(cookies)} LIVECONNECT cookies for mobile {mobile}")

    # -------- pending browser cleanup --------
    async def _cleanup_expired(self):
        now = time.time()
        to_close = [pid for pid, e in self._pending.items() if e["exp"] < now]
        for pid in to_close:
            entry = self._pending.pop(pid, None)
            if entry:
                try: await entry["ctx"].close()
                except Exception: pass

    # -------- begin --------
    async def begin(self, mobile: str) -> dict:
        """Open a browser, fill mobile, click Send-OTP. Returns { pendingId }."""
        async with self._lock:
            await self._cleanup_expired()
        browser = await self._get_browser()
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
            ignore_https_errors=True,
        )
        page = await ctx.new_page()
        try:
            await page.goto(LOGIN_URL, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            await page.fill(MOBILE_INPUT, mobile)
            await page.click(SEND_OTP_BTN)
            # Wait for OTP field to appear
            try:
                await page.wait_for_selector(OTP_INPUT, timeout=15000, state="visible")
            except Exception:
                # Try to read error text
                err = ""
                try:
                    err = (await page.inner_text("body"))[:200]
                except Exception:
                    pass
                await ctx.close()
                return {"ok": False, "error": f"OTP screen did not appear. Detail: {err[:120]}"}
        except Exception as e:
            try: await ctx.close()
            except Exception: pass
            return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}

        pending_id = str(uuid.uuid4())
        self._pending[pending_id] = {
            "ctx": ctx,
            "page": page,
            "mobile": mobile,
            "exp": time.time() + PENDING_TTL,
        }
        return {"ok": True, "pendingId": pending_id, "ttlSeconds": PENDING_TTL}

    # -------- verify --------
    async def verify(self, pending_id: str, otp: str) -> dict:
        entry = self._pending.get(pending_id)
        if not entry:
            return {"ok": False, "error": "OTP session expired or invalid — please Send OTP again"}
        page = entry["page"]
        ctx = entry["ctx"]
        try:
            # Use type() (dispatches input events) instead of fill() so the
            # page's JS validation enables the Verify button.
            try:
                await page.click(OTP_INPUT)
            except Exception:
                pass
            try:
                await page.fill(OTP_INPUT, "")
            except Exception:
                pass
            await page.type(OTP_INPUT, otp.strip(), delay=90)
            # Wait for the button to become enabled (some sites disable it until N digits)
            try:
                await page.wait_for_function(
                    "document.querySelector('#verifyotp') && !document.querySelector('#verifyotp').disabled",
                    timeout=5000,
                )
            except Exception:
                pass
            await page.click(VERIFY_BTN)
            # After verify, page should redirect to dashboard
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=25000)
            except Exception:
                pass
            await page.wait_for_timeout(3500)
            cur = (page.url or "").lower()
            body = ""
            try:
                body = (await page.inner_text("body"))[:500].lower()
            except Exception:
                pass
            # Success signals
            success = ("/site/login" not in cur) or ("logout" in body) or ("dashboard" in cur)
            # Failure signals
            if "invalid otp" in body or "otp does not match" in body or "expired" in body:
                success = False
            if not success:
                return {"ok": False, "error": "OTP verification failed (invalid or expired)"}
            await self._save_cookies(ctx, entry["mobile"])
            return {"ok": True, "url": page.url}
        except Exception as e:
            return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}
        finally:
            # Always close the browser after verify attempt
            self._pending.pop(pending_id, None)
            try: await ctx.close()
            except Exception: pass
