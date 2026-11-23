import re
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..auth import current_user, require, EDITORS, LEADS
from ..db import db, new_id, now_iso, audit
from ..logic import get_settings, kol_tier, load_universe, recommend, norm_handle, TIERS, COMMITTED, kol_indicator

router = APIRouter(prefix="/api/kols")


class KolIn(BaseModel):
    name: str = Field(min_length=2)
    handles: dict = {}
    primaryPlatform: str = "tiktok"
    followers: dict = {}
    city: str = ""
    audienceCityTop3: list[str] = []
    niche: list[str] = []
    contactWa: str = ""
    agency: str = ""
    rateCard: dict = {}
    avgViews30D: int | None = None
    avgER30D: float | None = None
    bankAccount: str = ""
    npwp: str = ""
    status: str = "Aktif"
    blacklistReason: str = ""
    picOfficerId: str | None = None   # PIC KOL (listing s/d lock/DEAL)
    insightFiles: list[str] = []      # screenshot insight akun (dasar avg views)
    notes: str = ""
    tierOverride: str | None = None
    tierOverrideReason: str = ""
    recommendationOverride: str | None = None


def mask(s: str):
    if not s:
        return s
    return s[:3] + "•" * max(len(s) - 6, 2) + s[-3:]


async def user_names():
    return {u["id"]: u["name"] async for u in db.users.find({}, {"_id": 0, "id": 1, "name": 1})}


def hist_avg_views(ms):
    n = sum(m["contents"] for m in ms if m["views"])
    return (sum(m["views"] for m in ms) / n) if n else None


def view(k, user, settings, names=None, ms=None):
    k = dict(k)
    k["tier"] = kol_tier(k, settings)
    k["indicator"] = kol_indicator(k, k["tier"], settings, hist_avg_views(ms or []))
    k["picName"] = (names or {}).get(k.get("picOfficerId"))
    if user["role"] not in ("Finance", "Manager"):
        k["bankAccount"] = mask(k.get("bankAccount", ""))
        k["npwp"] = mask(k.get("npwp", ""))
    if user["role"] == "Direksi":
        k.pop("contactWa", None)
    return k


async def check_dup(body: KolIn, exclude=None):
    for plat, h in (body.handles or {}).items():
        h = norm_handle(h)
        if not h:
            continue
        q = {f"handles.{plat}": {"$regex": f"^@?{re.escape(h)}$", "$options": "i"}}
        if exclude:
            q["id"] = {"$ne": exclude}
        other = await db.kols.find_one(q, {"_id": 0, "name": 1})
        if other:
            raise HTTPException(409, f"Handle {plat} @{h} sudah dipakai KOL {other['name']}")


def validate(body: KolIn, user):
    if body.tierOverride:
        if body.tierOverride not in TIERS:
            raise HTTPException(400, "Tier tidak dikenal")
        if user["role"] not in LEADS:
            raise HTTPException(403, "Override tier hanya oleh KOL TL / Manager")
        if not body.tierOverrideReason.strip():
            raise HTTPException(400, "Alasan override tier wajib diisi")
    if body.status == "Blacklist" and not body.blacklistReason.strip():
        raise HTTPException(400, "Alasan blacklist wajib diisi")
    if body.recommendationOverride and user["role"] not in LEADS:
        raise HTTPException(403, "Rekomendasi SCALE/KEEP/STOP hanya oleh KOL TL / Manager")


async def check_pic(uid):
    if not await db.users.find_one({"id": uid, "active": True, "role": {"$in": ["KOL Officer", "KOL TL", "Manager"]}}):
        raise HTTPException(400, "PIC harus user aktif KOL Officer / KOL Team Leader / Manager")


