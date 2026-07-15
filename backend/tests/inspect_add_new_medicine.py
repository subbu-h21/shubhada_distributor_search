"""Inspect what happens when 'Add New Medicine' is clicked."""
import asyncio, sys, os, json
sys.path.insert(0, "/app/backend")
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/pw-browsers")
from server import _get_browser

SH_URL = "https://shubhadahealth.com:7007"


async def main():
    browser = await _get_browser()
    ctx = await browser.new_context(ignore_https_errors=True, viewport={"width": 1366, "height": 900})
    page = await ctx.new_page()

    await page.goto(SH_URL, timeout=60000, wait_until="domcontentloaded")
    await page.wait_for_timeout(2500)
    await page.fill("input[name='user']", "9448188002")
    await page.fill("input[name='pass']", "Q")
    await page.evaluate("""() => { for (const b of document.querySelectorAll('button')) if ((b.innerText||'').trim().toLowerCase()==='login') b.click(); }""")
    await page.wait_for_timeout(6500)
    await page.locator("text=Re-Ordering Process").first.click(timeout=6000)
    await page.wait_for_timeout(6000)
    await page.screenshot(path="/app/backend/data/screenshots/anm_before.png")

    # Click "Add New Medicine"
    clicked = await page.evaluate("""() => {
        for (const el of document.querySelectorAll('a, button, span, div')) {
            if (!el.offsetParent) continue;
            const t = (el.innerText||'').trim().toLowerCase();
            if (t === 'add new medicine') { el.click(); return true; }
        }
        return false;
    }""")
    print("Clicked Add New Medicine:", clicked)
    await page.wait_for_timeout(4000)
    await page.screenshot(path="/app/backend/data/screenshots/anm_after.png")

    # Dump the state — search FROM DOCUMENT BODY (dialog may not be in mat-dialog-container)
    dump = await page.evaluate("""() => {
        const items = Array.from(document.querySelectorAll('input, textarea'))
            .filter(el => el.offsetParent)
            .map(el => ({
                tag: el.tagName, type: el.type||'', name: el.name||'', id: el.id||'',
                placeholder: el.placeholder||'', disabled: el.disabled, readOnly: el.readOnly,
                cls: (el.className||'').slice(0,140),
                value: (el.value||'').slice(0,40),
                label: ((el.closest('mat-form-field')||el.parentElement||{}).innerText||'').replace(/\\s+/g,' ').slice(0,80),
            }));
        return {
            url: location.href,
            count: items.length,
            editableWithPlaceholder: items.filter(i => !i.disabled && !i.readOnly && i.placeholder),
        };
    }""")
    print(json.dumps(dump, indent=2, default=str))

    await ctx.close()


asyncio.run(main())
