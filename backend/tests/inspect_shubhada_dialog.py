"""Inspect the Order Details dialog DOM to build correct selectors."""
import asyncio, os, sys, json
sys.path.insert(0, "/app/backend")

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/pw-browsers")

from server import _get_browser

SH_URL = "https://shubhadahealth.com:7007"
SH_USER = "9448188002"
SH_PASS = "Q"


async def main():
    browser = await _get_browser()
    ctx = await browser.new_context(ignore_https_errors=True, viewport={"width": 1366, "height": 900})
    page = await ctx.new_page()

    await page.goto(SH_URL, timeout=45000, wait_until="domcontentloaded")
    await page.wait_for_timeout(2200)
    await page.fill("input[name='user']", SH_USER)
    await page.fill("input[name='pass']", SH_PASS)
    await page.evaluate("""() => { for (const b of document.querySelectorAll('button')) if ((b.innerText||'').trim().toLowerCase()==='login') b.click(); }""")
    await page.wait_for_timeout(6500)

    await page.locator("text=Re-Ordering Process").first.click(timeout=6000)
    await page.wait_for_timeout(5500)

    # Click "Add New Medicine" link to open the Order Details dialog
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
    await page.wait_for_timeout(3000)
    await page.screenshot(path="/app/backend/data/screenshots/inspect_add_new_dialog.png")

    srch = await page.query_selector("#srch_prd")
    # Use a randomized product name to avoid 'Already Added' warnings
    import random, string
    unique_suffix = ''.join(random.choices(string.ascii_uppercase, k=3))
    # Type a common product; if it's in the PO already we'll dismiss + retry
    prod = "AMLIP 5"
    await srch.click(); await srch.type(prod, delay=90)
    await page.wait_for_timeout(3500)
    try: await page.locator("mat-option, li[role=option]").first.click(timeout=5000)
    except Exception: pass
    await page.wait_for_timeout(4000)

    # Dismiss any "Already Added" WARNING and retry with a different product
    for attempt, prod in enumerate(["AMLIP 5", "DOLO 650", "AMLONG 5", "BERITOL", "ZIFI 100", "CROCIN"]):
        # Check if WARNING is showing
        warn = await page.evaluate("""() => {
            for (const b of document.querySelectorAll('button')) {
                if (!b.offsetParent) continue;
                const t = (b.innerText||'').trim().toLowerCase();
                if (t === 'ok') return true;
            }
            return false;
        }""")
        if warn:
            await page.evaluate("""() => {
                for (const b of document.querySelectorAll('button')) {
                    if (b.offsetParent && (b.innerText||'').trim().toLowerCase() === 'ok') { b.click(); return; }
                }
            }""")
            await page.wait_for_timeout(1500)
            # Type next product
            srch2 = await page.query_selector("#srch_prd")
            await srch2.click()
            await srch2.fill("")
            await srch2.type(prod, delay=90)
            await page.wait_for_timeout(3500)
            try: await page.locator("mat-option, li[role=option]").first.click(timeout=5000)
            except Exception: pass
            await page.wait_for_timeout(4000)
            continue
        break

    await page.screenshot(path="/app/backend/data/screenshots/inspect_after_click.png")

    await page.screenshot(path="/app/backend/data/screenshots/inspect_after_click.png")


    # Inspect Patient Details section structure
    pd_dump = await page.evaluate("""() => {
        // Try searching the ENTIRE document for "Patient Details" text
        const found = [];
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
        let node;
        while (node = walker.nextNode()) {
            const t = (node.innerText || '').trim();
            if (t.toLowerCase() === 'patient details' || (t.toLowerCase().startsWith('patient details') && t.length < 50)) {
                // Skip if this is a nested containing element (many parents will match)
                if (found.some(f => f.el === node.parentElement)) continue;
                found.push({
                    el: node,
                    tag: node.tagName,
                    cls: (node.className || '').slice(0,100),
                    role: node.getAttribute('role') || '',
                    ariaExpanded: node.getAttribute('aria-expanded') || '',
                    innerText: t.slice(0,60),
                    childCount: node.children.length,
                    outer: (node.outerHTML || '').slice(0, 300).replace(/\\s+/g, ' '),
                });
            }
        }
        return found.slice(0, 15).map(f => { const { el, ...rest } = f; return rest; });
    }""")
    print('PATIENT DETAILS ELEMENTS:', json.dumps(pd_dump, indent=2))

    # DUMP EVERYTHING on the whole page (not just mat-dialog)
    dump = await page.evaluate("""() => {
        const items = Array.from(document.querySelectorAll('input, textarea, select, button, mat-select'))
            .filter(el => el.offsetParent)
            .map(el => ({
                tag: el.tagName,
                type: el.type || '',
                name: el.name || '',
                id: el.id || '',
                placeholder: el.placeholder || '',
                readOnly: el.readOnly || false,
                disabled: el.disabled || false,
                value: (el.value || '').slice(0,60),
                label: ((el.closest('mat-form-field')||el.parentElement||{}).innerText || '').replace(/\\s+/g, ' ').slice(0,120),
                innerText: (el.innerText||'').replace(/\\s+/g,' ').slice(0,80),
                class: (el.className||'').slice(0,120),
            }));
        return { url: window.location.href, count: items.length, items };
    }""")
    print(json.dumps(dump, indent=2, default=str))

    # Old detail dump was here — kept only for compat
    old_dump = 0

    await ctx.close()


asyncio.run(main())
