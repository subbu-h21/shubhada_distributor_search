"""Distributor Price-List Vault.

Pharmacists frequently receive Excel / native-PDF price lists via email or
WhatsApp from their distributors. This module lets them upload each file
once, auto-detects which distributor it belongs to, parses the tabular
rows, saves a canonical mapping (Product Name → MRP / PTR / Scheme /
Company) per distributor, and then makes the whole thing instantly
searchable.

Endpoints exposed by `register_routes(api_router, db)`:
    POST   /api/pricelist/upload      form-data file → returns preview + mapping suggestion
    POST   /api/pricelist/confirm     JSON body with confirmed mapping → replaces rows
    GET    /api/pricelist/search?q=X  → grouped results {product → [distributor rows]}
    GET    /api/pricelist/summary     → per-distributor row counts & last-uploaded

MongoDB collections used:
    pricelist_uploads   { _id, distributor_id, distributor_name, filename, row_count, uploaded_at }
    pricelist_rows      { _id, distributor_id, distributor_name, product, product_norm,
                          company, pack, mrp, ptr, scheme, uploaded_at, source_upload }
    pricelist_mappings  { _id: distributor_id, columns: {product: "COL_A", company: "COL_C", ...},
                          updated_at }
"""
from __future__ import annotations
import io
import os
import pickle
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

# Pending uploads awaiting user confirmation of the column mapping.
# We persist the parsed DataFrame to disk (as a lightweight pickle) so a
# backend restart during file review does NOT lose the user's work — a
# critical protection for large uploads that take time to finalise.
_PENDING_DIR = Path(os.environ.get("PRICELIST_PENDING_DIR", str(Path(__file__).parent / "data/pricelist_pending")))
_PENDING_DIR.mkdir(parents=True, exist_ok=True)
_PENDING_TTL_SECS = 3600  # 1 hour


def _pending_path(token: str) -> Path:
    # Basic guard: 12-hex only
    if not re.fullmatch(r"[a-f0-9]+", token or ""):
        raise HTTPException(400, "Invalid token")
    return _PENDING_DIR / f"{token}.pkl"


