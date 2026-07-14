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
| CHETHANA (CHIRAG PHARMA / chiragpharma.in) | ✅ Live | Code, Product, Pack, MRP |
| LIVECONNECT (8 sellers via search-all-sellers) | ✅ Live | Seller, Product, Mfr, Pack, MRP, PTR, Stock, Scheme, Tax |
| VARDHAMAN Shimoga (`fgtsmg.fortiddns.com:83`) | ⚠️ IP-blocked from container (port 83 refuses non-Indian IPs) |

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
    - New API endpoints: `POST /api/liveconnect/session/begin`, `/verify`, `GET /session`, `DELETE /session`.
    - New UI: LIVECONNECT SESSION item in user-avatar dropdown.
  - Added `seller` and `manufacturer` fields to `ExtractedItem`; CSV + ResultCard show them.
  - **Smart-prefix SUNSHOP search**: type first 4 chars → collect suggestions → canonical-score → click best. Progressive lengthening (4→5→6→…→full) and fallback to shorter (3, 2). Massive accuracy improvement — SAROJ, HEGDE now return SUCCESS where they returned NOT_FOUND. When genuinely not stocked, response lists the distributor's *nearest* SKUs.
  - **Multi-stage screenshotting during search** (SUNSHOP): Types in escalating stages — `PROL` → `PROLOMET` → `PROLOMET XL` → `PROLOMET XL 25`. Captures a screenshot per stage AND accumulates candidates in a unique-name pool. After all stages, picks the highest-scoring unique suggestion across the union of all stages. UI shows all 4 stage screenshots so the pharmacist can audit exactly what the distributor's autocomplete offered at each typing depth.
  - **Combo-drug intelligence**: `X/Y`, `X-Y`, and `X Y` (two consecutive dosage numbers) are now canonicalized to a single `X/Y` token, and a query of `X` matches a candidate of `X/Y` as a combo variant (score 45). Handles:
    - `ECOSPRIN AV 75` ≡ `ECOSPRIN AV 75/10` ≡ `ECOSPRIN AV 75 10` ≡ `ECOSPRIN AV 75-10` ≡ `ECOSPRIN AV 75 CAPSULES` (all match). Different primary strength (`75` vs `150`) still fails.
    - `TELMIKIND AM 40` matches `TELMIKIND AM 40/5`, does NOT match `TELMIKIND AM 80`.

## Pending / Next Tasks
- 🔴 **P0** — VARDHAMAN Shimoga is IP-blocked from our overseas container. Options: (a) whitelist container IP with VARDHAMAN admin, (b) route through an Indian proxy, (c) skip.
- 🟠 **P1** — Add remaining LIVECONNECT sellers if any (currently 8 auto-discovered from `stkchem-new` endpoint).
- 🟠 **P2** — SUNSHOP: extract MRP / PTR / Scheme / Batch / Expiry (currently only Stock). Requires user to identify the SUNSHOP menu that exposes these fields.
- 🔵 **P3** — PDF export of combined results.
- 🧹 Refactor `server.py` (~950 lines) into `routes/auth.py`, `routes/scraping.py`, `routes/products.py`, `routes/liveconnect.py`.

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

## Testing
- Backend: end-to-end curl tests passed for SUNSHOP, CHETHANA, LIVECONNECT (this session).
- Frontend: OTP flow verified end-to-end with live SMS.
- LIVECONNECT sample: `prolomet xl 25` → 5 sellers returned, 1 in stock (Venkatesha 346u @ MRP 68.47, PTR 52.17, 8% scheme).
