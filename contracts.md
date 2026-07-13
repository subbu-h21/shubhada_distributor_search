# PHARMASCRAPE API Contracts

## Overview
Convert the mock-based PHARMASCRAPE frontend into a real full-stack app.
Backend: FastAPI + MongoDB (Motor). All routes are prefixed with `/api`.

## Mocked → Real Data Mapping

Data currently mocked in `/app/frontend/src/mock.js`:
- `PORTALS`             → seeded in `portals` collection at startup
- `DEFAULT_TARGETS`     → seeded in `targets` collection at startup
- `HISTORY`             → seeded in `history` collection at startup
- `generateExtractionResults(product, targets)` → replaced by backend `/api/extract` endpoint (server-side mock scraper for MVP)

After integration, `mock.js` will only remain as a fallback seed reference (not imported by pages).

## MongoDB Collections

### `portals`
```
{ _id, id, name, baseUrl, status ("ACTIVE"|"INACTIVE"), description }
```

### `targets`
```
{ _id, id, name, url, portal, selected (bool), created_at }
```

### `history`
```
{ _id, id, product, timestamp, duration, targetsRun, found, outOfStock, errors, status, results: [ExtractionResult] }
```

### ExtractionResult (embedded)
```
{ targetId, targetName, portal, url, product, status ("IN_STOCK"|"OUT_OF_STOCK"|"ERROR"), price, mrp, stock, pack, responseMs, lastUpdated }
```

## REST Endpoints (all prefixed with `/api`)

### Portals
- `GET  /api/portals` → list all portals
- `POST /api/portals` → create portal (name, baseUrl, description, status)

### Targets
- `GET    /api/targets`         → list targets
- `POST   /api/targets`         → create target { name, url, portal, selected? }
- `PATCH  /api/targets/{id}`    → update target (selected toggle etc.)
- `DELETE /api/targets/{id}`    → remove target
- `POST   /api/targets/bulk-select` → { selected: bool } select/deselect all

### Extraction
- `POST /api/extract` → body: { product, target_ids: [id] }
  - Runs server-side mock scraper (adds latency per target)
  - Persists a history entry
  - Returns the full history entry (with results)

### History
- `GET    /api/history`         → list history (newest first)
- `GET    /api/history/{id}`    → detailed entry with results
- `DELETE /api/history/{id}`    → remove entry

## Frontend Integration Plan

1. Replace `AppContext.js` local-state initialization with API calls:
   - On mount: `GET /api/targets`, `GET /api/history`
   - `toggleTarget(id)` → `PATCH /api/targets/{id}` with `{ selected }`
   - `addTarget(t)`     → `POST /api/targets`
   - `removeTarget(id)` → `DELETE /api/targets/{id}`
   - `runExtraction()`  → `POST /api/extract { product, target_ids }` then prepend result to history
2. `PortalsPage` → fetch from `GET /api/portals`
3. `HistoryPage`/`HistoryDetail` → fetch `GET /api/history/{id}` on card open
4. Remove imports of mock data from pages/context. Keep `/app/frontend/src/mock.js` for reference only.
5. All fetch calls use `process.env.REACT_APP_BACKEND_URL + '/api/...'` via a small `api.js` helper (axios).

## Non-Goals for MVP
- Real portal scraping (SUNSHOP/CHETHANA/VARDHAMAN parsing) — deferred; extraction service is a deterministic mock scraper on the backend.
- Auth — not requested.
- Rate limiting, retries — not needed for MVP.
