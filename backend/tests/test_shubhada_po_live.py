"""Test Shubhada PO placement flow — uses server's browser factory so it works
whether bundled Chromium is present or falls back to /root/bin/chromium."""
import asyncio, os, sys, json
sys.path.insert(0, "/app/backend")

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/pw-browsers")

from shubhada_po import place_order
from server import _get_browser


async def main():
    res = await place_order(
        _get_browser,
        product="PANTOP 40",
        supplier="SAROJ",
        qty=2,
        mobile="9123456789",
        patient="RAJESH TESTER",
        advance=50,
    )
    print(json.dumps({k: v for k, v in res.items() if k != "screenshots"}, indent=2, default=str))
    print("SCREENSHOTS:", res.get("screenshots"))


asyncio.run(main())
