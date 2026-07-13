from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import random
import uuid
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="PharmaScrape API")
api_router = APIRouter(prefix="/api")


# ---------------------------- Models ----------------------------
class Portal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    baseUrl: str
    status: str = "ACTIVE"  # ACTIVE | INACTIVE
    description: Optional[str] = ""


class PortalCreate(BaseModel):
    name: str
    baseUrl: str
    status: str = "ACTIVE"
    description: Optional[str] = ""


class Target(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    url: str
    portal: str
    selected: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TargetCreate(BaseModel):
    name: str
    url: str
    portal: str
    selected: bool = True


class TargetUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    portal: Optional[str] = None
    selected: Optional[bool] = None


class BulkSelect(BaseModel):
    selected: bool


class ExtractionResult(BaseModel):
    targetId: str
    targetName: str
    portal: str
    url: str
    product: str
    status: str  # IN_STOCK | OUT_OF_STOCK | ERROR
    price: Optional[str] = None
    mrp: Optional[str] = None
    stock: int = 0
    pack: Optional[str] = None
    responseMs: int = 0
    lastUpdated: datetime = Field(default_factory=datetime.utcnow)


class HistoryEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration: str
    targetsRun: int
    found: int
    outOfStock: int
    errors: int = 0
    status: str  # COMPLETED | PARTIAL
    results: List[ExtractionResult] = []


class ExtractRequest(BaseModel):
    product: str
    target_ids: List[str]


# ---------------------------- Helpers ----------------------------
def strip_mongo_id(doc: dict) -> dict:
    if not doc:
        return doc
    doc.pop("_id", None)
    return doc


async def seed_if_empty():
    """Seed portals + targets + history if collections are empty."""
    if await db.portals.count_documents({}) == 0:
        portals = [
            Portal(name="SUNSHOP", baseUrl="https://www.sunshop.co.in", status="ACTIVE", description="Sunshop portal for multiple distributors"),
            Portal(name="CHETHANA", baseUrl="http://www.chiragpharma.in", status="ACTIVE", description="Chethana distribution portal"),
            Portal(name="VARDHAMAN", baseUrl="http://easysol.co.in", status="ACTIVE", description="Vardhaman medisales web order portal"),
            Portal(name="MEDPLUS", baseUrl="https://medplus.in", status="INACTIVE", description="MedPlus wholesale portal"),
            Portal(name="APOLLO", baseUrl="https://apollo.co.in", status="ACTIVE", description="Apollo pharmacy distributor portal"),
        ]
        await db.portals.insert_many([p.dict() for p in portals])
        logger.info("Seeded portals collection")

    if await db.targets.count_documents({}) == 0:
        targets = [
            Target(name="SAROJ PHARMA", url="https://www.sunshop.co.in/sunfilter/saroj", portal="SUNSHOP", selected=True),
            Target(name="HEGDE BROTHER", url="https://www.sunshop.co.in/sunfilter/hegde", portal="SUNSHOP", selected=True),
            Target(name="KAPILA PHARMA", url="https://www.sunshop.co.in/sunfilter/kapila", portal="SUNSHOP", selected=True),
            Target(name="KAPILA MEDICAL AGENCIES", url="https://www.sunshop.co.in/sunfilter/kapila-med", portal="SUNSHOP", selected=True),
            Target(name="CHIRAG PHARMA", url="http://www.chiragpharma.in/", portal="CHETHANA", selected=True),
            Target(name="VARDHAMAN MEDISALES PVT LTD", url="http://easysol.co.in/WebOrderRegistration", portal="VARDHAMAN", selected=True),
            Target(name="SRI SAI MEDICALS", url="https://www.sunshop.co.in/sunfilter/srisai", portal="SUNSHOP", selected=False),
            Target(name="BHARAT MEDICOS", url="http://easysol.co.in/WebOrderRegistration/bharat", portal="VARDHAMAN", selected=False),
        ]
        await db.targets.insert_many([t.dict() for t in targets])
        logger.info("Seeded targets collection")

    if await db.history.count_documents({}) == 0:
        seed_history = [
            HistoryEntry(product="PROLOMET XL 25", timestamp=datetime.fromisoformat("2025-07-12T14:32:00"), duration="4.2s", targetsRun=6, found=4, outOfStock=2, status="COMPLETED"),
            HistoryEntry(product="PANTOP DSR",    timestamp=datetime.fromisoformat("2025-07-12T11:08:00"), duration="3.8s", targetsRun=8, found=6, outOfStock=2, status="COMPLETED"),
            HistoryEntry(product="DOLO 650",      timestamp=datetime.fromisoformat("2025-07-11T18:45:00"), duration="5.1s", targetsRun=5, found=5, outOfStock=0, status="COMPLETED"),
            HistoryEntry(product="AZITHRAL 500",  timestamp=datetime.fromisoformat("2025-07-11T09:20:00"), duration="2.9s", targetsRun=4, found=1, outOfStock=3, status="COMPLETED"),
            HistoryEntry(product="MONTAIR LC",    timestamp=datetime.fromisoformat("2025-07-10T16:15:00"), duration="6.7s", targetsRun=8, found=3, outOfStock=4, errors=1, status="PARTIAL"),
            HistoryEntry(product="CROCIN ADVANCE",timestamp=datetime.fromisoformat("2025-07-10T10:02:00"), duration="3.3s", targetsRun=6, found=4, outOfStock=2, status="COMPLETED"),
        ]
        await db.history.insert_many([h.dict() for h in seed_history])
        logger.info("Seeded history collection")


def simulate_scrape(product: str, target: dict) -> ExtractionResult:
    """Deterministic-ish mock scraper for MVP. Returns realistic-looking data."""
    # Weighted outcome: 55% in-stock, 35% out, 10% error
    r = random.random()
    if r < 0.55:
        status = "IN_STOCK"
    elif r < 0.90:
        status = "OUT_OF_STOCK"
    else:
        status = "ERROR"

    price = None
    mrp = None
    stock = 0
    pack = None
    if status == "IN_STOCK":
        p = round(random.uniform(20.0, 120.0), 2)
        price = f"{p:.2f}"
        mrp = f"{round(p * 1.15, 2):.2f}"
        stock = random.randint(10, 210)
        pack = random.choice(["10x10", "1x10", "1x15", "1x30", "10x15"])

    return ExtractionResult(
        targetId=target["id"],
        targetName=target["name"],
        portal=target["portal"],
        url=target["url"],
        product=product,
        status=status,
        price=price,
        mrp=mrp,
        stock=stock,
        pack=pack,
        responseMs=random.randint(200, 1100),
    )


# ---------------------------- Portals ----------------------------
@api_router.get("/portals", response_model=List[Portal])
async def list_portals():
    docs = await db.portals.find().to_list(1000)
    return [Portal(**strip_mongo_id(d)) for d in docs]


@api_router.post("/portals", response_model=Portal)
async def create_portal(payload: PortalCreate):
    portal = Portal(**payload.dict())
    await db.portals.insert_one(portal.dict())
    return portal


# ---------------------------- Targets ----------------------------
@api_router.get("/targets", response_model=List[Target])
async def list_targets():
    docs = await db.targets.find().sort("created_at", 1).to_list(1000)
    return [Target(**strip_mongo_id(d)) for d in docs]


@api_router.post("/targets", response_model=Target)
async def create_target(payload: TargetCreate):
    target = Target(**payload.dict())
    await db.targets.insert_one(target.dict())
    return target


@api_router.patch("/targets/{target_id}", response_model=Target)
async def update_target(target_id: str, payload: TargetUpdate):
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.targets.find_one_and_update(
        {"id": target_id},
        {"$set": updates},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Target not found")
    return Target(**strip_mongo_id(result))


@api_router.delete("/targets/{target_id}")
async def delete_target(target_id: str):
    res = await db.targets.delete_one({"id": target_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Target not found")
    return {"ok": True, "id": target_id}


@api_router.post("/targets/bulk-select")
async def bulk_select(payload: BulkSelect):
    res = await db.targets.update_many({}, {"$set": {"selected": payload.selected}})
    return {"ok": True, "matched": res.matched_count, "modified": res.modified_count}


# ---------------------------- Extraction ----------------------------
@api_router.post("/extract", response_model=HistoryEntry)
async def run_extraction(payload: ExtractRequest):
    if not payload.product.strip():
        raise HTTPException(status_code=400, detail="Product name is required")
    if not payload.target_ids:
        raise HTTPException(status_code=400, detail="At least one target is required")

    docs = await db.targets.find({"id": {"$in": payload.target_ids}}).to_list(1000)
    if not docs:
        raise HTTPException(status_code=404, detail="No matching targets found")

    start = datetime.utcnow()
    results: List[ExtractionResult] = []
    for d in docs:
        # Simulate network latency (very short so backend testing is fast)
        await asyncio.sleep(random.uniform(0.02, 0.10))
        results.append(simulate_scrape(payload.product.upper(), d))
    elapsed = (datetime.utcnow() - start).total_seconds()

    found = sum(1 for r in results if r.status == "IN_STOCK")
    oos = sum(1 for r in results if r.status == "OUT_OF_STOCK")
    errs = sum(1 for r in results if r.status == "ERROR")

    entry = HistoryEntry(
        product=payload.product.upper(),
        duration=f"{elapsed:.1f}s",
        targetsRun=len(results),
        found=found,
        outOfStock=oos,
        errors=errs,
        status="PARTIAL" if errs > 0 else "COMPLETED",
        results=results,
    )
    await db.history.insert_one(entry.dict())
    return entry


# ---------------------------- History ----------------------------
@api_router.get("/history", response_model=List[HistoryEntry])
async def list_history():
    docs = await db.history.find().sort("timestamp", -1).to_list(1000)
    out = []
    for d in docs:
        d = strip_mongo_id(d)
        # Older seeded docs may not have `results` — normalize
        d.setdefault("results", [])
        d.setdefault("errors", 0)
        out.append(HistoryEntry(**d))
    return out


@api_router.get("/history/{entry_id}", response_model=HistoryEntry)
async def get_history(entry_id: str):
    doc = await db.history.find_one({"id": entry_id})
    if not doc:
        raise HTTPException(status_code=404, detail="History entry not found")
    doc = strip_mongo_id(doc)
    doc.setdefault("results", [])
    doc.setdefault("errors", 0)
    return HistoryEntry(**doc)


@api_router.delete("/history/{entry_id}")
async def delete_history(entry_id: str):
    res = await db.history.delete_one({"id": entry_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="History entry not found")
    return {"ok": True, "id": entry_id}


# ---------------------------- Root ----------------------------
@api_router.get("/")
async def root():
    return {"service": "pharmascrape", "status": "ok"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def on_startup():
    try:
        await seed_if_empty()
    except Exception as e:
        logger.error(f"Seed error: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
