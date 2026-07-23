"""MARG (margcompusoft.com/eRetail) OTP session manager.

Two-step SMS-OTP login flow of https://margcompusoft.com/eRetail/User/Login :
  1) begin(mobile)  →  fills mobile at #UserName, clicks Next (#submit),
                       lands on /User/LoginVerifyOtp, then clicks the
                       "Login with OTP" button (button[value='LoginWithOtp']).
                       Server redirects to /User/VerifyOTP?... showing the
                       #OTP input + #Verify submit. Returns pendingId.
  2) verify(pendingId, otp)  →  types the OTP into #OTP, clicks #Verify,
                                grabs cookies, persists into MongoDB
                                (`marg_session`, single "default" doc).

Cookies typically stay valid for a day; if they expire the adapter will
report LOGIN_FAILED "SESSION_EXPIRED" and the user re-authenticates.
"""
from __future__ import annotations
import asyncio
import time
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger("marg")

LOGIN_URL = "https://margcompusoft.com/eRetail/User/Login"
PENDING_TTL = 300  # 5 minutes


class MargSessionManager:
    def __init__(self, mongo_db, get_browser):
        self.db = mongo_db
        self._get_browser = get_browser
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    # -------- persistence --------
    async def get_saved_cookies(self) -> Optional[list]:
        doc = await self.db.marg_session.find_one({"_id": "default"})
        return (doc or {}).get("cookies")

    async def get_status(self) -> dict:
        doc = await self.db.marg_session.find_one({"_id": "default"})
        if not doc:
            return {"active": False}
        return {
            "active": True,
            "mobile": doc.get("mobile"),
            "since": doc.get("since"),
            "cookieCount": len(doc.get("cookies") or []),
        }

    async def clear_session(self) -> None:
        await self.db.marg_session.delete_one({"_id": "default"})

    async def _save_cookies(self, ctx, mobile: str):
        cookies = await ctx.cookies()
        await self.db.marg_session.update_one(
            {"_id": "default"},
            {"$set": {
                "cookies": cookies,
                "mobile": mobile,
                "since": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
        logger.info(f"Saved {len(cookies)} MARG cookies for {mobile}")

    async def _cleanup_expired(self):
        now = time.time()
        for pid in [k for k, v in self._pending.items() if v["exp"] < now]:
            entry = self._pending.pop(pid, None)
            if entry:
                try: await entry["ctx"].close()
                except Exception: pass

    # -------- begin --------
    async def begin(self, mobile: str) -> dict:
        async with self._lock:
            await self._cleanup_expired()
        browser = await self._get_browser()
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
            ignore_https_errors=True,
        )
        page = await ctx.new_page()
        try:
            # Step 1: Enter mobile / user id and hit Next
            await page.goto(LOGIN_URL, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            try:
                await page.fill("#UserName", mobile)
            except Exception:
                # Fallback for slight markup changes
                await page.fill("input[name='UserName']", mobile)
            await page.wait_for_timeout(300)
            try:
                await page.click("#submit")
            except Exception:
                await page.click("button[type='submit']")
            await page.wait_for_timeout(4500)

            if "LoginVerifyOtp" not in (page.url or "") and "VerifyOTP" not in (page.url or ""):
                # Try to surface a message
                err = ""
                try:
                    err = (await page.inner_text("body"))[:300]
                except Exception:
                    pass
                await ctx.close()
                return {"ok": False, "error": f"MARG did not accept mobile {mobile}. {err[:180]}"}

            # Step 2: Click "Login with OTP" to trigger OTP send
            try:
                await page.click("button[value='LoginWithOtp']")
            except Exception:
                # Text fallback
                try:
                    await page.click("button:has-text('Login with OTP')")
                except Exception as e:
                    await ctx.close()
                    return {"ok": False, "error": f"Could not find 'Login with OTP' button: {e}"}
            await page.wait_for_timeout(5500)

            # Step 3: Wait for the OTP input to appear
            try:
                await page.wait_for_selector("#OTP, input[name='OTP']", timeout=15000, state="visible")
            except Exception:
                err = ""
                try:
                    err = (await page.inner_text("body"))[:300]
                except Exception:
                    pass
                await ctx.close()
                return {"ok": False, "error": f"OTP screen did not appear. {err[:200]}"}
        except Exception as e:
            try: await ctx.close()
            except Exception: pass
            return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}

        pending_id = str(uuid.uuid4())
        self._pending[pending_id] = {
            "ctx": ctx, "page": page, "mobile": mobile,
            "exp": time.time() + PENDING_TTL,
        }
        return {"ok": True, "pendingId": pending_id, "ttlSeconds": PENDING_TTL}

    # -------- verify --------
    async def verify(self, pending_id: str, otp: str) -> dict:
        entry = self._pending.get(pending_id)
        if not entry:
            return {"ok": False, "error": "OTP session expired — please Send OTP again"}
        page = entry["page"]
        ctx = entry["ctx"]
        try:
            otp_str = (otp or "").strip()
            try:
                await page.click("#OTP")
            except Exception:
                pass
            try:
                await page.fill("#OTP", "")
            except Exception:
                pass
            await page.type("#OTP", otp_str, delay=80)
            await page.wait_for_timeout(300)
            # Click Verify
            try:
                await page.click("#Verify")
            except Exception:
                try:
                    await page.click("input[value='Verify']")
                except Exception:
                    try:
                        await page.keyboard.press("Enter")
                    except Exception:
                        pass

            try:
                await page.wait_for_load_state("domcontentloaded", timeout=25000)
            except Exception:
                pass
            await page.wait_for_timeout(4500)

            cur = (page.url or "").lower()
            body = ""
            try:
                body = (await page.inner_text("body"))[:500].lower()
            except Exception:
                pass
            # Success: no longer on VerifyOTP page
            success = ("verifyotp" not in cur) and ("user/login" not in cur)
            if "invalid otp" in body or "otp is incorrect" in body or "expired" in body or "wrong otp" in body:
                success = False
            if not success:
                return {"ok": False, "error": "OTP verification failed (invalid or expired)"}
            await self._save_cookies(ctx, entry["mobile"])
            return {"ok": True, "url": page.url}
        except Exception as e:
            return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}
        finally:
            self._pending.pop(pending_id, None)
            try: await ctx.close()
            except Exception: pass
