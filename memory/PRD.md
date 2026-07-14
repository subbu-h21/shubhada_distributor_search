# PHARMASCRAPE / Shubhada Pharma Sirsi — PRD

## Original Problem Statement
Clone the PHARMASCRAPE distributor-availability lookup app and make it fully functional.
Pharmacist logs into multiple distributor portals (SUNSHOP, CHETHANA, VARDHAMAN),
searches for a product + quantity, and receives live availability, MRP, PTR, Scheme,
and Stock with screenshots.

## Product Requirements
- Mobile-first UI, Space Grotesk font, Green/White theme, branded "SHUBHADA PHARMA SIRSI".
- 4-user JWT login (shared workspace):
  - shubhada / 2612
  - manju / 6387
  - abhishek / 5555
  - narendra / 6666
- Excel Product Master upload → instant frontend autocomplete (35K+ products).
- Playwright (headless Chromium) real-time scraping of distributor portals.
- AES/Fernet-encrypted distributor credentials.
- Screenshots (login / dashboard / results) captured per extraction.

## Tech Stack
- Frontend: React + Tailwind + shadcn UI + lucide-react.
- Backend: FastAPI + Motor (async MongoDB) + Playwright + Pandas/openpyxl.
- Auth/Security: JWT (pyjwt), bcrypt, Fernet AES (cryptography).

## Key Files
- `/app/backend/server.py` — API routes (needs future split into `routes/`).
- `/app/backend/adapters/base.py` — Playwright helpers.
- `/app/backend/adapters/sunshop.py` — SUNSHOP scraping logic (word-by-word autocomplete typing).
- `/app/backend/adapters/generic.py` — Generic scaffold for other portals.
- `/app/backend/auth.py`, `/app/backend/security.py` — Auth & AES helpers.
- `/app/frontend/src/components/ExtractionModal.jsx` — Results modal (Copy JSON, CSV export).
- `/app/frontend/src/pages/SearchPage.jsx` — Product search page.
- `/app/frontend/src/pages/PortalsPage.jsx`, `HistoryPage.jsx`, `LoginPage.jsx`.

## Completed
- **2026-07-13**: Full MVP — auth, Excel master upload, SUNSHOP scraper, encryption, history, screenshots.
- **2026-07-14 (this session)**:
  - Fixed `_get_browser()` — Playwright Chromium was v1208 in `/pw-browsers/`, package expected v1228. Ran `playwright install chromium`; added 3-level fallback (bundled → system chromium → on-the-fly install).
  - Verified extraction end-to-end via curl: SAROJ PHARMA extraction ran successfully (10.3s, NOT_FOUND result with screenshots).
  - Fixed **Copy JSON** button (ExtractionModal): iframe Permissions Policy blocks `navigator.clipboard.writeText` synchronously. Now uses legacy `document.execCommand('copy')` first, falling back to Clipboard API.
  - Refactored SUNSHOP search to type **word-by-word** into the autocomplete instead of only typing the first token — closer to human typing, better matches. Retains the `score >= 22` threshold for exact-variant matching.

## Pending / Next Tasks
- 🔴 **P0** — Build CHETHANA portal adapter (`chethanapharma.in` / `chiragpharma.in`).
- 🟡 **P1** — Build VARDHAMAN portal adapter (`easysol.co.in`).
- 🟠 **P2** — Extract MRP / PTR / Scheme / Batch / Expiry from SUNSHOP. Need user to identify which SUNSHOP menu exposes these fields (currently only Stock from Order Feed).
- 🔵 **P3** — PDF/CSV combined export of extraction results.
- 🧹 **Refactor** `server.py` (~880 lines) → split into `routes/auth.py`, `routes/scraping.py`, `routes/products.py`.

## Known Recurring Issues
- Playwright Chromium binary occasionally wiped from `/pw-browsers/` on environment reset. Auto-recovery is in place, but if extraction 500s again, verify `/pw-browsers/chromium_headless_shell-1228/` exists or run `playwright install chromium`.

## API Endpoints
- `POST /api/auth/login`
- `POST /api/extract` — body: `{product, quantity, target_ids: [...]}`
- `POST /api/products/upload` — Excel
- `GET  /api/products/search?q=...`
- `GET  /api/targets` — list distributors
- `GET  /api/screenshots/{filename}` — no auth (so `<img src>` works)
- `GET  /api/history`, `GET /api/history/{id}`

## Testing
- Backend: `deep_testing_backend_v2` passed.
- Curl verified extraction end-to-end after Chromium fix.
- Frontend: pending user verification after word-by-word typing change.
