import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from ..auth import current_user, require, LEADS
from ..db import db, now_iso, audit, parse_date
from ..logic import CATEGORIES, COMMITTED, total_cost, get_settings, committed_cost, campaign_allocation
from .campaigns import fmt_rp

router = APIRouter(prefix="/api")


def read_csv(data: bytes):
    text = data.decode("utf-8-sig", errors="replace")
    first = text.splitlines()[0] if text else ""
    delim = ";" if first.count(";") > first.count(",") else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delim))


def num(x):
    if x is None or str(x).strip() == "":
        return 0
    s = str(x).strip().replace("Rp", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.split(".")[1]) == 3):
        s = s.replace(".", "")
    s = s.replace(",", ".")
    return float(s)


# ----------------------------------------------------------------- Outlet
class OutletIn(BaseModel):
    code: str
    name: str
    area: str = ""


@router.get("/outlets")
async def outlets(user=Depends(current_user)):
    return await db.outlets.find({}, {"_id": 0}).sort("code").to_list(None)


@router.post("/outlets")
async def upsert_outlet(body: OutletIn, user=Depends(require(*LEADS))):
    await db.outlets.update_one({"code": body.code.strip().upper()}, {"$set": {**body.model_dump(), "code": body.code.strip().upper()}}, upsert=True)
    return {"ok": True}


@router.post("/outlets/import")
async def import_outlets(file: UploadFile = File(...), user=Depends(require(*LEADS))):
    rows = read_csv(await file.read())
    n = 0
    for r in rows:
        code = (r.get("code") or r.get("kode") or "").strip().upper()
        if not code:
            continue
        await db.outlets.update_one({"code": code}, {"$set": {"code": code, "name": r.get("name") or r.get("nama") or code, "area": r.get("area", "")}}, upsert=True)
        n += 1
    await audit(user, "outlets.import", None, after={"rows": n})
    return {"imported": n}


@router.post("/outlet-sales/import")
async def import_sales(file: UploadFile = File(...), user=Depends(require(*LEADS))):
    """CSV: date, outletCode, revenueRp, transactions, [sku:KODE ...]. Pemisah , atau ;"""
    rows = read_csv(await file.read())
    n, errors = 0, []
    for i, r in enumerate(rows, start=2):
        try:
            d = parse_date(r.get("date") or r.get("tanggal"))
            code = (r.get("outletCode") or r.get("outlet") or "").strip().upper()
            if not d or not code:
                raise ValueError("date/outletCode kosong")
            sku = {k.split(":", 1)[1].strip().upper(): num(v) for k, v in r.items() if k and k.lower().startswith("sku:")}
            doc = {"date": d.isoformat(), "outletCode": code, "revenueRp": num(r.get("revenueRp") or r.get("revenue")),
                   "transactions": int(num(r.get("transactions") or r.get("transaksi"))), "skuUnits": sku, "importedAt": now_iso()}
            await db.outlet_sales.update_one({"outletCode": code, "date": doc["date"]}, {"$set": doc}, upsert=True)
            n += 1
        except ValueError as e:
            msg = str(e)
            errors.append(f"Baris {i}: " + ("format tanggal harus YYYY-MM-DD" if "isoformat" in msg else msg))
    await audit(user, "outlet_sales.import", None, after={"rows": n, "errors": len(errors)})
    return {"imported": n, "errors": errors[:20]}


@router.get("/outlet-sales")
async def list_sales(outletCode: str, start: str, end: str, user=Depends(current_user)):
    return await db.outlet_sales.find({"outletCode": outletCode.upper(), "date": {"$gte": start, "$lte": end}}, {"_id": 0}).sort("date").to_list(None)


# ----------------------------------------------------------------- Budget
class BudgetIn(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    category: str
    plannedRp: int = Field(ge=0)
    notes: str = ""


@router.get("/budget")
async def budget(month: str, user=Depends(current_user)):
    settings = await get_settings()
    plans = {p["category"]: p for p in await db.budget.find({"month": month}, {"_id": 0}).to_list(None)}
    camps = await db.campaigns.find({"month": month}, {"_id": 0}).to_list(None)
    cids = {c["id"]: c for c in camps}
    bookings = await db.bookings.find({"campaignId": {"$in": list(cids)}}, {"_id": 0}).to_list(None)
    rows = []
    for cat in CATEGORIES:
        cs = [c for c in camps if c["category"] == cat]
        alloc = 0
        for c in cs:
            alloc += await campaign_allocation(c)
        bs = [b for b in bookings if cids[b["campaignId"]]["category"] == cat]
        committed = sum(committed_cost(b) for b in bs)
        paid = sum(int((b.get("payment") or {}).get("paidRp") or 0) + int((b.get("payment") or {}).get("dpRp") or 0) for b in bs)
        planned = int((plans.get(cat) or {}).get("plannedRp", 0))
        rows.append({"category": cat, "plannedRp": planned, "allocatedRp": alloc, "committedRp": committed, "paidRp": paid,
                     "remainingRp": planned - committed, "unallocatedRp": planned - alloc, "notes": (plans.get(cat) or {}).get("notes", ""),
                     "warn": planned > 0 and committed > 0.9 * planned, "campaigns": [{"id": c["id"], "name": c["name"], "budgetRp": c["budgetRp"], "code": c.get("linkedInitiativeCode")} for c in cs]})
    tot = {k: sum(r[k] for r in rows) for k in ("plannedRp", "allocatedRp", "committedRp", "paidRp", "remainingRp")}
    return {"month": month, "pagu": settings["monthlyKolPagu"], "rows": rows, "total": tot}


@router.put("/budget")
async def set_budget(body: BudgetIn, user=Depends(require("Manager"))):
    if body.category not in CATEGORIES:
        raise HTTPException(400, "Kategori tidak dikenal")
    settings = await get_settings()
    others = 0
    async for p in db.budget.find({"month": body.month, "category": {"$ne": body.category}}, {"_id": 0}):
        others += int(p["plannedRp"])
    if others + body.plannedRp > settings["monthlyKolPagu"]:
        raise HTTPException(400, f"Total plan melebihi pagu KOL bulanan {fmt_rp(settings['monthlyKolPagu'])} (sisa {fmt_rp(settings['monthlyKolPagu'] - others)})")
    alloc = 0
    async for c in db.campaigns.find({"month": body.month, "category": body.category}, {"_id": 0}):
        alloc += await campaign_allocation(c)
    if body.plannedRp < alloc:
        raise HTTPException(400, f"Plan tidak boleh di bawah budget campaign yang sudah dialokasikan ({fmt_rp(alloc)})")
    before = await db.budget.find_one({"month": body.month, "category": body.category}, {"_id": 0})
    await db.budget.update_one({"month": body.month, "category": body.category},
                               {"$set": {**body.model_dump(), "updatedBy": user["name"], "updatedAt": now_iso()}}, upsert=True)
    await audit(user, "budget.set", f"{body.month}/{body.category}", before={"plannedRp": (before or {}).get("plannedRp")}, after={"plannedRp": body.plannedRp})
    return {"ok": True}


@router.get("/audit")
async def audit_log(ref: str | None = None, limit: int = 200, user=Depends(require("Manager", "KOL TL"))):
    q = {"ref": ref} if ref else {}
    return await db.audit.find(q, {"_id": 0}).sort("at", -1).limit(limit).to_list(None)
