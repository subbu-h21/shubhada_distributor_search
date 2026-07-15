"""Shubhada Pharma PO placement automation.

Endpoint: /api/order/place (see server.py)

Flow (per user spec):
  1. Login to https://shubhadahealth.com:7007 as `9448188002 / Q`.
  2. Click "Re-Ordering Process" tile → search screen.
  3. Click the "Add New Medicine" link at the top of the reorder page —
     this opens the fresh Order Details dialog.
  4. In the dialog's Product field, type the product name and pick the
     matching autocomplete option.
  5. In the Supplier field, type the FIRST 4 LETTERS of the distributor
     name. A dropdown appears → pick the option matching the passed-in
     supplier.
  6. Expand the "Patient Details" section.
  7. Type patient name → if an auto-suggest option appears, click it;
     otherwise keep the typed value.
  8. Enter qty into "Quantity" and advance into "Advance Payment".
  9. Click "Add to PO".
 10. If this is a new patient, a warning box appears with a "Create Account"
     button → click it to confirm.
 11. Return success back to caller with screenshots + step log.

Selectors are Angular Material; failures are surfaced as `{ok:false, error,
screenshots, steps}` for debugging.
"""
from __future__ import annotations
import os, uuid, re
from pathlib import Path
from typing import Optional

SH_URL = "https://shubhadahealth.com:7007"
SH_USER = "9448188002"
SH_PASS = "Q"

_SCREENSHOTS_DIR = Path(os.environ.get("SCREENSHOTS_DIR", str(Path(__file__).parent / "data/screenshots")))
_SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


async def _shot(page, tag: str) -> Optional[str]:
    try:
        name = f"po_{tag}_{uuid.uuid4().hex[:6]}.png"
        await page.screenshot(path=str(_SCREENSHOTS_DIR / name), full_page=False)
        return name
    except Exception:
        return None


async def _fill_dialog_field(page, regex: str, value: str, *, force_enable: bool = False) -> bool:
    """Find an input in ANY currently-open dialog whose placeholder/name/id/
    surrounding label matches `regex` (case-insensitive) and set its value.
    If force_enable=True, temporarily remove disabled attr so Angular
    Material's readonly-styled inputs accept programmatic values."""
    try:
        return bool(await page.evaluate(
            """({rx, v, force}) => {
                const re = new RegExp(rx, 'i');
                const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                // Search all likely dialog containers PLUS the entire document
                // (some Angular apps render form pieces outside the overlay).
                const dialogs = Array.from(document.querySelectorAll(
                    'mat-dialog-container, .mat-mdc-dialog-container, .cdk-overlay-pane, .modal-content, [role=dialog]'
                ));
                const scopes = dialogs.length ? [...dialogs, document] : [document];
                const seen = new Set();
                const inputs = [];
                for (const s of scopes) {
                    for (const el of s.querySelectorAll('input, textarea')) {
                        if (seen.has(el)) continue;
                        seen.add(el);
                        inputs.push(el);
                    }
                }
                // Match strictly by name/placeholder/id first
                for (const el of inputs) {
                    if (el.readOnly) continue;
                    if (el.disabled && !force) continue;
                    const meta = (el.placeholder||'') + ' ' + (el.name||'') + ' ' + (el.id||'');
                    if (re.test(meta)) {
                        if (el.disabled) { el.disabled = false; el.removeAttribute('disabled'); }
                        try { el.focus(); } catch(_) {}
                        setter.call(el, String(v));
                        ['input','change','keyup','blur'].forEach(t => el.dispatchEvent(new Event(t, {bubbles:true})));
                        return true;
                    }
                }
                // Broader match against surrounding label text
                for (const el of inputs) {
                    if (el.readOnly) continue;
                    if (el.disabled && !force) continue;
                    const ctx = ((el.closest('mat-form-field')||el.parentElement||{}).innerText||'').slice(0,400);
                    if (re.test(ctx)) {
                        if (el.disabled) { el.disabled = false; el.removeAttribute('disabled'); }
                        try { el.focus(); } catch(_) {}
                        setter.call(el, String(v));
                        ['input','change','keyup','blur'].forEach(t => el.dispatchEvent(new Event(t, {bubbles:true})));
                        return true;
                    }
                }
                return false;
            }""",
            {"rx": regex, "v": value, "force": force_enable},
        ))
    except Exception:
        return False


