# PHARMASCRAPE — PRD

## Original Problem Statement
Pharmacist tool to search product availability across many distributor portals in
one query and place auto-POs. Mobile-first, Space Grotesk / Green-White theme,
4-user shared workspace, headless-browser scraping via Playwright + fuzzy match,
Distributor Price-List Vault (offline Excel/PDF catalog search).

## Implemented (chronological)

### Feb 2026
- ShubhadaHealth Auto-PO placement (async task + polling)
- Hanumanji Hero Banner + CSS float animation
- Distributor Price-List Vault (100k+ row Excel/PDF ingest, dedupe, disk-caching, `.xls` support, header-row detection, duplicate-column-name safe)
- **Fix**: Bottom-nav layout — was `grid-cols-3` with 4 tabs, causing HISTORY to wrap and hide RUN EXTRACTION. Now `grid-cols-4`.
- **NEW MARG PORTAL** (this session):
  - OTP session manager `/backend/marg_session.py` (mobile → Login with OTP button → OTP → cookies)
  - Adapter `/backend/adapters/marg.py` (session-cookie, Search Supplier → ALL → product → parse Stock/MRP/PTR/Scheme)
  - Endpoints: `GET /api/marg/session`, `POST /api/marg/session/begin`, `POST /api/marg/session/verify`, `DELETE /api/marg/session`
  - Auto-seeded distributor **MARG (ALL SUPPLIERS)** — enabled by default in SEARCH
  - Frontend: `MargOtpSheet.jsx`, `MargAPI` in `lib/api.js`, "MARG SESSION" menu item in user dropdown

## Distributors currently seeded (17)
SAROJ · HEGDE · KAPILA PHARMA · KAPILA MEDICAL · CHIRAG · CHETHANA · VARDHAMAN · A.K.PHARMA (x2) · LIVECONNECT (ALL SELLERS) · RETAILIO · YASHIKA · MARG (ALL SUPPLIERS) · …

## Backlog (P0 → P3)
- **P0** Verify MARG scrape end-to-end after user's first OTP login (selectors on authed Search Supplier screen may need one refinement pass — currently heuristic-based).
- **P0** Verify Kapila 25,997-row `.xls` upload in Price-List Vault (previous fix pending user retest).
- **P1** Refactor `server.py` (1300+ lines) into `routes/*.py` modules.
- **P2** "Placed Orders" history page (today's auto-POs + screenshots).
- **P3** SUNSHOP MRP/PTR/Batch/Expiry — needs UI screenshot from user.
- **P3** PDF export of combined search results.
- **P3** "Share on WhatsApp" button.
- **P3** Best-Price finder (auto-highlight lowest PTR).
- **P3** Persist filter preferences to localStorage.

## Test credentials
See `/app/memory/test_credentials.md`.

## Critical Notes for Future Agents
- MARG adapter's Search-Supplier flow uses heuristic selectors. On the first live
  test if items come back empty despite a valid session, inspect Playwright
  screenshot output (in `data/screenshots/`) and refine `_open_search_supplier`
  and the row-selector list in `/app/backend/adapters/marg.py`.
- Do NOT revert `pricelist.py` `.pkl` disk cache back to in-memory (hot-reload
  wipes memory during two-step upload flow).
- `/api/order/place` MUST stay async (fire-and-poll) — Cloudflare drops sync
  connections at 100s and MARG/Shubhada POs can take ~120s.
