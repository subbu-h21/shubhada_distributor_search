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
        # Diagnostic screenshots — saved under backend/data/screenshots so we
        # can inspect them via the /api/screenshots/{name} endpoint.
        import os as _os
        from pathlib import Path as _Path
        _shot_dir = _Path(_os.environ.get("SCREENSHOTS_DIR", str(_Path(__file__).parent / "data/screenshots")))
        _shot_dir.mkdir(parents=True, exist_ok=True)
        _shots: list[str] = []
        async def _diag(tag: str):
            try:
                name = f"rio_{tag}_{uuid.uuid4().hex[:6]}.png"
                await page.screenshot(path=str(_shot_dir / name), full_page=False)
                _shots.append(name)
            except Exception:
                pass
        try:
            await page.goto(LOGIN_URL, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)
            await _diag("01_open")

            # 1) Fill mobile number
            inp = await page.query_selector("input.input-fields, input[placeholder*='Mobile' i], input[placeholder*='Email' i]")
            if not inp:
                await ctx.close()
                return {"ok": False, "error": "Login mobile field not found on retailio.in", "diag": _shots}
            await inp.fill(mobile)
            await page.wait_for_timeout(300)

            # 1b) Retailio requires selecting "I'm a Retailer" (radio-style
            # chip) to enable Continue. Use Playwright's text locator which
            # is the most reliable way to click custom radios/chips.
            picked_retailer = False
            for loc_expr in ("text=/I['\u2019]?m a Retailer/i", "text=I'm a Retailer", 'text="I\'m a Retailer"'):
                try:
                    loc = page.locator(loc_expr).first
                    await loc.click(timeout=2500)
                    picked_retailer = True
                    break
                except Exception:
                    continue
            logger.info(f"Retailio: picked_retailer={picked_retailer}")
            await page.wait_for_timeout(500)

            # 2) Tick the terms / agree checkbox. Multiple strategies.
            # IMPORTANT: this is IDEMPOTENT — it only toggles when unchecked.
            async def _is_terms_checked():
                try:
                    return bool(await page.evaluate("""() => {
                        for (const cb of document.querySelectorAll('input[type=checkbox]')) {
                            if (cb.offsetParent && cb.checked) return true;
                        }
                        return false;
                    }"""))
                except Exception:
                    return False

            async def _tick_terms():
                if await _is_terms_checked():
                    return True
                # a) Native setter: forces state without toggling.
                try:
                    changed = await page.evaluate("""() => {
                        const boxes = Array.from(document.querySelectorAll('input[type=checkbox]'));
                        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'checked').set;
                        for (const cb of boxes) {
                            if (!cb.offsetParent) continue;
                            if (!cb.checked) {
                                setter.call(cb, true);
                                cb.dispatchEvent(new Event('input', {bubbles: true}));
                                cb.dispatchEvent(new Event('change', {bubbles: true}));
                                cb.dispatchEvent(new Event('click', {bubbles: true}));
                                return true;
                            }
                        }
                        return false;
                    }""")
                    if changed and await _is_terms_checked():
                        return True
                except Exception:
                    pass
                # b) Fallback — click label with agree text (only if still unchecked)
                if not await _is_terms_checked():
                    try:
                        await page.evaluate("""() => {
                            const rx = /agree|terms|condition/i;
                            for (const l of document.querySelectorAll('label, p, span, div')) {
                                if (!l.offsetParent) continue;
                                const t = (l.innerText || '').trim();
                                if (t.length > 200 || t.length < 8) continue;
                                if (rx.test(t)) {
                                    const cb = l.querySelector('input[type=checkbox]');
                                    if (cb && !cb.checked) { l.click(); return; }
                                }
                            }
                        }""")
                    except Exception:
                        pass
                return await _is_terms_checked()

            await _tick_terms()
            await _diag("02_after_tick")
            await page.wait_for_timeout(500)

            # 3) Wait for Continue to become enabled — poll up to 6s.
            # Only re-tick when actually unchecked (idempotent, no toggling).
            enabled = False
            for _ in range(24):
                try:
                    is_disabled = await page.evaluate("""() => {
                        for (const b of document.querySelectorAll('button')) {
                            if (!b.offsetParent) continue;
                            const t = (b.innerText || b.textContent || '').trim();
                            if (/continue|proceed|next|submit/i.test(t)) return b.disabled;
                        }
                        return true;
                    }""")
                    if not is_disabled:
                        enabled = True
                        break
                except Exception:
                    pass
                if not await _is_terms_checked():
                    await _tick_terms()
                await page.wait_for_timeout(250)

            if not enabled:
                # Diagnostic: dump body for logs
                try:
                    body = (await page.inner_text("body"))[:400]
                    logger.warning(f"Retailio Continue stayed disabled. body={body[:200]}")
                except Exception:
                    pass

            # 4) Click Continue
            try:
                await page.evaluate("""() => {
                    for (const b of document.querySelectorAll('button')) {
                        if (!b.offsetParent) continue;
                        const t = (b.innerText || '').trim();
                        if (/continue|proceed|next|submit/i.test(t) && !b.disabled) { b.click(); return; }
                    }
                }""")
            except Exception:
                pass
            await page.wait_for_timeout(4500)
            await _diag("03_after_continue")

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
            await _diag("04_after_role")

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
                await _diag("05_no_otp")
                await ctx.close()
                return {"ok": False, "error": "OTP screen didn't appear after Continue + retailer selection.", "diag": _shots}
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