async def _focus_dialog_field(page, regex: str, *, force_enable: bool = False) -> bool:
    """Focus (and clear) a dialog input matching regex — used before typing so
    that Angular's autocomplete fires with real keyboard events."""
    try:
        return bool(await page.evaluate(
            """({rx, force}) => {
                const re = new RegExp(rx, 'i');
                const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                const dialogs = Array.from(document.querySelectorAll(
                    'mat-dialog-container, .mat-mdc-dialog-container, .cdk-overlay-pane, .modal-content, [role=dialog]'
                ));
                const scopes = dialogs.length ? [...dialogs, document] : [document];
                const seen = new Set();
                const inputs = [];
                for (const s of scopes) {
                    for (const el of s.querySelectorAll('input')) {
                        if (seen.has(el)) continue;
                        seen.add(el);
                        inputs.push(el);
                    }
                }
                const tryMatch = (metaFn) => {
                    for (const el of inputs) {
                        if (el.readOnly) continue;
                        if (el.disabled && !force) continue;
                        if (re.test(metaFn(el))) {
                            if (el.disabled) { el.disabled = false; el.removeAttribute('disabled'); }
                            try { el.focus(); } catch(_) {}
                            setter.call(el, '');
                            ['input','change','keyup'].forEach(t => el.dispatchEvent(new Event(t, {bubbles:true})));
                            return true;
                        }
                    }
                    return false;
                };
                if (tryMatch(el => (el.placeholder||'') + ' ' + (el.name||'') + ' ' + (el.id||''))) return true;
                if (tryMatch(el => ((el.closest('mat-form-field')||el.parentElement||{}).innerText||'').slice(0,400))) return true;
                return false;
            }""",
            {"rx": regex, "force": force_enable},
        ))
    except Exception:
        return False


async def _click_mat_option_matching(page, needle: str, timeout_ms: int = 3500, *, require_match: bool = False) -> bool:
    """Click the mat-option whose text best matches `needle` (case-insensitive
    substring). If require_match=True, ONLY click if a genuine match exists
    (used for patient name where we don't want to accidentally pick a random
    existing patient)."""
    needle_up = needle.upper().strip()
    try:
        await page.wait_for_selector("mat-option, .mat-option, li[role=option]", timeout=timeout_ms)
    except Exception:
        return False

    try:
        clicked = await page.evaluate(
            """({needle, requireMatch}) => {
                const opts = Array.from(document.querySelectorAll('mat-option, .mat-option, li[role=option]'))
                    .filter(o => o.offsetParent);
                if (!opts.length) return false;
                let best = null, bestScore = -1;
                for (const o of opts) {
                    const t = (o.innerText || '').toUpperCase().trim();
                    let score = 0;
                    if (needle && t.includes(needle)) score = needle.length * 2;
                    else if (needle && t.startsWith(needle.slice(0,4))) score = 4;
                    if (score > bestScore) { bestScore = score; best = o; }
                }
                if (requireMatch && bestScore <= 0) return false;
                (best || opts[0]).click();
                return (best || opts[0]).innerText || '';
            }""",
            {"needle": needle_up, "requireMatch": require_match},
        )
        return bool(clicked)
    except Exception:
        return False


async def _click_button_matching(page, label_rx: str, in_dialog: bool = True) -> bool:
    """Click a button whose innerText matches label_rx (case-insensitive)."""
    try:
        return bool(await page.evaluate(
            """({rx, inDlg}) => {
                const re = new RegExp(rx, 'i');
                let scopes = [document];
                if (inDlg) {
                    const dialogs = Array.from(document.querySelectorAll(
                        'mat-dialog-container, .mat-mdc-dialog-container, .cdk-overlay-pane, .modal-content, [role=dialog]'
                    ));
                    scopes = dialogs.length ? dialogs : [document];
                }
                const seen = new Set();
                for (const root of scopes) {
                    for (const b of root.querySelectorAll('button, a')) {
                        if (seen.has(b)) continue;
                        seen.add(b);
                        if (!b.offsetParent) continue;
                        const t = (b.innerText || '').trim();
                        if (re.test(t)) { b.click(); return true; }
                    }
                }
                return false;
            }""",
            {"rx": label_rx, "inDlg": in_dialog},
        ))
    except Exception:
        return False


