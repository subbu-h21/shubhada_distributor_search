"""Shubhada Pharma PO placement automation.

Endpoint: /api/order/place (see server.py)

Given { product, supplier, qty, mobile, patient, advance } from the extraction
result screen, this module:
  1. Logs in to https://shubhadahealth.com:7007 as `9448188002 / Q`.
  2. Navigates to the "Re-Ordering Process" (Purchase Order Management) page.
  3. Types the product name into the top search bar and clicks the first
     matching autocomplete suggestion — this appends a new row to the PO
     table.
  4. Sets the new row's Qty column.
  5. Clicks the row's "Modify Patient Details" link and fills patient name,
     mobile, quantity + advance-payment fields.
  6. Clicks the "Add to PO" (or "Save" fallback) button inside that dialog.
  7. Captures diagnostic screenshots at each step for the caller to display.

The selectors are best-effort (Shubhada's UI is Angular Material). If a step
fails, the caller receives a structured `error` + `screenshots` list so the
main app can show the user exactly where automation broke.
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
        user_agent="Mozilla/5.0 Chrome/124.0",
        viewport={"width": 1366, "height": 900},
    )
    page = await ctx.new_page()
    try:
        # 1. Login
        await page.goto(SH_URL, timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2200)
        await page.fill("input[name='user']", SH_USER)
        await page.fill("input[name='pass']", SH_PASS)
        await page.evaluate(
            """() => { for (const b of document.querySelectorAll('button')) if ((b.innerText||'').trim().toLowerCase()==='login') { b.click(); return; } }"""
        )
        await page.wait_for_timeout(6500)
        if "login" in (page.url or "").lower():
            shots.append(await _shot(page, "login-fail") or "")
            return {"ok": False, "error": "Shubhada login failed", "screenshots": shots, "steps": steps}
        steps.append("login-ok")
        shots.append(await _shot(page, "logged-in") or "")

        # 2. Navigate to Re-Ordering Process
        try:
            await page.locator("text=Re-Ordering Process").first.click(timeout=6000)
        except Exception as e:
            shots.append(await _shot(page, "no-reorder-tile") or "")
            return {"ok": False, "error": f"Re-Ordering Process tile not clickable: {e}", "screenshots": shots, "steps": steps}
        await page.wait_for_timeout(5500)
        steps.append(f"reorder-page url={page.url}")
        shots.append(await _shot(page, "reorder-page") or "")

        # 3. Type product name into #srch_prd, wait for autocomplete
        srch = await page.query_selector("#srch_prd")
        if not srch:
            shots.append(await _shot(page, "no-search-input") or "")
            return {"ok": False, "error": "Search products input (#srch_prd) not found", "screenshots": shots, "steps": steps}
        await srch.click()
        try: await srch.fill("")
        except Exception: pass
        await srch.type(product, delay=90)
        await page.wait_for_timeout(3500)
        shots.append(await _shot(page, "search-typed") or "")

        # 4. Click the first autocomplete option → this opens the
        #    "Order Details" dialog directly (not a table row).
        opt = page.locator("mat-option, li[role=option]").first
        try:
            await opt.click(timeout=5000)
        except Exception as e:
            shots.append(await _shot(page, "no-autocomplete") or "")
            return {"ok": False, "error": f"No autocomplete option matched '{product}': {e}", "screenshots": shots, "steps": steps}
        steps.append("suggestion-clicked")
        await page.wait_for_timeout(3500)
        shots.append(await _shot(page, "order-dialog") or "")

        # 5. Fill the "Order Details" dialog fields.
        # Field layout (verified):
        #   Product              — readonly
        #   Stockist/Supplier    — editable (default is recent purchaser)
        #   Last Pur. Date       — readonly
        #   Last Pur. Qty        — readonly
        #   Current Stock        — readonly
        #   Enter Suggested Qty  — EDITABLE   ← we set this to `qty`
        #   Patient Details (expandable)      ← we open + fill patient/mobile/advance
        #   Add To PO button
        async def _dlg_fill(regex: str, value: str) -> bool:
            try:
                return bool(await page.evaluate(
                    """({rx, v}) => {
                        const dlg = document.querySelector('mat-dialog-container, .mat-mdc-dialog-container, .cdk-overlay-pane');
                        if (!dlg) return false;
                        const re = new RegExp(rx, 'i');
                        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                        for (const el of dlg.querySelectorAll('input, textarea')) {
                            if (!el.offsetParent) continue;
                            if (el.readOnly || el.disabled) continue;
                            const ctx = ((el.placeholder||'') + ' ' + (el.name||'') + ' ' + (el.id||'') + ' ' + ((el.closest('mat-form-field')||el.parentElement||{}).innerText||'')).slice(0,400);
                            if (re.test(ctx)) {
                                setter.call(el, String(v));
                                ['input','change','keyup','blur'].forEach(t => el.dispatchEvent(new Event(t, {bubbles:true})));
                                return true;
                            }
                        }
                        return false;
                    }""",
                    {"rx": regex, "v": value},
                ))
            except Exception:
                return False

        # 5a. Enter Suggested Qty
        set_qty = await _dlg_fill(r"suggested\s*qty|enter\s*suggested", str(qty))
        steps.append(f"suggested-qty-set={set_qty}")
        await page.wait_for_timeout(400)

        # 5b. Supplier — clear the auto-filled recent supplier and type ours.
        # We need to click the field first, then clear + type + pick from dropdown.
        if supplier:
            try:
                clicked_supp = await page.evaluate(
                    """() => {
                        const dlg = document.querySelector('mat-dialog-container, .mat-mdc-dialog-container, .cdk-overlay-pane');
                        if (!dlg) return false;
                        for (const el of dlg.querySelectorAll('input')) {
                            if (!el.offsetParent) continue;
                            const ctx = ((el.placeholder||'') + ' ' + (el.name||'') + ' ' + ((el.closest('mat-form-field')||el.parentElement||{}).innerText||'')).slice(0,300);
                            if (/stockist|supplier|purchaser/i.test(ctx) && !el.readOnly) {
                                el.focus();
                                const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                                setter.call(el, '');
                                ['input','change','keyup'].forEach(t => el.dispatchEvent(new Event(t, {bubbles:true})));
                                return true;
                            }
                        }
                        return false;
                    }"""
                )
                if clicked_supp:
                    await page.wait_for_timeout(400)
                    # Type first few chars of the supplier
                    supp_prefix = supplier.split(" ")[0][:6]
                    await page.keyboard.type(supp_prefix, delay=90)
                    await page.wait_for_timeout(1500)
                    # Click the first matching mat-option
                    try:
                        await page.locator("mat-option").first.click(timeout=3500)
                        steps.append(f"supplier-picked={supplier}")
                    except Exception:
                        steps.append(f"supplier-no-suggestion (typed '{supp_prefix}')")
                    await page.wait_for_timeout(800)
                else:
                    steps.append("supplier-field-not-found")
            except Exception as e:
                steps.append(f"supplier-error: {e}")

        # 5c. Expand "Patient Details" section
        try:
            await page.evaluate(
                """() => {
                    const dlg = document.querySelector('mat-dialog-container, .mat-mdc-dialog-container, .cdk-overlay-pane') || document;
                    for (const el of dlg.querySelectorAll('mat-expansion-panel-header, button, div, span')) {
                        if (!el.offsetParent) continue;
                        const t = (el.innerText || '').trim().toLowerCase();
                        if (t === 'patient details' || t.startsWith('patient details')) { el.click(); return true; }
                    }
                    return false;
                }"""
            )
            await page.wait_for_timeout(1500)
            shots.append(await _shot(page, "patient-expanded") or "")
        except Exception as e:
            steps.append(f"patient-expand-error: {e}")

        # 5d. Fill patient name and (optionally) select the auto-suggested
        # patient. Autocomplete-style: type name, wait, click first mat-option.
        if patient:
            name_filled = await _dlg_fill(r"name(?!.*supplier|.*stockist)|patient", patient[:20])
            steps.append(f"patient-name-filled={name_filled}")
            if name_filled:
                await page.wait_for_timeout(1500)
                try:
                    await page.locator("mat-option").first.click(timeout=2000)
                    steps.append("patient-autocomplete-picked")
                except Exception:
                    steps.append("patient-autocomplete-none")

        # 5e. Patient quantity (some dialogs have a separate qty inside patient section)
        if qty:
            q2 = await _dlg_fill(r"^quantity$|patient.*qty|qty.*patient", str(qty))
            steps.append(f"patient-qty-filled={q2}")

        # 5f. Mobile
        if mobile:
            m_ok = await _dlg_fill(r"mobile|phone|contact", mobile)
            steps.append(f"patient-mobile-filled={m_ok}")

        # 5g. Advance payment
        if advance:
            a_ok = await _dlg_fill(r"advance", str(advance))
            steps.append(f"patient-advance-filled={a_ok}")

        shots.append(await _shot(page, "dialog-filled") or "")

        # 5. Locate the newly added row (by product text). Prefer the topmost
        #    row that contains the product name.
        row_upper = product.upper().split()[0]  # e.g. "PROLOMET"
        row_handle = await page.query_selector(f"tr:has-text('{row_upper}')")
        if not row_handle:
            # Fallback via evaluate_handle
            row_handle = await page.evaluate_handle(
                "(needle) => { const trs = Array.from(document.querySelectorAll('tr')); for (const tr of trs) { if ((tr.innerText||'').toUpperCase().includes(needle)) return tr; } return null; }",
                row_upper,
            )
            # If evaluate_handle returned JSValue null, that shows up as an
            # ElementHandle whose asElement() is None.
            if row_handle:
                as_el = await row_handle.evaluate("(n) => !!n")
                if not as_el:
                    row_handle = None
        if not row_handle:
            shots.append(await _shot(page, "no-row-found") or "")
            return {"ok": False, "error": "Newly added PO row not found", "screenshots": shots, "steps": steps}

        # 5a. Set Qty in that row (arg passed as a tuple → Playwright expects
        # a single serializable argument, so wrap in an array).
        try:
            qty_ok = await row_handle.evaluate(
                """(tr, q) => {
                    const inputs = tr.querySelectorAll('input[type=number]');
                    if (!inputs.length) return false;
                    const el = inputs[0];
                    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                    setter.call(el, String(q));
                    ['input','change','blur'].forEach(t => el.dispatchEvent(new Event(t, {bubbles:true})));
                    return true;
                }""",
                qty,
            )
            steps.append(f"qty-set={bool(qty_ok)}")
        except Exception as e:
            steps.append(f"qty-fill-error: {e}")

        # 5b. Change supplier if a "Change" link exists and supplier arg given
        if supplier:
            try:
                changed = await row_handle.evaluate(
                    """(tr) => {
                        for (const a of tr.querySelectorAll('a, button, span')) {
                            const t = (a.innerText || '').trim().toLowerCase();
                            if (t === 'change') { a.click(); return true; }
                        }
                        return false;
                    }"""
                )
                if changed:
                    await page.wait_for_timeout(2500)
                    dlg_input = await page.query_selector("mat-dialog-container input, .mat-mdc-dialog-container input")
                    if dlg_input:
                        await dlg_input.fill(supplier)
                        await page.wait_for_timeout(1800)
                        try:
                            opt2 = page.locator("mat-option").first
                            await opt2.click(timeout=3000)
                        except Exception:
                            pass
                        try:
                            await page.locator("mat-dialog-container button, .mat-mdc-dialog-container button").filter(has_text=re.compile(r"save|update|add", re.I)).first.click(timeout=3000)
                        except Exception:
                            pass
                        await page.wait_for_timeout(1500)
                steps.append(f"supplier-changed={changed}")
            except Exception as e:
                steps.append(f"supplier-error: {e}")

        # 6. Click "Modify Patient Details" on that row
        try:
            clicked = await row_handle.evaluate(
                """(tr) => {
                    for (const a of tr.querySelectorAll('a, button')) {
                        const t = (a.innerText || '').trim().toLowerCase();
                        if (t.includes('patient')) { a.click(); return true; }
                    }
                    return false;
                }"""
            )
            steps.append(f"patient-details-clicked={clicked}")
            await page.wait_for_timeout(3500)
            shots.append(await _shot(page, "patient-dialog") or "")
        except Exception as e:
            steps.append(f"patient-click-error: {e}")

        # 7. Fill patient dialog — name, mobile, qty, advance
        dlg_inputs = await page.evaluate("""() => {
            const dlg = document.querySelector('mat-dialog-container, .mat-mdc-dialog-container, .cdk-overlay-pane');
            if (!dlg) return [];
            return Array.from(dlg.querySelectorAll('input, textarea')).filter(i=>i.offsetParent).map((el, idx) => ({
                idx, name: el.name || '', id: el.id || '',
                placeholder: (el.placeholder || '').trim(),
                type: el.type || '',
            }));
        }""") or []
        steps.append(f"patient-dialog-inputs={len(dlg_inputs)}")

        async def _dlg_fill(match_rx: str, value: str):
            try:
                filled = await page.evaluate(
                    """({rx, v}) => {
                        const dlg = document.querySelector('mat-dialog-container, .mat-mdc-dialog-container, .cdk-overlay-pane');
                        if (!dlg) return false;
                        const re = new RegExp(rx, 'i');
                        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                        for (const el of dlg.querySelectorAll('input, textarea')) {
                            if (!el.offsetParent) continue;
                            const ctx = ((el.placeholder||'') + ' ' + (el.name||'') + ' ' + (el.id||'') + ' ' + ((el.closest('mat-form-field')||el.parentElement||{}).innerText||'')).slice(0,400);
                            if (re.test(ctx)) {
                                setter.call(el, String(v));
                                ['input','change','keyup','blur'].forEach(t => el.dispatchEvent(new Event(t, {bubbles:true})));
                                return true;
                            }
                        }
                        return false;
                    }""",
                    {"rx": match_rx, "v": value},
                )
                return bool(filled)
            except Exception:
                return False

        if patient:
            steps.append(f"patient-name-filled={await _dlg_fill(r'name', patient)}")
            await page.wait_for_timeout(1500)  # let autocomplete surface if any
        if mobile:
            steps.append(f"patient-mobile-filled={await _dlg_fill(r'mobile|phone|contact', mobile)}")
        if qty:
            steps.append(f"patient-qty-filled={await _dlg_fill(r'quantity|qty', str(qty))}")
        if advance:
            steps.append(f"patient-advance-filled={await _dlg_fill(r'advance', str(advance))}")

        shots.append(await _shot(page, "patient-filled") or "")

        # 8. Click "Add to PO" or "Save"
        clicked_add = False
        for label_rx in [r"^Add to PO$", r"Add\s*to\s*PO", r"^Save$", r"^Confirm$", r"^OK$", r"^Update$"]:
            try:
                await page.locator(f"mat-dialog-container button, .mat-mdc-dialog-container button").filter(has_text=re.compile(label_rx, re.I)).first.click(timeout=2000)
                clicked_add = True
                break
            except Exception:
                continue
        if not clicked_add:
            # fallback: click ANY button that reads Add / Save
            try:
                await page.evaluate("""() => {
                    const dlg = document.querySelector('mat-dialog-container, .mat-mdc-dialog-container, .cdk-overlay-pane') || document;
                    for (const b of dlg.querySelectorAll('button')) {
                        const t = (b.innerText || '').trim().toLowerCase();
                        if (/^(add to po|save|confirm|ok|update)/.test(t)) { b.click(); return true; }
                    }
                    return false;
                }""")
                clicked_add = True
            except Exception:
                pass
        steps.append(f"add-to-po-clicked={clicked_add}")
        await page.wait_for_timeout(4500)
        shots.append(await _shot(page, "after-add-to-po") or "")

        if not clicked_add:
            return {"ok": False, "error": "Could not click 'Add to PO' button", "screenshots": shots, "steps": steps}

        return {"ok": True, "screenshots": shots, "steps": steps}
    except Exception as e:
        shots.append(await _shot(page, "unhandled-error") or "")
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}", "screenshots": shots, "steps": steps}
    finally:
        try: await ctx.close()
        except Exception: pass
