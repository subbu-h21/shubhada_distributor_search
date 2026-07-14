from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Query, Header, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import re
import io
import logging
import asyncio
import random
import uuid
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env', override=True)

# Configure Playwright browsers path BEFORE importing playwright
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/pw-browsers"))

from security import encrypt_secret, decrypt_secret
from auth import hash_password, verify_password, create_token, decode_token, bearer_from_header
from adapters import get_adapter

# Playwright is imported lazily inside extraction to keep app startup snappy
_playwright = None
_browser_install_lock = asyncio.Lock()


# --- Screenshot directory ---
SCREENSHOTS_DIR = Path(os.environ.get("SCREENSHOTS_DIR", str(ROOT_DIR / "data/screenshots")))
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
RETENTION_DAYS = int(os.environ.get("SCREENSHOT_RETENTION_DAYS", "7"))

# --- DB setup ---
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# --- App ---
app = FastAPI(title="PharmaScrape API")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("server")


# ============================================================
# MODELS
# ============================================================
class Portal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    baseUrl: str
    status: str = "ACTIVE"
    description: Optional[str] = ""


class PortalCreate(BaseModel):
    name: str
    baseUrl: str
    status: str = "ACTIVE"
    description: Optional[str] = ""


class Distributor(BaseModel):
    """Distributor with credentials. Password never returned in responses."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    url: str
    portal: str                 # e.g. "SUNSHOP" | "CHETHANA" | "VARDHAMAN"
    portalType: str = "GENERIC" # adapter to use — SUNSHOP | GENERIC etc.
    username: Optional[str] = None
    hasCredentials: bool = False
    selected: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DistributorCreate(BaseModel):
    name: str
    url: str
    portal: str
    portalType: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    selected: bool = True


class DistributorUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    portal: Optional[str] = None
    portalType: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    selected: Optional[bool] = None


class BulkSelect(BaseModel):
    selected: bool


class ExtractRequest(BaseModel):
    product: str
    quantity: Optional[int] = None
    target_ids: List[str]


class TestLoginResponse(BaseModel):
    ok: bool
    detail: str
    screenshot: Optional[str] = None


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    name: Optional[str] = None
    isAdmin: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class LoginResponse(BaseModel):
    token: str
    user: User


# ============================================================
# HELPERS
# ============================================================
def strip_mongo(doc: dict) -> dict:
    if not doc:
        return doc
    doc.pop("_id", None)
    doc.pop("encryptedPassword", None)  # never expose
    return doc


def infer_portal_type(portal: str) -> str:
    p = (portal or "").upper()
    if "SUNSHOP" in p:
        return "SUNSHOP"
    return "GENERIC"


async def _get_browser():
    """Launch a shared Playwright browser instance. Auto-recovers if the
    Chromium executable was wiped between sessions. Uses a persistent
    PLAYWRIGHT_BROWSERS_PATH (see .env) so browsers survive across
    ephemeral container resets."""
    global _playwright
    import sys
    from playwright.async_api import async_playwright
    if _playwright is None:
        _playwright = await async_playwright().start()

    launch_args = ["--no-sandbox", "--disable-dev-shm-usage"]

    async with _browser_install_lock:
        # 1) Try Playwright's bundled chromium first
        try:
            return await _playwright.chromium.launch(headless=True, args=launch_args)
        except Exception as e:
            err = str(e)
            logger.warning(f"Bundled chromium launch failed: {err[:200]}")

        # 2) Try system chromium (persists across environment resets)
        for candidate in ("/root/chromium-persistent/chromium", "/usr/bin/chromium", "/root/bin/chromium"):
            if os.path.exists(candidate):
                try:
                    logger.info(f"Falling back to system chromium at {candidate}")
                    return await _playwright.chromium.launch(
                        headless=True,
                        executable_path=candidate,
                        args=launch_args,
                    )
                except Exception as e2:
                    logger.warning(f"System chromium at {candidate} failed: {str(e2)[:200]}")

        # 3) Last resort — install playwright chromium on the fly using
        # the current python interpreter (so PATH issues don't matter).
        logger.warning("All chromium candidates failed — running `python -m playwright install chromium`...")
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "playwright", "install", "chromium",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        logger.info(f"playwright install exit={proc.returncode} stdout={(stdout or b'')[:200]!r} stderr={(stderr or b'')[:200]!r}")
        return await _playwright.chromium.launch(headless=True, args=launch_args)


async def _cleanup_old_screenshots():
    """Delete screenshots older than RETENTION_DAYS."""
    try:
        cutoff = datetime.now().timestamp() - RETENTION_DAYS * 86400
        removed = 0
        for f in SCREENSHOTS_DIR.glob("*.png"):
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink(missing_ok=True)
                    removed += 1
            except Exception:
                pass
        if removed:
            logger.info(f"Cleaned up {removed} old screenshot(s)")
    except Exception as e:
        logger.warning(f"Screenshot cleanup failed: {e}")


async def seed_if_empty():
    """Seed portals + distributors + users if collections are empty."""
    if await db.users.count_documents({}) == 0:
        seed_users = [
            ("shubhada", "2612", "Shubhada"),
            ("manju", "6387", "Manju"),
            ("abhishek", "5555", "Abhishek"),
            ("narendra", "6666", "Narendra"),
        ]
        docs = []
        for username, password, name in seed_users:
            u = User(username=username, name=name, isAdmin=True)
            d = u.dict()
            d["hashedPassword"] = hash_password(password)
            docs.append(d)
        await db.users.insert_many(docs)
        try:
            await db.users.create_index("username", unique=True)
        except Exception:
            pass
        logger.info(f"Seeded {len(seed_users)} users")

    if await db.portals.count_documents({}) == 0:
        portals = [
            Portal(name="SUNSHOP", baseUrl="https://www.sunshop.co.in", status="ACTIVE", description="Sunshop portal — supports real login + scrape"),
            Portal(name="CHETHANA", baseUrl="http://www.chethanapharma.in", status="ACTIVE", description="Chethana Pharma portal (adapter pending)"),
            Portal(name="VARDHAMAN", baseUrl="http://easysol.co.in", status="ACTIVE", description="Vardhaman medisales portal (adapter pending)"),
            Portal(name="MEDPLUS", baseUrl="https://medplus.in", status="INACTIVE", description="MedPlus wholesale portal"),
            Portal(name="APOLLO", baseUrl="https://apollo.co.in", status="ACTIVE", description="Apollo pharmacy portal"),
        ]
        await db.portals.insert_many([p.dict() for p in portals])
        logger.info("Seeded portals")

    if await db.targets.count_documents({}) == 0:
        seeds = [
            {"name": "SAROJ PHARMA", "url": "https://www.sunshop.co.in", "portal": "SUNSHOP", "portalType": "SUNSHOP"},
            {"name": "HEGDE BROTHER", "url": "https://www.sunshop.co.in", "portal": "SUNSHOP", "portalType": "SUNSHOP"},
            {"name": "KAPILA PHARMA", "url": "https://www.sunshop.co.in", "portal": "SUNSHOP", "portalType": "SUNSHOP"},
            {"name": "KAPILA MEDICAL AGENCIES", "url": "https://www.sunshop.co.in", "portal": "SUNSHOP", "portalType": "SUNSHOP"},
            {"name": "CHIRAG PHARMA", "url": "http://www.chethanapharma.in", "portal": "CHETHANA", "portalType": "GENERIC"},
            {"name": "VARDHAMAN MEDISALES PVT LTD", "url": "http://easysol.co.in", "portal": "VARDHAMAN", "portalType": "GENERIC"},
        ]
        docs = []
        for s in seeds:
            d = Distributor(**s, selected=True, hasCredentials=False)
            docs.append(d.dict())
        await db.targets.insert_many(docs)
        logger.info("Seeded distributors")


# ============================================================
# AUTHENTICATION
# ============================================================
async def _get_user_by_username(username: str) -> Optional[dict]:
    return await db.users.find_one({"username": username.lower()})


async def _current_user_from_request(request) -> Optional[dict]:
    """Extract & validate the JWT from the Authorization header. Return user dict or None."""
    token = bearer_from_header(request.headers.get("authorization"))
    if not token:
        return None
    try:
        payload = decode_token(token)
    except HTTPException:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = await db.users.find_one({"id": user_id})
    return user


@api_router.post("/auth/login", response_model=LoginResponse)
async def auth_login(payload: LoginRequest):
    user = await _get_user_by_username(payload.username.strip().lower())
    if not user or not verify_password(payload.password, user.get("hashedPassword", "")):
        raise HTTPException(401, "Invalid username or password")
    token = create_token(user["id"], user["username"])
    return LoginResponse(token=token, user=User(**{k: v for k, v in user.items() if k not in ("_id", "hashedPassword")}))


@api_router.get("/auth/me", response_model=User)
async def auth_me(authorization: Optional[str] = Header(None)):
    token = bearer_from_header(authorization)
    if not token:
        raise HTTPException(401, "Not authenticated")
    payload = decode_token(token)
    user = await db.users.find_one({"id": payload.get("sub")})
    if not user:
        raise HTTPException(401, "User no longer exists")
    return User(**{k: v for k, v in user.items() if k not in ("_id", "hashedPassword")})


@api_router.post("/auth/change-password")
async def auth_change_password(payload: ChangePasswordRequest, authorization: Optional[str] = Header(None)):
    token = bearer_from_header(authorization)
    if not token:
        raise HTTPException(401, "Not authenticated")
    p = decode_token(token)
    user = await db.users.find_one({"id": p.get("sub")})
    if not user:
        raise HTTPException(401, "User no longer exists")
    if not verify_password(payload.current_password, user.get("hashedPassword", "")):
        raise HTTPException(400, "Current password is incorrect")
    if len(payload.new_password) < 4:
        raise HTTPException(400, "New password too short (min 4 chars)")
    await db.users.update_one({"id": user["id"]}, {"$set": {"hashedPassword": hash_password(payload.new_password)}})
    return {"ok": True}


# ============================================================
# PORTALS
# ============================================================
@api_router.get("/portals", response_model=List[Portal])
async def list_portals():
    docs = await db.portals.find().to_list(1000)
    return [Portal(**strip_mongo(d)) for d in docs]


@api_router.post("/portals", response_model=Portal)
async def create_portal(payload: PortalCreate):
    p = Portal(**payload.dict())
    await db.portals.insert_one(p.dict())
    return p


# ============================================================
# DISTRIBUTORS (stored in `targets` collection for backwards compat)
# ============================================================
@api_router.get("/targets", response_model=List[Distributor])
async def list_distributors():
    docs = await db.targets.find().sort("created_at", 1).to_list(1000)
    out = []
    for d in docs:
        d = strip_mongo(d)
        d.setdefault("portalType", infer_portal_type(d.get("portal", "")))
        d.setdefault("hasCredentials", False)
        out.append(Distributor(**d))
    return out


@api_router.post("/targets", response_model=Distributor)
async def create_distributor(payload: DistributorCreate):
    data = payload.dict()
    pwd = data.pop("password", None)
    portal_type = data.get("portalType") or infer_portal_type(data.get("portal", ""))
    dist = Distributor(**{
        "name": data["name"],
        "url": data["url"],
        "portal": data["portal"],
        "portalType": portal_type,
        "username": data.get("username"),
        "selected": data.get("selected", True),
        "hasCredentials": bool(pwd),
    })
    to_store = dist.dict()
    if pwd:
        to_store["encryptedPassword"] = encrypt_secret(pwd)
    await db.targets.insert_one(to_store)
    return dist


@api_router.patch("/targets/{tid}", response_model=Distributor)
async def update_distributor(tid: str, payload: DistributorUpdate):
    raw = {k: v for k, v in payload.dict().items() if v is not None}
    if not raw:
        raise HTTPException(400, "No fields to update")
    updates: Dict[str, Any] = {}
    for k, v in raw.items():
        if k == "password":
            updates["encryptedPassword"] = encrypt_secret(v)
            updates["hasCredentials"] = True
        else:
            updates[k] = v
    # Re-derive portalType if portal changed but portalType not provided
    if "portal" in updates and "portalType" not in updates:
        updates["portalType"] = infer_portal_type(updates["portal"])
    doc = await db.targets.find_one_and_update({"id": tid}, {"$set": updates}, return_document=True)
    if not doc:
        raise HTTPException(404, "Distributor not found")
    doc = strip_mongo(doc)
    doc.setdefault("portalType", infer_portal_type(doc.get("portal", "")))
    doc.setdefault("hasCredentials", False)
    return Distributor(**doc)


@api_router.delete("/targets/{tid}")
async def delete_distributor(tid: str):
    res = await db.targets.delete_one({"id": tid})
    if res.deleted_count == 0:
        raise HTTPException(404, "Distributor not found")
    return {"ok": True, "id": tid}


@api_router.post("/targets/bulk-select")
async def bulk_select(payload: BulkSelect):
    res = await db.targets.update_many({}, {"$set": {"selected": payload.selected}})
    return {"ok": True, "matched": res.matched_count, "modified": res.modified_count}


# ============================================================
# TEST LOGIN
# ============================================================
@api_router.post("/targets/{tid}/test-login", response_model=TestLoginResponse)
async def test_login(tid: str):
    doc = await db.targets.find_one({"id": tid})
    if not doc:
        raise HTTPException(404, "Distributor not found")
    if not doc.get("encryptedPassword") or not doc.get("username"):
        return TestLoginResponse(ok=False, detail="Credentials not set for this distributor")

    username = doc["username"]
    try:
        password = decrypt_secret(doc["encryptedPassword"])
    except Exception as e:
        return TestLoginResponse(ok=False, detail=f"Password decrypt failed: {e}")

    url = doc["url"]
    portal_type = doc.get("portalType") or infer_portal_type(doc.get("portal", ""))

    filename = f"testlogin_{tid}_{uuid.uuid4().hex[:8]}.png"
    async def _shot(page, tag):
        p = SCREENSHOTS_DIR / f"testlogin_{tid}_{tag}_{uuid.uuid4().hex[:6]}.png"
        try:
            await page.screenshot(path=str(p), full_page=False)
            return p.name
        except Exception:
            return None

    browser = None
    try:
        browser = await _get_browser()
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-IN",
            extra_http_headers={
                "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        page = await ctx.new_page()
        adapter = get_adapter(portal_type)
        adapter.screenshotter = _shot
        ok, detail = await adapter.test_login(page, url, username, password)
        shot = await _shot(page, "final")
        await ctx.close()
        return TestLoginResponse(ok=ok, detail=detail, screenshot=shot)
    except Exception as e:
        return TestLoginResponse(ok=False, detail=f"{e.__class__.__name__}: {e}")
    finally:
        if browser:
            try: await browser.close()
            except Exception: pass


# ============================================================
# EXTRACTION (REAL — Playwright + adapters)
# ============================================================
@api_router.post("/extract")
async def run_extraction(payload: ExtractRequest):
    if not payload.product.strip():
        raise HTTPException(400, "Product name is required")
    if not payload.target_ids:
        raise HTTPException(400, "At least one distributor is required")

    docs = await db.targets.find({"id": {"$in": payload.target_ids}}).to_list(1000)
    if not docs:
        raise HTTPException(404, "No matching distributors")

    entry_id = str(uuid.uuid4())
    product_upper = payload.product.upper().strip()
    qty = payload.quantity

    start_ts = datetime.utcnow()
    results: List[Dict[str, Any]] = []

    browser = None
    try:
        browser = await _get_browser()

        async def run_one(doc):
            tid = doc["id"]
            name = doc["name"]
            portal = doc.get("portal", "")
            portal_type = doc.get("portalType") or infer_portal_type(portal)
            url = doc["url"]

            base = {
                "targetId": tid,
                "targetName": name,
                "portal": portal,
                "portalType": portal_type,
                "url": url,
                "product": product_upper,
            }

            if not doc.get("username") or not doc.get("encryptedPassword"):
                return {**base, **{"status": "LOGIN_FAILED", "detail": "Credentials not set. Edit distributor to add username/password.", "items": [], "requestedQty": qty, "canFulfill": None, "loginScreenshot": None, "searchScreenshot": None, "resultsScreenshot": None, "debug": {}}}

            try:
                password = decrypt_secret(doc["encryptedPassword"])
            except Exception as e:
                return {**base, **{"status": "ERROR", "detail": f"Password decrypt failed: {e}", "items": [], "requestedQty": qty, "canFulfill": None, "loginScreenshot": None, "searchScreenshot": None, "resultsScreenshot": None, "debug": {}}}

            async def _shot(page, tag):
                p = SCREENSHOTS_DIR / f"{entry_id}_{tid}_{tag}_{uuid.uuid4().hex[:6]}.png"
                try:
                    await page.screenshot(path=str(p), full_page=False)
                    return p.name
                except Exception:
                    return None

            ctx = None
            try:
                ctx = await browser.new_context(
                    viewport={"width": 1366, "height": 900},
                    ignore_https_errors=True,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    locale="en-IN",
                    extra_http_headers={
                        "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                        "Upgrade-Insecure-Requests": "1",
                    },
                )
                page = await ctx.new_page()
                adapter = get_adapter(portal_type)
                adapter.screenshotter = _shot
                outcome = await adapter.extract(page, url, doc["username"], password, product_upper, qty or 0, distributor_name=name)
                return {**base, **outcome.to_dict()}
            except Exception as e:
                return {**base, **{"status": "ERROR", "detail": f"{e.__class__.__name__}: {e}", "items": [], "requestedQty": qty, "canFulfill": None, "loginScreenshot": None, "searchScreenshot": None, "resultsScreenshot": None, "debug": {}}}
            finally:
                if ctx:
                    try: await ctx.close()
                    except Exception: pass

        # Run all distributors in parallel (limit concurrency to 4)
        sem = asyncio.Semaphore(4)
        async def _guarded(d):
            async with sem:
                return await run_one(d)

        results = await asyncio.gather(*[_guarded(d) for d in docs])
    finally:
        if browser:
            try: await browser.close()
            except Exception: pass

    elapsed = (datetime.utcnow() - start_ts).total_seconds()
    success = sum(1 for r in results if r["status"] == "SUCCESS")
    not_found = sum(1 for r in results if r["status"] == "NOT_FOUND")
    login_failed = sum(1 for r in results if r["status"] == "LOGIN_FAILED")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    entry = {
        "id": entry_id,
        "product": product_upper,
        "quantity": qty,
        "timestamp": start_ts,
        "duration": f"{elapsed:.1f}s",
        "targetsRun": len(results),
        "found": success,
        "notFound": not_found,
        "loginFailed": login_failed,
        "errors": errors,
        "outOfStock": not_found,  # legacy alias
        "status": "COMPLETED" if errors == 0 and login_failed == 0 else "PARTIAL",
        "results": results,
    }
    await db.history.insert_one(entry)
    entry.pop("_id", None)
    return entry


# ============================================================
# HISTORY
# ============================================================
@api_router.get("/history")
async def list_history():
    docs = await db.history.find().sort("timestamp", -1).to_list(1000)
    out = []
    for d in docs:
        d = strip_mongo(d)
        d.setdefault("results", [])
        d.setdefault("errors", 0)
        d.setdefault("quantity", None)
        out.append(d)
    return out


@api_router.get("/history/{entry_id}")
async def get_history(entry_id: str):
    doc = await db.history.find_one({"id": entry_id})
    if not doc:
        raise HTTPException(404, "Not found")
    doc = strip_mongo(doc)
    doc.setdefault("results", [])
    doc.setdefault("errors", 0)
    doc.setdefault("quantity", None)
    return doc


@api_router.delete("/history/{entry_id}")
async def delete_history(entry_id: str):
    res = await db.history.delete_one({"id": entry_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True, "id": entry_id}


# ============================================================
# SCREENSHOTS
# ============================================================
@api_router.get("/screenshots/{filename}")
async def get_screenshot(filename: str):
    # Prevent path traversal
    fn = os.path.basename(filename)
    p = SCREENSHOTS_DIR / fn
    if not p.exists():
        raise HTTPException(404, "Screenshot not found")
    return FileResponse(str(p), media_type="image/png")


# ============================================================
# PRODUCT MASTER
# ============================================================
def _normalize_product(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _pick_col(headers, aliases):
    """Return the header value that matches any alias (case-insensitive contains)."""
    lower_map = {h.lower(): h for h in headers if isinstance(h, str)}
    for a in aliases:
        a_low = a.lower()
        for k, orig in lower_map.items():
            if a_low == k or a_low in k:
                return orig
    return None


class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    pack: Optional[str] = None
    strength: Optional[str] = None
    mrp: Optional[str] = None
    manufacturer: Optional[str] = None
    code: Optional[str] = None
    norm: str = ""


@api_router.get("/products/count")
async def products_count():
    return {"count": await db.products.count_documents({})}


@api_router.get("/products/search")
async def products_search(q: str = Query("", min_length=0, max_length=100), limit: int = Query(20, ge=1, le=50)):
    q_norm = _normalize_product(q)
    if not q_norm:
        # Return top N by name
        docs = await db.products.find().limit(limit).to_list(limit)
        return [strip_mongo(d) for d in docs]

    # Split query into tokens; every token must appear in `norm` (prefix or substring)
    tokens = [t for t in q_norm.split() if t]

    # Build regex for prefix on first token; fall back to substring for others
    # Fast prefix on `norm` (indexed) then further filter with $all-style regex
    query = {"norm": {"$regex": f".*{re.escape(tokens[0])}", "$options": "i"}}
    if len(tokens) > 1:
        # Ensure all remaining tokens are present in norm too
        query = {"$and": [query] + [
            {"norm": {"$regex": re.escape(t), "$options": "i"}} for t in tokens[1:]
        ]}

    cursor = db.products.find(query).limit(limit)
    docs = await cursor.to_list(limit)
    return [strip_mongo(d) for d in docs]


@api_router.delete("/products/clear")
async def products_clear():
    r = await db.products.delete_many({})
    return {"deleted": r.deleted_count}


@api_router.post("/products/upload")
async def products_upload(file: UploadFile = File(...)):
    """Accepts .xlsx or .csv, extracts columns matching Product Name / Pack / Strength / MRP / Manufacturer / Code."""
    try:
        import pandas as pd
    except Exception:
        raise HTTPException(500, "pandas not installed on server")

    filename = (file.filename or "").lower()
    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content), dtype=str)
            df = df.fillna("")
        else:
            raise HTTPException(400, "Unsupported file type. Please upload .xlsx or .csv")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Failed to parse file: {e}")

    if df.empty:
        raise HTTPException(400, "File contains no rows")

    headers = list(df.columns)
    name_col = _pick_col(headers, ["product name", "product", "name", "item", "item name", "description"])
    pack_col = _pick_col(headers, ["pack", "packing", "size"])
    strength_col = _pick_col(headers, ["strength", "mg", "dosage"])
    mrp_col = _pick_col(headers, ["mrp"])
    mfr_col = _pick_col(headers, ["manufacturer", "mfr", "company", "brand"])
    code_col = _pick_col(headers, ["code", "product code", "sku", "barcode", "id"])

    if not name_col:
        raise HTTPException(400, f"Could not find a Product Name column in: {headers}. Please rename one to 'Product Name'.")

    # Wipe existing products before importing new master (upload replaces)
    await db.products.delete_many({})

    now = datetime.utcnow()
    docs: List[Dict[str, Any]] = []
    inserted = 0
    for _, row in df.iterrows():
        name = str(row.get(name_col, "") or "").strip()
        if not name:
            continue
        p = {
            "id": str(uuid.uuid4()),
            "name": name.upper(),
            "pack": (str(row.get(pack_col, "") or "").strip() or None) if pack_col else None,
            "strength": (str(row.get(strength_col, "") or "").strip() or None) if strength_col else None,
            "mrp": (str(row.get(mrp_col, "") or "").strip() or None) if mrp_col else None,
            "manufacturer": (str(row.get(mfr_col, "") or "").strip() or None) if mfr_col else None,
            "code": (str(row.get(code_col, "") or "").strip() or None) if code_col else None,
            "norm": _normalize_product(name),
            "created_at": now,
        }
        docs.append(p)
        # Chunked insert to avoid huge single-shot
        if len(docs) >= 2000:
            try:
                await db.products.insert_many(docs, ordered=False)
                inserted += len(docs)
            except Exception as e:
                logger.warning(f"insert_many chunk error: {e}")
            docs = []
    if docs:
        try:
            await db.products.insert_many(docs, ordered=False)
            inserted += len(docs)
        except Exception as e:
            logger.warning(f"insert_many tail error: {e}")

    # Ensure index for fast search on `norm`
    try:
        await db.products.create_index("norm")
    except Exception:
        pass

    return {
        "inserted": inserted,
        "detectedColumns": {
            "name": name_col, "pack": pack_col, "strength": strength_col,
            "mrp": mrp_col, "manufacturer": mfr_col, "code": code_col,
        },
    }




# ============================================================
# ROOT
# ============================================================
@api_router.get("/")
async def root():
    return {"service": "pharmascrape", "status": "ok", "version": "2.0"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Auth middleware: protect all /api/* except /api/auth/* and /api/ root ----
PUBLIC_API_PATHS = {"/api/", "/api"}


@app.middleware("http")
async def auth_middleware(request, call_next):
    from starlette.responses import JSONResponse
    path = request.url.path
    # Only guard /api/* endpoints; skip auth endpoints, root, and screenshots
    if (
        path.startswith("/api/")
        and not path.startswith("/api/auth/")
        and not path.startswith("/api/screenshots/")
        and path not in PUBLIC_API_PATHS
    ):
        # Allow OPTIONS preflight through
        if request.method != "OPTIONS":
            token = bearer_from_header(request.headers.get("authorization"))
            if not token:
                return JSONResponse({"detail": "Not authenticated"}, status_code=401)
            try:
                decode_token(token)
            except HTTPException as e:
                return JSONResponse({"detail": e.detail}, status_code=e.status_code)
            except Exception:
                return JSONResponse({"detail": "Invalid token"}, status_code=401)
    return await call_next(request)


@app.on_event("startup")
async def on_startup():
    try:
        # Migrate: reset seed if legacy targets have no portalType and no credentials
        legacy = await db.targets.count_documents({"portalType": {"$exists": False}})
        if legacy > 0:
            await db.targets.update_many(
                {"portalType": {"$exists": False}},
                {"$set": {"portalType": "GENERIC", "hasCredentials": False}}
            )
            logger.info(f"Backfilled portalType on {legacy} legacy distributor(s)")
        await seed_if_empty()
        asyncio.create_task(_cleanup_old_screenshots())
    except Exception as e:
        logger.error(f"Startup error: {e}")


@app.on_event("shutdown")
async def on_shutdown():
    global _playwright
    try:
        client.close()
    except Exception:
        pass
    if _playwright is not None:
        try:
            await _playwright.stop()
        except Exception:
            pass