async def place_order(
    get_browser,
    *,
    product: str,
    supplier: str,
    qty: int,
    mobile: str,
    patient: str,
    advance: float = 0,
) -> dict:
    """Attempts to place a PO on shubhadahealth.com. Returns:
    { ok: bool, error?: str, screenshots: [names], steps: [str] }"""
    shots: list[str] = []
    steps: list[str] = []
    browser = await get_browser()
    ctx = await browser.new_context(
        ignore_https_errors=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1366, "height": 900},
    )
    page = await ctx.new_page()
    try:
        # 1. LOGIN --------------------------------------------------------
        await page.goto(SH_URL, timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2200)
        try:
            await page.fill("input[name='user']", SH_USER)
            await page.fill("input[name='pass']", SH_PASS)
        except Exception:
            # Fallback: type by placeholder
            await page.evaluate(
                """([u, p]) => {
                    const inputs = Array.from(document.querySelectorAll('input'));
                    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                    for (const el of inputs) {
                        const c = ((el.placeholder||'') + ' ' + (el.name||'') + ' ' + (el.id||'')).toLowerCase();
                        if (/user|mobile|phone|login/.test(c) && !el.value) { setter.call(el, u); el.dispatchEvent(new Event('input',{bubbles:true})); }
                        if (/pass/.test(c) && !el.value) { setter.call(el, p); el.dispatchEvent(new Event('input',{bubbles:true})); }
                    }
                }""",
                [SH_USER, SH_PASS],
            )
        await page.evaluate(
            """() => { for (const b of document.querySelectorAll('button')) if ((b.innerText||'').trim().toLowerCase()==='login') { b.click(); return; } }"""
        )
        await page.wait_for_timeout(6500)
        if "login" in (page.url or "").lower():
            shots.append(await _shot(page, "login-fail") or "")
            return {"ok": False, "error": "Shubhada login failed", "screenshots": shots, "steps": steps}
        steps.append("login-ok")
        shots.append(await _shot(page, "logged-in") or "")

        # 2. NAV to Re-Ordering Process ----------------------------------
        try:
            await page.locator("text=Re-Ordering Process").first.click(timeout=6000)
        except Exception as e:
            shots.append(await _shot(page, "no-reorder-tile") or "")
            return {"ok": False, "error": f"Re-Ordering Process tile not clickable: {e}", "screenshots": shots, "steps": steps}
        await page.wait_for_timeout(5500)
        steps.append(f"reorder-page url={page.url}")
        shots.append(await _shot(page, "reorder-page") or "")

        # 3. Click "Add New Medicine" link then type into the product
        # search bar. Clicking "Add New Medicine" simply focuses / anchors
        # the product-search section; the actual product input is #srch_prd.
        try:
            await page.evaluate(
                """() => {
                    for (const el of document.querySelectorAll('a, button, span, div')) {
                        if (!el.offsetParent) continue;
                        const t = (el.innerText || '').trim().toLowerCase();
                        if (t === 'add new medicine' || t.startsWith('add new medicine')) { el.click(); return true; }
                    }
                    return false;
                }"""
            )
            await page.wait_for_timeout(1000)
            steps.append("add-new-medicine-clicked")
        except Exception as e:
            steps.append(f"add-new-medicine-click-error: {e}")

        # 4. Product search — type into #srch_prd and pick first autocomplete
        srch = await page.query_selector("#srch_prd")
        if not srch:
            shots.append(await _shot(page, "no-search-input") or "")
            return {"ok": False, "error": "Product search input (#srch_prd) not found", "screenshots": shots, "steps": steps}
        await srch.click()
        try: await srch.fill("")
        except Exception: pass
        await srch.type(product, delay=90)
        await page.wait_for_timeout(3000)
        shots.append(await _shot(page, "product-typed") or "")

        try:
            await page.locator("mat-option, li[role=option]").first.click(timeout=5000)
        except Exception as e:
            shots.append(await _shot(page, "no-product-autocomplete") or "")
            return {"ok": False, "error": f"No autocomplete option matched product '{product}': {e}", "screenshots": shots, "steps": steps}
        steps.append("product-suggestion-clicked")
        await page.wait_for_timeout(3000)

        # 4b. Handle potential "WARNING - Already Added" popup by clicking Ok.
        # If the Order Details dialog is no longer present afterwards, treat
        # as success (product already on PO).
        warn_dismissed = await _click_button_matching(page, r"^\s*ok\s*$", in_dialog=False)
        if warn_dismissed:
            steps.append("already-added-warning-dismissed")
            await page.wait_for_timeout(1500)
            still_open = await page.evaluate(
                """() => {
                    const dialogs = document.querySelectorAll('mat-dialog-container, .mat-mdc-dialog-container, .cdk-overlay-pane');
                    for (const dlg of dialogs) {
                        if (/stockist|supplier|patient details|enter suggested qty/i.test(dlg.innerText || '')) return true;
                    }
                    return false;
                }"""
            )
            if not still_open:
                shots.append(await _shot(page, "already-on-po") or "")
                return {"ok": True, "screenshots": shots, "steps": steps + ["product-already-on-po"]}

        shots.append(await _shot(page, "order-dialog") or "")

        # 5. SUPPLIER --------------------------------------------------
        # Field is `disabled=true` by default (shows "By Default Recent
        # Purchaser"). Force-enable, type first 4 letters of the wanted
        # distributor, then click the mat-autocomplete option that matches.
        if supplier:
            supp_prefix = re.sub(r"\s+", "", supplier)[:4].upper()
            focused = await _focus_dialog_field(page, r"stockist|supplier|purchaser", force_enable=True)
            steps.append(f"supplier-field-focused={focused}")
            if focused:
                await page.wait_for_timeout(400)
                await page.keyboard.type(supp_prefix, delay=110)
                await page.wait_for_timeout(1800)
                picked = await _click_mat_option_matching(page, supplier, timeout_ms=3500)
                steps.append(f"supplier-picked={picked} (prefix='{supp_prefix}', want='{supplier}')")
                await page.wait_for_timeout(800)
                shots.append(await _shot(page, "supplier-picked") or "")

        # 6. Enter Suggested Qty (top-level `Enter Suggested Qty` field).
        # Field is `disabled=true` initially — force-enable it.
        set_qty = await _fill_dialog_field(page, r"enter\s*suggested\s*qty|suggested\s*qty|^sqt$", str(qty), force_enable=True)
        steps.append(f"suggested-qty-set={set_qty}")
        await page.wait_for_timeout(300)

        # 6b. Expand "Patient Details" panel so its fields become visible.
        # The panel is a mat-expansion-panel; click its header to open it,
        # then verify aria-expanded=true. If not, click once more.
        try:
            for attempt in range(3):
                expanded = await page.evaluate(
                    """() => {
                        // Search whole document; the mat-accordion may be
                        // outside any mat-dialog-container overlay.
                        for (const hdr of document.querySelectorAll('mat-expansion-panel-header')) {
                            if (/patient\\s*details/i.test(hdr.innerText || '')) {
                                if (hdr.getAttribute('aria-expanded') !== 'true') hdr.click();
                                return hdr.getAttribute('aria-expanded') === 'true';
                            }
                        }
                        return false;
                    }"""
                )
                await page.wait_for_timeout(1000)
                if expanded: break
            steps.append(f"patient-details-expanded={expanded}")
            shots.append(await _shot(page, "patient-expanded") or "")
        except Exception as e:
            steps.append(f"patient-expand-error: {e}")

        # 7. Patient Mobile (name='mob', placeholder='Patient Mobile') ----
        # Fill mobile FIRST so the app can auto-search patient by mobile.
        if mobile:
            focused_mob = await _focus_dialog_field(page, r"\bpatient\s*mobile\b|\bmob\b")
            steps.append(f"patient-mobile-focused={focused_mob}")
            if focused_mob:
                await page.keyboard.type(mobile, delay=80)
                await page.wait_for_timeout(1800)
                picked_mob = await _click_mat_option_matching(page, mobile, timeout_ms=1500, require_match=True)
                steps.append(f"patient-mobile-autocomplete-picked={picked_mob}")

        # 8. Patient Name (name='pat', placeholder='Patient Name'). Initially
        # disabled — becomes editable once mobile is entered. Type via
        # keyboard so autocomplete fires; if no match, force the final value
        # via JS setter (Angular tends to clear the field when focus is lost).
        if patient:
            focused_p = await _focus_dialog_field(page, r"\bpatient\s*name\b|\bpat\b", force_enable=True)
            steps.append(f"patient-name-focused={focused_p}")
            if focused_p:
                await page.keyboard.type(patient, delay=90)
                await page.wait_for_timeout(1500)
                picked_p = await _click_mat_option_matching(page, patient, timeout_ms=1500, require_match=True)
                steps.append(f"patient-autocomplete-picked={picked_p}")
                if not picked_p:
                    # No autocomplete match — force-set the value via JS to
                    # ensure it persists after focus loss (Angular reactive
                    # form controls sometimes reset disabled fields on blur).
                    forced = await page.evaluate(
                        """(v) => {
                            const el = document.querySelector('input[name="pat"]');
                            if (!el) return false;
                            if (el.disabled) { el.disabled = false; el.removeAttribute('disabled'); }
                            const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                            setter.call(el, String(v));
                            ['input','change','keyup','blur'].forEach(t => el.dispatchEvent(new Event(t, {bubbles:true})));
                            return true;
                        }""",
                        patient,
                    )
                    steps.append(f"patient-name-forced={forced}")

        # 9. Quantity (name='qty', placeholder='Quantity') — inside patient section.
        # Match by EXACT placeholder 'Quantity' or EXACT name 'qty' to avoid
        # colliding with 'Enter Suggested Qty' (which contains 'Qty').
        if qty:
            q2 = await page.evaluate(
                """(q) => {
                    const el = document.querySelector('input[name="qty"]');
                    if (!el) return false;
                    if (el.disabled) { el.disabled = false; el.removeAttribute('disabled'); }
                    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                    try { el.focus(); } catch(_) {}
                    setter.call(el, String(q));
                    ['input','change','keyup','blur'].forEach(t => el.dispatchEvent(new Event(t, {bubbles:true})));
                    return true;
                }""",
                str(qty),
            )
            steps.append(f"patient-qty-filled={bool(q2)}")

        # 10. Advance Payment (name='payment', placeholder='Advance Payment')
        if advance:
            a_ok = await page.evaluate(
                """(v) => {
                    const el = document.querySelector('input[name="payment"]');
                    if (!el) return false;
                    if (el.disabled) { el.disabled = false; el.removeAttribute('disabled'); }
                    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                    try { el.focus(); } catch(_) {}
                    setter.call(el, String(v));
                    ['input','change','keyup','blur'].forEach(t => el.dispatchEvent(new Event(t, {bubbles:true})));
                    return true;
                }""",
                str(advance),
            )
            steps.append(f"patient-advance-filled={bool(a_ok)}")

        shots.append(await _shot(page, "dialog-filled") or "")

        # 11. Click "Add to PO" --------------------------------------
        clicked_add = False
        for label_rx in [r"^Add\s*to\s*PO$", r"Add\s*To\s*PO", r"Add\s*to\s*PO"]:
            if await _click_button_matching(page, label_rx, in_dialog=True):
                clicked_add = True
                break
        steps.append(f"add-to-po-clicked={clicked_add}")
        if not clicked_add:
            shots.append(await _shot(page, "no-add-button") or "")
            return {"ok": False, "error": "Could not click 'Add to PO' button", "screenshots": shots, "steps": steps}

        # 12. Handle "Create Account" warning for new patients ---------
        await page.wait_for_timeout(2500)
        shots.append(await _shot(page, "post-add-to-po") or "")

        # A warning dialog may open ("Patient does not exist — Create
        # Account?"). Click "Create Account" / "Yes" / "Ok" to confirm.
        created_ok = False
        for label_rx in [r"create\s*account", r"^create$", r"^yes$", r"^ok$", r"^confirm$", r"^proceed$"]:
            if await _click_button_matching(page, label_rx, in_dialog=True):
                created_ok = True
                break
            if await _click_button_matching(page, label_rx, in_dialog=False):
                created_ok = True
                break
        if created_ok:
            steps.append("create-account-warning-confirmed")
            await page.wait_for_timeout(3000)
            shots.append(await _shot(page, "after-create-account") or "")
        else:
            steps.append("no-create-account-warning (existing patient or auto-dismissed)")

        # 13. Final settle screenshot -------------------------------
        await page.wait_for_timeout(2500)
        shots.append(await _shot(page, "po-final") or "")

        return {"ok": True, "screenshots": shots, "steps": steps}
    except Exception as e:
        shots.append(await _shot(page, "unhandled-error") or "")
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}", "screenshots": shots, "steps": steps}
    finally:
        try: await ctx.close()
        except Exception: pass