def _pending_save(token: str, df: pd.DataFrame, filename: str) -> None:
    payload = {"df": df, "filename": filename, "saved_at": datetime.now(timezone.utc)}
    with _pending_path(token).open("wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)


def _pending_load(token: str) -> Optional[Dict[str, Any]]:
    p = _pending_path(token)
    if not p.exists(): return None
    with p.open("rb") as f:
        payload = pickle.load(f)
    return payload


def _pending_delete(token: str) -> None:
    p = _pending_path(token)
    if p.exists():
        try: p.unlink()
        except Exception: pass


def _pending_gc() -> None:
    """Sweep pending uploads older than TTL. Called on each new upload."""
    now = datetime.now(timezone.utc).timestamp()
    for p in _PENDING_DIR.glob("*.pkl"):
        try:
            if now - p.stat().st_mtime > _PENDING_TTL_SECS:
                p.unlink()
        except Exception:
            pass


# ------------ Canonical helpers ------------

def _canon(s: str) -> str:
    """Same canonicalisation used elsewhere in the app — strips units, pack
    sizes, and non-alphanumerics so 'DOLO 650 MG (15S)' and 'Dolo-650' both
    hash to the same token."""
    if not s: return ""
    s = str(s).upper()
    s = re.sub(r"\([^)]*\)", " ", s)  # drop parentheticals like "(15S)"
    s = re.sub(r"\b(TAB|TABLET|CAP|CAPSULE|SYP|SYRUP|INJ|INJECTION|CREAM|OINTMENT|GEL|LOTION|DROPS?|POWDER|SUSP|SR|XR|XL|MG|ML|GM|GMS|MCG|IU|LTR|LTRS?)\b", " ", s)
    s = re.sub(r"\b\d+\s*S\b", " ", s)  # pack sizes like "15S"
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ------------ Column auto-detection ------------

_FIELD_PATTERNS: Dict[str, List[str]] = {
    "product":  [r"\bproduct\b", r"\bitem\b", r"\bname\b", r"\bmedicine\b", r"\bdrug\b", r"\bdescription\b", r"\bparticular"],
    "company":  [r"\bcompan", r"\bmanufactur", r"\bmfr\b", r"\bmfg\b", r"\bmaker\b", r"\bbrand\s*by\b"],
    "pack":     [r"\bpack\b", r"\bpacking\b", r"\bsize\b", r"\bqty\b", r"\bunit\b"],
    "mrp":      [r"\bmrp\b", r"\bm\.?r\.?p\.?\b", r"\bmax(imum)?\s*retail", r"\bretail\s*price"],
    "ptr":      [r"\bptr\b", r"\bp\.?t\.?r\.?\b", r"\brate\b", r"\bnet\s*rate", r"\bselling\s*price", r"\bs\.?p\.?\b", r"\bwholes"],
    "scheme":   [r"\bscheme\b", r"\boffer\b", r"\bfree\b", r"\bdisc(ount)?\b", r"\b\+\d\b"],
}


def _match_column(field: str, headers: List[str]) -> Optional[str]:
    """Return the header (case-preserved) that best matches `field` per
    _FIELD_PATTERNS. None if no header matches."""
    lows = [(h, h.lower().strip()) for h in headers]
    for pat in _FIELD_PATTERNS[field]:
        rx = re.compile(pat, re.I)
        for orig, low in lows:
            if rx.search(low):
                return orig
    return None


def auto_detect_columns(headers: List[str]) -> Dict[str, Optional[str]]:
    return {field: _match_column(field, headers) for field in _FIELD_PATTERNS}


# ------------ Distributor auto-detection ------------

# Generic words that appear in many distributor names — must NOT count
# toward a match by themselves. Only distinctive tokens qualify.
_GENERIC_TOKENS = {
    "PHARMA", "PHARMACY", "PHARMACEUTICAL", "PHARMACEUTICALS", "PHARMACIES",
    "MEDICAL", "MEDICALS", "MEDICINES", "MEDICINE",
    "AGENCIES", "AGENCY",
    "STORES", "STORE",
    "BROTHER", "BROTHERS", "BROS",
    "PVT", "LTD", "LIMITED", "PRIVATE", "COMPANY", "CO",
    "TRADERS", "TRADING", "TRADE",
    "SUPPLIERS", "SUPPLY", "SUPPLIES",
    "ENTERPRISE", "ENTERPRISES",
    "DISTRIBUTORS", "DISTRIBUTOR", "DISTRIBUTION",
    "SALES", "SALES", "MEDISALES", "MEDISTOCK",
    "PRODUCTS", "PRODUCT",
    "AGENCIES",
    "ALL", "SELLERS",
}


def detect_distributor(filename: str, sample_text: str, known: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Try to find which of the known distributors this file belongs to.

    A distributor matches only if one of its DISTINCTIVE tokens (length >= 4
    and not in _GENERIC_TOKENS) appears in the filename or first ~2KB of
    file content. Ties are broken by which token appears earliest in the
    filename (filename takes precedence over body).
    """
    fn_up = filename.upper()
    body_up = sample_text.upper()
    best = None
    best_score = -1
    best_fn_hit = False
    for d in known:
        name = (d.get("name") or "").upper()
        if not name: continue
        tokens = [
            t for t in re.split(r"[^A-Z0-9]+", name)
            if len(t) >= 4 and t not in _GENERIC_TOKENS
        ]
        if not tokens: continue
        fn_hit = any(t in fn_up for t in tokens)
        body_hit = any(t in body_up for t in tokens)
        # Filename match strongly preferred; body match still counts.
        if fn_hit:
            score = 10 + sum(1 for t in tokens if t in fn_up)
        elif body_hit:
            score = 1 + sum(1 for t in tokens if t in body_up)
        else:
            score = 0
        if score > best_score:
            best_score = score
            best = d
            best_fn_hit = fn_hit
    return best if best_score >= 1 else None


# ------------ File parsing ------------

def _find_header_row(rows: List[List[str]]) -> int:
    """Scan the first ~20 rows and pick the one that most looks like a
    header — the first row where at least 3 cells are non-empty short
    strings that don't parse as numbers AND aren't pandas' 'Unnamed:'
    placeholder from an earlier read.
    """
    def is_real_label(cell: str) -> bool:
        s = str(cell).strip()
        if not s: return False
        if s.lower().startswith("unnamed"): return False
        if s.lower() in ("nan", "none", "null"): return False
        try:
            float(s.replace(",", ""))
            return False   # numeric — not a label
        except Exception:
            return True

    for idx in range(min(20, len(rows))):
        r = rows[idx]
        labels = [c for c in r if is_real_label(c)]
        if len(labels) >= 3:
            return idx
    return 0


def _reheader(df: pd.DataFrame) -> pd.DataFrame:
    """If the raw DataFrame has mostly-blank / Unnamed: columns (i.e. the
    real header wasn't on row 1), scan the body for a plausible header row
    and promote it. Silently returns df unchanged if headers look fine."""
    good_hdrs = [c for c in df.columns if str(c).strip() and not str(c).lower().startswith("unnamed")]
    if len(good_hdrs) >= 3:
        # Headers look OK — just drop the empty/unnamed columns.
        return df.loc[:, good_hdrs]
    # Otherwise: read raw rows and find the header inside.
    rows = [df.columns.tolist()] + df.values.tolist()
    rows = [[("" if c is None else str(c)) for c in r] for r in rows]
    hdr_idx = _find_header_row(rows)
    header = [str(x).strip() or f"col_{i+1}" for i, x in enumerate(rows[hdr_idx])]
    body = rows[hdr_idx + 1:]
    # Normalise width
    width = len(header)
    body = [(r + [""] * width)[:width] for r in body]
    return pd.DataFrame(body, columns=header)


def _parse_xls_or_csv(data: bytes, filename: str) -> pd.DataFrame:
    lower = filename.lower()
    bio = io.BytesIO(data)
    if lower.endswith(".csv"):
        return pd.read_csv(bio, dtype=str, keep_default_na=False)
    # Pick the correct Excel engine explicitly — `engine=None` fails when
    # the file magic-bytes are ambiguous or non-standard.
    if lower.endswith(".xls"):
        # Old binary Excel 97-2003 → xlrd
        try:
            return pd.read_excel(bio, dtype=str, engine="xlrd")
        except Exception:
            bio.seek(0)
    if lower.endswith(".xlsx"):
        try:
            return pd.read_excel(bio, dtype=str, engine="openpyxl")
        except Exception:
            bio.seek(0)
    # Fallback: try both engines in turn, then let pandas throw a clean
    # error for the user.
    for eng in ("openpyxl", "xlrd", None):
        try:
            bio.seek(0)
            return pd.read_excel(bio, dtype=str, engine=eng)
        except Exception:
            continue
    raise HTTPException(400, "Unable to read this Excel file. Please re-save as .xlsx (Excel 2007+ format) and try again.")


def _parse_pdf(data: bytes) -> pd.DataFrame:
    """Extract the LARGEST tabular grid found across all pages of a native
    (non-scanned) PDF. Returns a DataFrame with the first row treated as
    the header if it looks like text labels."""
    import pdfplumber
    rows: List[List[str]] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            for tbl in page.extract_tables() or []:
                if len(tbl) < 2: continue
                for r in tbl:
                    rows.append([("" if c is None else str(c).strip()) for c in r])
    if not rows:
        raise HTTPException(400, "No tabular data found in the PDF. Is it a scanned image? (OCR is not supported yet.)")
    # Normalise widths — every row padded to max cols
    max_cols = max(len(r) for r in rows)
    rows = [r + [""] * (max_cols - len(r)) for r in rows]
    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df


def parse_file(data: bytes, filename: str) -> pd.DataFrame:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _parse_pdf(data)
    if lower.endswith((".xlsx", ".xls", ".csv")):
        return _parse_xls_or_csv(data, filename)
    raise HTTPException(400, "Unsupported file type. Please upload .xlsx, .xls, .csv, or .pdf")


# ------------ Row normalisation ------------

_NUM_RX = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _to_float(v: Any) -> Optional[float]:
    if v is None: return None
    s = str(v).strip()
    if not s: return None
    m = _NUM_RX.search(s.replace(",", ""))
    return float(m.group()) if m else None


def normalise_rows(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> List[Dict[str, Any]]:
    """Apply the mapping to produce clean dicts. Drops rows where the
    product name is empty. Deduplicates by canonical product name — later
    duplicates overwrite earlier ones (last-wins per distributor)."""
    if not mapping.get("product"):
        raise HTTPException(400, "Please map the 'Product' column — it is mandatory.")
    prod_col = mapping["product"]
    if prod_col not in df.columns:
        raise HTTPException(400, f"Mapped Product column '{prod_col}' not found in file.")

    dedup: Dict[str, Dict[str, Any]] = {}
    for _, r in df.iterrows():
        raw_prod = str(r.get(prod_col, "")).strip()
        if not raw_prod or raw_prod.lower() in ("nan", "none"): continue
        norm = _canon(raw_prod)
        if not norm: continue
        entry = {
            "product": raw_prod,
            "product_norm": norm,
            "company": str(r.get(mapping.get("company") or "", "")).strip() if mapping.get("company") else "",
            "pack":    str(r.get(mapping.get("pack") or "", "")).strip() if mapping.get("pack") else "",
            "mrp":     _to_float(r.get(mapping.get("mrp"))) if mapping.get("mrp") else None,
            "ptr":     _to_float(r.get(mapping.get("ptr"))) if mapping.get("ptr") else None,
            "scheme":  str(r.get(mapping.get("scheme") or "", "")).strip() if mapping.get("scheme") else "",
        }
        dedup[norm] = entry
    return list(dedup.values())


# ============================================================
# Route registration
# ============================================================


class ConfirmRequest(BaseModel):
    token: str
    distributor_id: Optional[str] = None  # override auto-detection
    mapping: Dict[str, Optional[str]]     # {product: "Column A", company: "Column C", ...}
    save_mapping: bool = True             # persist mapping for this distributor?


def register_routes(api_router: APIRouter, db) -> None:

    @api_router.post("/pricelist/upload")
    async def pricelist_upload(file: UploadFile = File(...)):
        """Step 1: parse the uploaded file, auto-detect distributor & columns,
        return a preview (first 5 rows) + suggested column mapping. Frontend
        then displays a mapping UI for user confirmation.
        Returns:
            {
              token,
              filename, rows: N,
              detected_distributor: {id, name} | null,
              headers: [...],
              preview: [{col: val, ...}, ...5],
              mapping_suggested: {product, company, pack, mrp, ptr, scheme},
              mapping_saved:     {...} | null,   (if this distributor had a saved mapping)
            }
        """
        if not file.filename:
            raise HTTPException(400, "No filename")
        data = await file.read()
        if not data:
            raise HTTPException(400, "Empty file")

        df = parse_file(data, file.filename)
        if df.empty:
            raise HTTPException(400, "File contains no data rows")

        # Smart header detection — if the first row isn't a real header
        # (e.g. file starts with a title / blank row), scan for it.
        df = _reheader(df)
        if len(df.columns) == 0:
            raise HTTPException(400, "Could not detect column headers. Please open the file, ensure row 1 has column names (Product, MRP, Rate, etc.), and re-save.")
        headers = [str(c) for c in df.columns]

        # Auto-detect distributor
        distributors = [d async for d in db.targets.find({}, {"name": 1, "location": 1, "id": 1})]
        for d in distributors:
            d["id"] = d.get("id") or str(d.get("_id"))
        # Grab first ~2KB of stringified rows as heuristic
        sample_text = df.head(20).to_csv(index=False)[:2000]
        detected = detect_distributor(file.filename, sample_text, distributors)

        # Any previously-saved mapping for this distributor?
        saved_mapping = None
        if detected:
            saved = await db.pricelist_mappings.find_one({"_id": detected["id"]})
            if saved:
                saved_mapping = saved.get("columns")

        _pending_gc()
        token = uuid.uuid4().hex[:12]
        _pending_save(token, df, file.filename)

        return {
            "token": token,
            "filename": file.filename,
            "rows": int(len(df)),
            "detected_distributor": ({"id": detected["id"], "name": detected["name"]} if detected else None),
            "headers": headers,
            "preview": df.head(5).fillna("").astype(str).to_dict(orient="records"),
            "mapping_suggested": auto_detect_columns(headers),
            "mapping_saved": saved_mapping,
        }

    @api_router.post("/pricelist/confirm")
    async def pricelist_confirm(payload: ConfirmRequest):
        """Step 2: apply confirmed mapping → replace this distributor's rows."""
        pending = _pending_load(payload.token)
        if not pending:
            raise HTTPException(400, "Upload session expired. Please re-upload the file.")
        if not payload.distributor_id:
            raise HTTPException(400, "distributor_id is required")

        # Look up distributor (stored in `targets` collection with string `id`)
        dist = await db.targets.find_one({"id": payload.distributor_id})
        if not dist:
            raise HTTPException(404, "Distributor not found")

        df = pending["df"].fillna("")

        rows = normalise_rows(df, payload.mapping)
        if not rows:
            raise HTTPException(400, "No valid rows found after applying mapping (product column may be empty).")

        now = datetime.now(timezone.utc)
        upload_id = uuid.uuid4().hex

        # REPLACE mode (per user spec)
        await db.pricelist_rows.delete_many({"distributor_id": payload.distributor_id})

        docs = []
        for r in rows:
            docs.append({
                **r,
                "distributor_id": payload.distributor_id,
                "distributor_name": dist.get("name") or "",
                "source_upload": upload_id,
                "uploaded_at": now,
            })
        # Chunk inserts so 100k-row uploads don't stall the driver
        CHUNK = 5000
        inserted = 0
        for i in range(0, len(docs), CHUNK):
            await db.pricelist_rows.insert_many(docs[i:i + CHUNK], ordered=False)
            inserted += len(docs[i:i + CHUNK])

        # Ensure fast lookup at any scale — indexes are idempotent, cheap to
        # re-declare, and only actually built once.
        await db.pricelist_rows.create_index("product_norm")
        await db.pricelist_rows.create_index("distributor_id")
        await db.pricelist_rows.create_index([("distributor_id", 1), ("product_norm", 1)])

        # Record the upload
        await db.pricelist_uploads.insert_one({
            "_id": upload_id,
            "distributor_id": payload.distributor_id,
            "distributor_name": dist.get("name") or "",
            "filename": pending["filename"],
            "row_count": len(docs),
            "uploaded_at": now,
        })

        # Save mapping for next time
        if payload.save_mapping:
            await db.pricelist_mappings.update_one(
                {"_id": payload.distributor_id},
                {"$set": {"columns": payload.mapping, "updated_at": now}},
                upsert=True,
            )

        # Cleanup: pending upload is done — remove the on-disk temp file
        _pending_delete(payload.token)

        return {
            "ok": True,
            "distributor": dist.get("name"),
            "rows_inserted": len(docs),
            "mapping_saved": payload.save_mapping,
        }

    @api_router.get("/pricelist/search")
    async def pricelist_search(q: str = ""):
        """Fuzzy-search across all uploaded distributor rows. Returns rows
        grouped by canonical product. Empty q → returns [] (frontend can
        show a hint instead of dumping the whole DB)."""
        q_norm = _canon(q)
        if not q_norm or len(q_norm) < 2:
            return {"query": q, "count": 0, "groups": []}

        # Split on whitespace; every token must be a substring of product_norm.
        # We build a $regex $and to keep it fast enough at 10-100k rows.
        tokens = q_norm.split()
        clauses = [{"product_norm": {"$regex": re.escape(t), "$options": "i"}} for t in tokens]
        cursor = db.pricelist_rows.find({"$and": clauses}).limit(500)

        groups: Dict[str, Dict[str, Any]] = {}
        async for r in cursor:
            key = r.get("product_norm") or r.get("product") or ""
            g = groups.setdefault(key, {
                "product": r.get("product"),
                "product_norm": key,
                "company": r.get("company") or "",
                "distributors": [],
            })
            # If a company isn't set yet on the group, adopt the first non-empty one
            if not g["company"] and r.get("company"):
                g["company"] = r["company"]
            g["distributors"].append({
                "distributor_id": r.get("distributor_id"),
                "distributor_name": r.get("distributor_name") or "",
                "pack": r.get("pack") or "",
                "mrp": r.get("mrp"),
                "ptr": r.get("ptr"),
                "scheme": r.get("scheme") or "",
                "uploaded_at": r.get("uploaded_at").isoformat() if r.get("uploaded_at") else None,
            })

        # Sort each group's distributors by cheapest PTR (None = last)
        for g in groups.values():
            g["distributors"].sort(key=lambda d: (d["ptr"] is None, d["ptr"] or 0))
            g["cheapest_ptr"] = next((d["ptr"] for d in g["distributors"] if d["ptr"] is not None), None)

        # Sort groups: closest match to q first
        result = sorted(groups.values(), key=lambda g: (
            0 if g["product_norm"] == q_norm else 1,
            0 if g["product_norm"].startswith(q_norm.split()[0]) else 1,
            len(g["product_norm"]),
        ))
        return {"query": q, "count": len(result), "groups": result[:100]}

    @api_router.get("/pricelist/summary")
    async def pricelist_summary():
        """Per-distributor upload stats for the UI dashboard."""
        pipeline = [
            {"$group": {
                "_id": "$distributor_id",
                "distributor_name": {"$last": "$distributor_name"},
                "row_count":  {"$sum": 1},
                "last_upload": {"$max": "$uploaded_at"},
            }},
            {"$sort": {"distributor_name": 1}},
        ]
        results = [r async for r in db.pricelist_rows.aggregate(pipeline)]
        for r in results:
            r["distributor_id"] = r.pop("_id")
            if r.get("last_upload"):
                r["last_upload"] = r["last_upload"].isoformat()
        total = sum(r["row_count"] for r in results)
        return {"total_rows": total, "distributors": results}

    @api_router.delete("/pricelist/distributor/{distributor_id}")
    async def pricelist_clear_distributor(distributor_id: str):
        """Wipe all rows for one distributor (useful before re-uploading)."""
        res = await db.pricelist_rows.delete_many({"distributor_id": distributor_id})
        return {"deleted": res.deleted_count}
