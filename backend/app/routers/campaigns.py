import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..auth import current_user, require, LEADS
from ..db import db, new_id, now_iso, audit
from ..logic import (CATEGORIES, load_universe, aggregate, with_roi, campaign_budgets_in_month,
                     committed_for_campaign, total_cost, COMMITTED)

router = APIRouter(prefix="/api/campaigns")
GATES = ["PENDING", "GO", "GWC", "HOLD", "SELESAI"]
REVIEWS = ["SCALE", "KEEP", "STOP"]


class CampaignIn(BaseModel):
    name: str = Field(min_length=3)
    category: str
    objective: str = ""
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    start: str
    end: str
    target: dict = {}          # {outlets:[], area:"", sku:"", store:""}
    budgetRp: int = Field(ge=0)
    kpiTargets: dict = {}      # {views, cpv, outcome, costPerOutcome, roas, revenueDirect}
    gateStatus: str = "PENDING"
    gateNote: str = ""
    linkedInitiativeCode: str = ""
    promoCodePrefix: str = ""


class ReviewIn(BaseModel):
    review: str
    reviewNote: str = Field(min_length=10)
    whatWorked: str = ""
    whatDidnt: str = ""
    nextAction: str = ""


def fmt_rp(x):
    return "Rp" + f"{int(x):,}".replace(",", ".")


async def check_budget(body: CampaignIn, exclude=None):
    if body.category not in CATEGORIES:
        raise HTTPException(400, "Kategori tidak dikenal")
    plan = await db.budget.find_one({"month": body.month, "category": body.category}, {"_id": 0})
    if not plan:
        raise HTTPException(400, f"Belum ada budget plan {body.category} untuk {body.month}. Minta Manager mengisi halaman Budget dulu.")
    if body.gateStatus == "HOLD":
        return
    used = await campaign_budgets_in_month(body.month, body.category, exclude_campaign=exclude)
    remaining = int(plan["plannedRp"]) - used
    if body.budgetRp > remaining:
        raise HTTPException(400, f"Melebihi sisa budget {body.category} bulan ini (sisa {fmt_rp(max(remaining, 0))})")


def slug(s):
    return re.sub(r"[^A-Z0-9]+", "-", s.upper()).strip("-")[:14]


@router.get("")
async def list_campaigns(month: str | None = None, user=Depends(current_user)):
    q = {"month": month} if month else {}
    u = await load_universe(campaign_query=q)
    gm = u["settings"]["gmBlended"]
    out = []
    for c in sorted(u["campaigns"].values(), key=lambda c: (c["month"], c["name"]), reverse=True):
        bs = [b for b in u["bookings"] if b["campaignId"] == c["id"]]
        ms = [u["metrics"][b["id"]] for b in bs if b.get("status") in COMMITTED]
        a = with_roi(aggregate(ms), gm)
        committed = sum(total_cost(b.get("costs")) for b in bs if b.get("status") in
                        ("DEAL", "BRIEF_SENT", "DRAFT_REVIEW", "POSTED", "REPORT_DUE", "REPORT_SUBMITTED", "REPORT_APPROVED", "PAID"))
        out.append({**c, "agg": a, "committed": committed, "bookingCount": len(bs)})
    return out


@router.get("/{cid}")
async def get_campaign(cid: str, user=Depends(current_user)):
    u = await load_universe(campaign_query={"id": cid})
    c = u["campaigns"].get(cid)
    if not c:
        raise HTTPException(404, "Campaign tidak ditemukan")
    gm = u["settings"]["gmBlended"]
    rows = []
    for b in u["bookings"]:
        k = u["kols"].get(b["kolId"], {})
        rows.append({"booking": b, "kol": {"id": k.get("id"), "name": k.get("name"), "handles": k.get("handles")},
                     "metrics": u["metrics"][b["id"]], "contents": u["contents_by_booking"].get(b["id"], [])})
    ms = [r["metrics"] for r in rows if r["booking"].get("status") in COMMITTED]
    agg = with_roi(aggregate(ms), gm)
    committed = await committed_for_campaign(cid)
    return {**c, "rows": rows, "agg": agg, "committed": committed, "config": CATEGORIES[c["category"]]}


@router.post("")
async def create_campaign(body: CampaignIn, user=Depends(require(*LEADS))):
    if body.gateStatus not in GATES:
        raise HTTPException(400, "Status gate tidak dikenal")
    if body.gateStatus not in ("PENDING",) and user["role"] != "Manager":
        raise HTTPException(403, "Status Activity Gate hanya diputuskan Manager")
    await check_budget(body)
    doc = body.model_dump()
    doc["code"] = f"KOL-{body.month[2:4]}{body.month[5:7]}-{CATEGORIES[body.category]['code']}-{slug(body.name)}"
    doc.update({"id": new_id(), "createdAt": now_iso(), "ownerId": user["id"], "ownerName": user["name"], "review": None})
    await db.campaigns.insert_one(doc)
    await audit(user, "campaign.create", doc["id"], after={"name": body.name, "budgetRp": body.budgetRp})
    doc.pop("_id", None)
    return doc


@router.put("/{cid}")
async def update_campaign(cid: str, body: CampaignIn, user=Depends(require(*LEADS))):
    before = await db.campaigns.find_one({"id": cid}, {"_id": 0})
    if not before:
        raise HTTPException(404, "Campaign tidak ditemukan")
    if body.gateStatus != before.get("gateStatus"):
        if user["role"] != "Manager":
            raise HTTPException(403, "Status Activity Gate hanya diputuskan Manager")
        if body.gateStatus == "SELESAI" and not before.get("review"):
            raise HTTPException(400, "Isi Review (SCALE/KEEP/STOP + learning) sebelum campaign ditutup SELESAI")
    if body.category != before["category"]:
        n = await db.bookings.count_documents({"campaignId": cid})
        if n:
            raise HTTPException(400, "Kategori tidak bisa diubah setelah ada booking")
    await check_budget(body, exclude=cid)
    committed = await committed_for_campaign(cid)
    if body.budgetRp < committed:
        raise HTTPException(400, f"Budget tidak boleh di bawah biaya yang sudah DEAL ({fmt_rp(committed)})")
    data = body.model_dump()
    await db.campaigns.update_one({"id": cid}, {"$set": data})
    changed = {k: v for k, v in data.items() if before.get(k) != v}
    await audit(user, "campaign.update", cid, before={k: before.get(k) for k in changed}, after=changed)
    return {"ok": True}


@router.post("/{cid}/review")
async def review_campaign(cid: str, body: ReviewIn, user=Depends(require(*LEADS))):
    if body.review not in REVIEWS:
        raise HTTPException(400, "Review harus SCALE / KEEP / STOP")
    c = await db.campaigns.find_one({"id": cid}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Campaign tidak ditemukan")
    open_ = await db.bookings.count_documents({"campaignId": cid, "status": {"$in": ["POSTED", "REPORT_DUE", "REPORT_SUBMITTED"]}})
    if open_:
        raise HTTPException(400, f"Masih ada {open_} booking yang report-nya belum di-approve")
    data = body.model_dump()
    data.update({"reviewedBy": user["name"], "reviewedAt": now_iso()})
    await db.campaigns.update_one({"id": cid}, {"$set": data})
    await audit(user, "campaign.review", cid, after=data)
    return {"ok": True}
