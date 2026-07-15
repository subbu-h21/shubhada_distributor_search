# PHARMASCRAPE / Shubhada Pharma Sirsi — PRD

## Original Problem Statement
Clone the PHARMASCRAPE distributor-availability lookup app and make it fully functional.
A pharmacist logs into multiple distributor portals (SUNSHOP, CHETHANA, LIVECONNECT, VARDHAMAN),
searches for a product + quantity, and receives live availability, MRP, PTR, Scheme, and Stock
with screenshots.

## Product Requirements
- Mobile-first UI, Space Grotesk font, Green/White theme, "SHUBHADA PHARMA SIRSI" branding.
- 4-user JWT login (shared workspace): shubhada/2612, manju/6387, abhishek/5555, narendra/6666.
- Excel Product Master upload → instant frontend autocomplete (35K+ products).
- Playwright (headless Chromium) real-time scraping of distributor portals.
- AES/Fernet-encrypted distributor credentials.
- Screenshots (login / search / results) captured per extraction.
- Match rule ignores special chars, unit words (mg/ml/tab/cap), and pack sizes (10s/15s).
  Different strength numbers (25 vs 50) are treated as different products.
- Word-by-word typing into portal search fields (never paste — respects autocomplete).

## Tech Stack
- Frontend: React 19 + Tailwind + shadcn UI + lucide-react.
- Backend: FastAPI + Motor (async MongoDB) + Playwright + Pandas/openpyxl + BeautifulSoup4.
- Auth/Security: JWT (pyjwt), bcrypt, Fernet AES (cryptography).

## Adapters Implemented
| Portal | Status | Fields returned |
|--------|--------|------------------|
| SUNSHOP (SAROJ, HEGDE, KAPILA PHARMA, KAPILA MEDICAL) | ✅ Live | Product, Pack, Stock |
| CHETHANA (CHIRAG PHARMA, CHETHANA PHARMA / chethanapharma.in) | ✅ Live | Code, Product, Pack, MRP |
| LIVECONNECT (8 sellers via search-all-sellers) | ✅ Live | Seller, Product, Mfr, Pack, MRP, PTR, Stock, Scheme, Tax |
| VARDHAMAN Shimoga (`fgtsmg.fortiddns.com:83`) | ⚠️ IP-blocked from container (port 83 refuses non-Indian IPs) |
| RETAILIO (order.retailio.in) | ✅ Live | Seller, Product, Pack, MRP, PTR, Scheme, Stock (OTP-based session, drills into detail view) |
| YASHIKA AGENCIES HUBLI (yashikaagencies.in) | ✅ Live | Product, Mfr, Pack, Scheme, MRP, PTR, Expiry, Stock (customer-id login) |

## Key Files
- `/app/backend/server.py` — API routes (needs future split into `routes/`).
- `/app/backend/liveconnect_session.py` — OTP session manager (mobile + OTP → cookies stored in `db.liveconnect_session`).
- `/app/backend/adapters/base.py` — Playwright helpers + ExtractedItem model.
- `/app/backend/adapters/match.py` — Shared canonicalization + fuzzy match scoring.
- `/app/backend/adapters/sunshop.py` — SUNSHOP scraper.
- `/app/backend/adapters/chethana.py` — CHETHANA / chiragpharma scraper.
- `/app/backend/adapters/liveconnect.py` — LIVECONNECT search-all-sellers aggregator (BeautifulSoup parse).
- `/app/backend/adapters/generic.py` — Fallback (extends Sunshop).
- `/app/backend/auth.py`, `/app/backend/security.py` — JWT + AES helpers.
- `/app/frontend/src/components/LiveconnectOtpSheet.jsx` — OTP UI (mobile → OTP → done).
- `/app/frontend/src/components/ResultCard.jsx` — Result rendering with SELLER + MFR columns.
- `/app/frontend/src/components/ExtractionModal.jsx` — Progress + CSV/JSON export.
- `/app/frontend/src/pages/SearchPage.jsx`, `PortalsPage.jsx`, `HistoryPage.jsx`, `LoginPage.jsx`.

## Completed
- **2026-07-13**: MVP — auth, Excel master upload, SUNSHOP scraper, encryption, history, screenshots.
- **2026-07-14 (this session)**:
  - Fixed persistent Playwright Chromium: moved browsers to `/app/.pw-browsers/` (survives container resets), added 3-tier fallback in `_get_browser()`.
  - Added asyncio.Lock to serialize browser install retries.
  - Fixed Copy-JSON button — iframe blocks Clipboard API; now uses `document.execCommand('copy')` first.
  - Refactored matcher into `adapters/match.py` — special chars, unit words (mg/ml/tab/cap/tablet/…) and pack sizes (10s/15s) are stripped; strength numbers respected; alphabetic modifiers (xl/sr/xr/dt/am/plus/…) preserved.
  - Word-by-word typing into portal autocompletes.
  - **Built CHETHANA adapter** (`chiragpharma.in`). Extracts Code, Product, Pack, MRP.
  - **Built LIVECONNECT adapter** with OTP session manager. One search → 8 sellers with Stock/MRP/PTR/Scheme.
  - Added `seller` and `manufacturer` fields; CSV + ResultCard show them.
  - **Smart-prefix SUNSHOP search**.
  - **VARDHAMAN adapter** (`easysol.co.in` → `fgtsmg.fortiddns.com:83`).
  - **CHETHANA color-status extraction** — Poll for colored `<tr>`. Verified by testing agent iteration 3 (100% pass).
  - **Distributor `location` field**, city-grouped roster.
  - **Anjaneya-Sanjeevini extraction progress overlay**.
  - **Manual Pick UI** — clickable candidate pills → `POST /api/extract/manual-pick`.
  - **Multi-stage screenshotting during search** (SUNSHOP).
  - **Combo-drug intelligence**: `X/Y`, `X-Y`, and `X Y` unified.