@router.get("")
async def list_kols(user=Depends(current_user)):
    settings = await get_settings()
    u = await load_universe()
    by_kol = defaultdict(list)
    for b in u["bookings"]:
        if b.get("status") in COMMITTED:
            by_kol[b["kolId"]].append(u["metrics"][b["id"]])
    out = []
    names = await user_names()
    for k in await db.kols.find({}, {"_id": 0}).sort("name").to_list(None):
        ms = by_kol.get(k["id"], [])
        v = view(k, user, settings, names, ms)
        late = sum(1 for m in ms if any(f["code"] == "report_overdue" for f in m["flags"]))
        v["stats"] = {
            "bookings": len(ms), "spend": sum(m["cost"] for m in ms),
            "views": sum(m["views"] for m in ms),
            "avgCpv": (sum(m["cost"] for m in ms) / sum(m["views"] for m in ms)) if sum(m["views"] for m in ms) else None,
            "avgEr": (sum(m["engagement"] for m in ms) / sum(m["views"] for m in ms)) if sum(m["views"] for m in ms) else None,
            "revenueDirect": sum(m["revenueDirect"] for m in ms), "lateReports": late,
            "flags": sorted({f["label"] for m in ms for f in m["flags"]}),
        }
        v["recommendation"] = k.get("recommendationOverride") or recommend(ms)
        out.append(v)
    return out


@router.get("/{kid}")
async def get_kol(kid: str, user=Depends(current_user)):
    k = await db.kols.find_one({"id": kid}, {"_id": 0})
    if not k:
        raise HTTPException(404, "KOL tidak ditemukan")
    settings = await get_settings()
    u = await load_universe()
    hist = []
    ms = []
    for b in u["bookings"]:
        if b["kolId"] != kid:
            continue
        m = u["metrics"][b["id"]]
        c = u["campaigns"].get(b["campaignId"], {})
        hist.append({"booking": b, "campaign": {"id": c.get("id"), "name": c.get("name"), "category": c.get("category"), "month": c.get("month")}, "metrics": m})
        if b.get("status") != "CANCELLED":
            ms.append(m)
    ms_c = [h["metrics"] for h in hist if h["booking"].get("status") in COMMITTED]
    v = view(k, user, settings, await user_names(), ms_c)
    v["history"] = sorted(hist, key=lambda h: h["booking"].get("createdAt", ""), reverse=True)
    v["recommendation"] = k.get("recommendationOverride") or recommend(ms)
    v["recommendationAuto"] = recommend(ms)
    return v


@router.post("")
async def create_kol(body: KolIn, user=Depends(require(*EDITORS))):
    validate(body, user)
    await check_dup(body)
    doc = body.model_dump()
    if not doc.get("picOfficerId"):
        doc["picOfficerId"] = user["id"]
    await check_pic(doc["picOfficerId"])
    doc.update({"id": new_id(), "createdAt": now_iso(), "createdBy": user["name"]})
    await db.kols.insert_one(doc)
    await audit(user, "kol.create", doc["id"], after={"name": body.name})
    doc.pop("_id", None)
    return doc


@router.put("/{kid}")
async def update_kol(kid: str, body: KolIn, user=Depends(require(*EDITORS))):
    before = await db.kols.find_one({"id": kid}, {"_id": 0})
    if not before:
        raise HTTPException(404, "KOL tidak ditemukan")
    # field sensitif yang ditampilkan ter-mask tidak boleh menimpa nilai asli
    data = body.model_dump()
    for f in ("bankAccount", "npwp"):
        if "•" in (data.get(f) or ""):
            data[f] = before.get(f, "")
    if (data.get("tierOverride") or None) != (before.get("tierOverride") or None) or data.get("recommendationOverride") != before.get("recommendationOverride"):
        validate(body, user)
    elif body.status == "Blacklist" and not body.blacklistReason.strip():
        raise HTTPException(400, "Alasan blacklist wajib diisi")
    await check_dup(body, exclude=kid)
    if data.get("picOfficerId"):
        await check_pic(data["picOfficerId"])
    for f in data.get("insightFiles") or []:
        if not await db.files.find_one({"id": f}):
            raise HTTPException(400, "Screenshot insight tidak ditemukan, upload ulang")
    await db.kols.update_one({"id": kid}, {"$set": data})
    changed = {k: (before.get(k), v) for k, v in data.items() if before.get(k) != v and k not in ("bankAccount", "npwp")}
    await audit(user, "kol.update", kid, before={k: v[0] for k, v in changed.items()}, after={k: v[1] for k, v in changed.items()},
                reason=body.tierOverrideReason or body.blacklistReason or None)
    return {"ok": True}
