"""RETAILIO OTP session manager — same pattern as liveconnect_session.py.

Two-step SMS-OTP login flow of https://order.retailio.in/rio/secure-login :
  1) begin(mobile)  →  opens Playwright, fills mobile, ticks the terms
     checkbox, clicks Continue, selects "I am a retailer" (radio/button),
     and waits until the OTP entry appears. Returns pendingId.
  2) verify(pendingId, otp)  →  types the OTP, clicks Verify/Continue,
     extracts cookies + localStorage, persists into MongoDB
     (`retailio_session` collection, single "default" doc).

Cookies typically remain valid for weeks so subsequent scraping runs skip
the OTP dance entirely.
"""
from __future__ import annotations
import asyncio
import time
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger("retailio")

LOGIN_URL = "https://order.retailio.in/rio/secure-login"
PENDING_TTL = 300  # 5 minutes


class RetailioSessionManager:
    def __init__(self, mongo_db, get_browser):
        self.db = mongo_db
        self._get_browser = get_browser
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    # -------- persistence --------
    async def get_saved_cookies(self) -> Optional[list]:
        doc = await self.db.retailio_session.find_one({"_id": "default"})
        return (doc or {}).get("cookies")

    async def get_status(self) -> dict:
        doc = await self.db.retailio_session.find_one({"_id": "default"})
        if not doc:
            return {"active": False}
        return {
            "active": True,
            "mobile": doc.get("mobile"),
            "since": doc.get("since"),
            "cookieCount": len(doc.get("cookies") or []),
        }

    async def clear_session(self) -> None:
        await self.db.retailio_session.delete_one({"_id": "default"})

    async def _save_cookies(self, ctx, mobile: str, ls: Optional[dict] = None):
        cookies = await ctx.cookies()
        payload = {
            "cookies": cookies,
            "mobile": mobile,
            "since": datetime.now(timezone.utc).isoformat(),
        }
        if ls:
            payload["localStorage"] = ls
        await self.db.retailio_session.update_one({"_id": "default"}, {"$set": payload}, upsert=True)
        logger.info(f"Saved {len(cookies)} RETAILIO cookies for {mobile}")

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
            await page.goto(LOGIN_URL, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)

            # 1) Fill mobile number
            inp = await page.query_selector("input.input-fields, input[placeholder*='Mobile' i], input[placeholder*='Email' i]")
            if not inp:
                await ctx.close()
                return {"ok": False, "error": "Login mobile field not found on retailio.in"}
            await inp.fill(mobile)

            # 2) Tick the terms checkbox (id may be checkbox--checkbox-login)
            for sel in ("#checkbox--checkbox-login", "input[type='checkbox']"):
                try:
                    cb = await page.query_selector(sel)
                    if cb and not await cb.is_checked():
                        try:
                            await cb.check(force=True)
                        except Exception:
                            # Click the associated label instead
                            await page.evaluate("(id) => { const cb = document.getElementById(id); if (cb) cb.click(); }", sel.lstrip("#"))
                        break
                except Exception:
                    continue

            # 3) Click Continue
            await page.click("button:has-text('Continue'), button[type='submit']")
            await page.wait_for_timeout(4500)

            # 4) Select "I am a retailer" if a role picker is presented
            try:
                clicked = await page.evaluate("""() => {
                    const rx = /i\\s*am\\s*a\\s*retail|retailer/i;
                    for (const el of document.querySelectorAll('button, a, div, label, input[type=radio], input[type=button]')) {
                        if (!el.offsetParent) continue;
                        const t = (el.innerText || el.value || '').trim();
                        if (rx.test(t)) { el.click(); return t; }
                    }
                    return null;
                }""")
                if clicked:
                    await page.wait_for_timeout(2500)
            except Exception:
                pass

            # 5) Accept any subsequent terms checkbox that appears
            try:
                await page.evaluate("""() => {
                    for (const cb of document.querySelectorAll('input[type=checkbox]')) {
                        if (cb.offsetParent && !cb.checked) cb.click();
                    }
                }""")
                # And click any following continue/proceed button
                await page.evaluate("""() => {
                    const rx = /continue|proceed|next|confirm/i;
                    for (const el of document.querySelectorAll('button')) {
                        if (!el.offsetParent) continue;
                        const t = (el.innerText || '').trim();
                        if (rx.test(t) && !el.disabled) { el.click(); return; }
                    }
                }""")
                await page.wait_for_timeout(4000)
            except Exception:
                pass

            # 6) Wait for OTP entry. It may be a single input or 4-6 boxes.
            otp_found = await page.evaluate("""() => {
                const selectors = [
                    'input[placeholder*="OTP" i]',
                    'input[type="tel"][maxlength="1"]',
                    'input[maxlength="1"]',
                    'input[autocomplete="one-time-code"]',
                    'input[name*="otp" i]',
                    'input[id*="otp" i]',
                ];
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    if (els.length > 0 && els[0].offsetParent) return sel;
                }
                return null;
            }""")
            if not otp_found:
                # Snap a diagnostic screenshot before failing
                await ctx.close()
                return {"ok": False, "error": "OTP screen didn't appear after Continue + retailer selection. Please share a screenshot of what you see."}
        except Exception as e:
            try: await ctx.close()
            except Exception: pass
            return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}

        pending_id = str(uuid.uuid4())
        self._pending[pending_id] = {
            "ctx": ctx, "page": page, "mobile": mobile,
            "otp_selector": otp_found, "exp": time.time() + PENDING_TTL,
        }
        return {"ok": True, "pendingId": pending_id, "ttlSeconds": PENDING_TTL}

    # -------- verify --------
    async def verify(self, pending_id: str, otp: str) -> dict:
        entry = self._pending.get(pending_id)
        if not entry:
            return {"ok": False, "error": "OTP session expired — please Send OTP again"}
        page = entry["page"]
        ctx = entry["ctx"]
        sel = entry["otp_selector"]
        try:
            otp_str = (otp or "").strip()
            # Multi-box OTP inputs
            els = await page.query_selector_all(sel)
            if els and len(els) >= max(4, len(otp_str)):
                # One digit per box
                for i, ch in enumerate(otp_str):
                    if i >= len(els):
                        break
                    try:
                        await els[i].click()
                        await page.keyboard.type(ch, delay=80)
                    except Exception:
                        pass
            elif els:
                # Single input
                try:
                    await els[0].click()
                    await els[0].fill("")
                except Exception:
                    pass
                await page.type(sel, otp_str, delay=80)

            # Fire Verify — try common labels + Enter fallback
            clicked = False
            for label in ("Verify", "VERIFY", "Continue", "Submit", "Login", "Confirm"):
                try:
                    await page.click(f"button:has-text('{label}')", timeout=2000)
                    clicked = True
                    break
                except Exception:
                    continue
            if not clicked:
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
            success = "secure-login" not in cur
            body = ""
            try:
                body = (await page.inner_text("body"))[:400].lower()
            except Exception:
                pass
            if "invalid otp" in body or "expired" in body or "incorrect" in body:
                success = False

            if not success:
                return {"ok": False, "error": "OTP verification failed"}
            # Optionally capture localStorage tokens for Retailio SPA
            ls = None
            try:
                ls = await page.evaluate("() => Object.fromEntries(Object.entries(localStorage))")
            except Exception:
                pass
            await self._save_cookies(ctx, entry["mobile"], ls)
            return {"ok": True, "url": page.url}
        except Exception as e:
            return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}
        finally:
            self._pending.pop(pending_id, None)
            try: await ctx.close()
            except Exception: pass