- **2026-07-15 (this session)**:
  - **Shubhada Auto-PO Placement (`/api/order/place`) — END-TO-END WORKING**. Playwright automates the full purchase-order flow on `https://shubhadahealth.com:7007`:
    1. Login `9448188002/Q` → Re-Ordering Process tile.
    2. Clicks the **"Add New Medicine"** link (NOT the top #srch_prd Order Entry search) — opens empty Order Details dialog.
    3. Types product into the dialog's own `Product` input (name=`sprd`).
    4. Types **first 4 letters** of the supplier into Stockist/Supplier → mat-autocomplete → picks the matching option.
    5. Sets Enter Suggested Qty (force-enables the disabled input).
    6. Expands the Patient Details `mat-expansion-panel-header` (by `aria-expanded` check, retries).
    7. Fills Patient Mobile (name=`mob`) → auto-search picks existing patient if match.
    8. Fills Patient Name (name=`pat`) — force-enabled, keyboard-typed for autocomplete, JS-forced if no match.
    9. Fills Quantity (name=`qty`) and Advance Payment (name=`payment`).
    10. Clicks **Add To PO**.
    11. Handles the "**No Patient Found — Created Account / Leave it**" warning by clicking **Created Account** (regex `created?\s*account`).
  - **Async task pattern** (`POST /api/order/place` returns `{task_id}` immediately; frontend polls `GET /api/order/status/{task_id}`) — bypasses Cloudflare's ~100s edge timeout. Verified via curl end-to-end (75s completion).
  - **Frontend**: `OrderAPI.placeAndWait()` helper does submit + poll with elapsed-time indicator. `AddToOrderSheet.jsx` shows `PLACING ORDER… (Ns)` while polling.
  - Verified visually: ROSUVAS F 10 / NEUROBION FORTE / DOLO 650 all landed on the Saved PO table with supplier SAROJ PHARMA and qty 2 / advance 25.

## Pending / Next Tasks
- 🟠 **P1** — Refactor `server.py` (~1250 lines) into `routes/auth.py`, `routes/scraping.py`, `routes/orders.py`, `routes/sessions.py`.
- 🔵 **P2** — SUNSHOP: extract MRP / PTR / Scheme / Batch / Expiry (currently only Stock). Requires user to share screenshots of the SUNSHOP menu that exposes these fields.
- 🔵 **P3** — PDF export of combined results (multi-seller layout).
- 🔵 **P4** — Share-on-WhatsApp button.
- 🔵 **P5** — Best-price finder (auto-highlight seller with lowest PTR).
- 🔵 **P6** — Persist filter chip prefs in localStorage.
- 🔴 **P0 (env)** — VARDHAMAN Shimoga IP-blocked from container. Options: whitelist container IP, use Indian proxy, or skip.

## Known Recurring Issues
- Playwright Chromium binary previously wiped from `/pw-browsers/` on container resets. FIXED — moved to persistent `/app/.pw-browsers/`.
- LIVECONNECT cookies expire after 1–4 weeks. Fallback: adapter returns `LOGIN_FAILED` with `SESSION_EXPIRED` detail so user re-runs the OTP flow.

## API Endpoints
- `POST /api/auth/login`
- `POST /api/extract` — body: `{product, quantity, target_ids: [...]}`
- `POST /api/products/upload` — Excel
- `GET  /api/products/search?q=...`
- `GET  /api/targets` — list distributors
- `POST /api/liveconnect/session/begin` — send OTP (body `{mobile}`)
- `POST /api/liveconnect/session/verify` — verify OTP (body `{pendingId, otp}`)
- `GET  /api/liveconnect/session` — status
- `DELETE /api/liveconnect/session` — clear cookies
- `GET  /api/screenshots/{filename}` — no auth
- `GET  /api/history`, `GET /api/history/{id}`, `DELETE /api/history/{id}`
- `POST /api/order/place` — start Shubhada PO placement, returns `{task_id, status:"running"}` (async).
- `GET  /api/order/status/{task_id}` — poll for `{status:"done", ok, screenshots, steps}`.

## Testing
- Backend: end-to-end curl tests passed for SUNSHOP, CHETHANA, LIVECONNECT (this session).
- Frontend: OTP flow verified end-to-end with live SMS.
- LIVECONNECT sample: `prolomet xl 25` → 5 sellers returned, 1 in stock (Venkatesha 346u @ MRP 68.47, PTR 52.17, 8% scheme).
