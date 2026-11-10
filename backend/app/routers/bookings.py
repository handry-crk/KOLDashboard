from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..auth import current_user, require, EDITORS, LEADS
from ..db import db, new_id, now_iso, audit, today, parse_date
from ..logic import (STATUSES, COMMITTED, CATEGORIES, get_settings, kol_tier, total_cost, load_universe,
                     norm_handle)
from ..services import refresh_statuses, snapshot_locked
from .campaigns import fmt_rp

router = APIRouter(prefix="/api")
IDX = {s: i for i, s in enumerate(STATUSES)}


class BookingIn(BaseModel):
    campaignId: str
    kolId: str
    platform: str = "tiktok"
    deliverables: list[dict] = []   # [{format, qty, dueDate}]
    costs: dict = {}                # feeRp, productRp, transportRp, otherRp, commissionPct
    trackingLink: str = ""
    uniqueCode: str = ""
    contentRights: dict = {}        # {repostDays, adsUsage}
    notes: str = ""


class TransitionIn(BaseModel):
    to: str
    reason: str = ""


class PayIn(BaseModel):
    amountRp: int = Field(ge=0)
    proofFiles: list[str] = []
    invoiceFiles: list[str] = []
    note: str = ""
    overrideReason: str = ""


def needs_approval(b, settings):
    return b.get("tierAtBooking") in ("Macro", "Mega") or total_cost(b.get("costs")) >= settings["approvalThresholdRp"]


def has_manager_approval(b):
    return any(a.get("role") == "Manager" and a.get("decision", "approve") == "approve" for a in (b.get("approvals") or []))


async def check_deal(b, settings, campaign):
    if campaign.get("gateStatus") == "HOLD":
        raise HTTPException(400, "Campaign berstatus HOLD di Activity Gate")
    if int(campaign.get("budgetRp") or 0) >= settings["approvalThresholdRp"] and campaign.get("gateStatus") not in ("GO", "GWC"):
        raise HTTPException(400, f"Campaign ≥ {fmt_rp(settings['approvalThresholdRp'])} wajib Activity Gate GO/GWC sebelum DEAL")
    committed = 0
    async for x in db.bookings.find({"campaignId": campaign["id"], "status": {"$in": list(COMMITTED)}, "id": {"$ne": b["id"]}}, {"_id": 0}):
        committed += total_cost(x.get("costs"))
    remaining = int(campaign.get("budgetRp") or 0) - committed
    if total_cost(b.get("costs")) > remaining:
        raise HTTPException(400, f"Biaya booking {fmt_rp(total_cost(b.get('costs')))} melebihi sisa budget campaign (sisa {fmt_rp(max(remaining, 0))})")
    if needs_approval(b, settings) and not has_manager_approval(b):
        raise HTTPException(400, "Butuh approval Manager (tier Macro/Mega atau biaya di atas batas). Pindahkan ke WAITING_APPROVAL.")


async def check_report_complete(b, campaign):
    contents = await db.contents.find({"bookingId": b["id"]}, {"_id": 0}).to_list(None)
    if not contents:
        raise HTTPException(400, "Belum ada konten tayang")
    fields = CATEGORIES[campaign["category"]]["fields"]
    for ct in contents:
        s = await db.snapshots.find_one({"contentId": ct["id"], "day": {"$in": ["H7", "H30"]}}, {"_id": 0})
        if not s:
            raise HTTPException(400, f"Snapshot H+7 belum ada untuk {ct['url']}")
        missing = [f for f in fields if s.get(f) is None]
        if missing:
            raise HTTPException(400, f"Field wajib kosong di H+7: {', '.join(missing)}")
        if not s.get("proofFiles"):
            raise HTTPException(400, "Screenshot insight H+7 wajib diunggah")


def push_hist(frm, to, user, reason=""):
    return {"from": frm, "to": to, "by": user["name"], "role": user["role"], "at": now_iso(), "reason": reason}


async def do_transition(b, to, user, reason=""):
    settings = await get_settings()
    campaign = await db.campaigns.find_one({"id": b["campaignId"]}, {"_id": 0})
    frm = b["status"]
    if to not in IDX:
        raise HTTPException(400, "Status tidak dikenal")
    if to == frm:
        return b
    role = user["role"]
    if role in ("Direksi",):
        raise HTTPException(403, "Direksi hanya dapat melihat")
    if to == "PAID":
        raise HTTPException(400, "Pelunasan dilakukan Finance lewat menu Pembayaran")
    if role == "Finance":
        raise HTTPException(403, "Finance hanya mencatat pembayaran")
    if to == "CANCELLED":
        if frm == "PAID":
            raise HTTPException(400, "Booking yang sudah lunas tidak bisa dibatalkan")
        if len(reason.strip()) < 5:
            raise HTTPException(400, "Alasan pembatalan wajib diisi")
    elif frm == "CANCELLED" or IDX[to] < IDX[frm]:
        if role not in LEADS:
            raise HTTPException(403, "Mundur status hanya oleh KOL TL / Manager")
        if len(reason.strip()) < 5:
            raise HTTPException(400, "Alasan wajib diisi untuk mundur status / menolak report")
    else:
        if IDX[to] >= IDX["DEAL"] and not b.get("dealAt"):
            await check_deal(b, settings, campaign)
        if IDX[to] >= IDX["POSTED"]:
            n = await db.contents.count_documents({"bookingId": b["id"]})
            if not n:
                raise HTTPException(400, "Tambahkan link konten yang sudah tayang dulu")
        if IDX[to] >= IDX["REPORT_SUBMITTED"]:
            await check_report_complete(b, campaign)
        if to == "REPORT_APPROVED":
            if role not in LEADS:
                raise HTTPException(403, "Report hanya di-approve KOL TL / Manager")
            if frm != "REPORT_SUBMITTED":
                raise HTTPException(400, "Report harus disubmit officer dulu (REPORT_SUBMITTED)")
    upd = {"status": to, "statusAt": now_iso()}
    if IDX.get(to, 0) >= IDX["DEAL"] and to != "CANCELLED" and not b.get("dealAt"):
        upd["dealAt"] = now_iso()
    if to == "CANCELLED" or (IDX[to] < IDX["DEAL"]):
        upd["dealAt"] = None
    if to == "REPORT_APPROVED":
        upd["reportApprovedBy"] = user["name"]; upd["reportApprovedAt"] = now_iso()
    await db.bookings.update_one({"id": b["id"]}, {"$set": upd, "$push": {"history": push_hist(frm, to, user, reason)}})
    await audit(user, "booking.transition", b["id"], before={"status": frm}, after={"status": to}, reason=reason or None)
    return {**b, **upd}


def enrich(b, u):
    k = u["kols"].get(b["kolId"], {})
    c = u["campaigns"].get(b["campaignId"], {})
    return {**b, "totalCostRp": total_cost(b.get("costs")),
            "kol": {"id": k.get("id"), "name": k.get("name"), "handles": k.get("handles"), "followers": k.get("followers")},
            "campaign": {"id": c.get("id"), "name": c.get("name"), "category": c.get("category"), "month": c.get("month"), "code": c.get("code"), "gateStatus": c.get("gateStatus")},
            "metrics": u["metrics"].get(b["id"])}


@router.get("/bookings")
async def list_bookings(campaignId: str | None = None, month: str | None = None, status: str | None = None,
                        officer: str | None = None, user=Depends(current_user)):
    await refresh_statuses()
    cq = {"month": month} if month else None
    if campaignId:
        cq = {"id": campaignId}
    bq = {}
    if status:
        bq["status"] = status
    if officer:
        bq["createdById"] = officer
    u = await load_universe(campaign_query=cq, booking_query=bq or None)
    out = [enrich(b, u) for b in u["bookings"]]
    out.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    return out


@router.get("/bookings/{bid}")
async def get_booking(bid: str, user=Depends(current_user)):
    b = await db.bookings.find_one({"id": bid}, {"_id": 0})
    if not b:
        raise HTTPException(404, "Booking tidak ditemukan")
    u = await load_universe(booking_query={"id": bid})
    settings = u["settings"]
    out = enrich(u["bookings"][0], u)
    c = u["campaigns"][b["campaignId"]]
    cts = []
    for ct in u["contents_by_booking"].get(bid, []):
        snaps = sorted(u["snaps_by_content"].get(ct["id"], []), key=lambda s: s["day"])
        for s in snaps:
            s["locked"] = snapshot_locked(s, ct.get("postedAt"))
        cts.append({**ct, "snapshots": snaps})
    out["contents"] = cts
    out["requiredFields"] = CATEGORIES[c["category"]]["fields"]
    out["needsApproval"] = needs_approval(b, settings)
    out["hasApproval"] = has_manager_approval(b)
    return out


async def build_doc(body: BookingIn, user, existing=None):
    settings = await get_settings()
    campaign = await db.campaigns.find_one({"id": body.campaignId}, {"_id": 0})
    if not campaign:
        raise HTTPException(404, "Campaign tidak ditemukan")
    if campaign.get("gateStatus") in ("HOLD", "SELESAI") and not existing:
        raise HTTPException(400, f"Campaign berstatus {campaign['gateStatus']}, tidak bisa menambah booking")
    kol = await db.kols.find_one({"id": body.kolId}, {"_id": 0})
    if not kol:
        raise HTTPException(404, "KOL tidak ditemukan")
    if kol.get("status") == "Blacklist" and not existing:
        raise HTTPException(400, f"KOL {kol['name']} masuk Blacklist: {kol.get('blacklistReason', '')}")
    doc = body.model_dump()
    doc["tierAtBooking"] = existing.get("tierAtBooking") if existing and existing.get("dealAt") else kol_tier(kol, settings)
    if not doc["uniqueCode"]:
        h = norm_handle((kol.get("handles") or {}).get(body.platform) or kol["name"]).upper().replace(".", "").replace("_", "")[:12]
        doc["uniqueCode"] = f"{CATEGORIES[campaign['category']]['code']}-{h}"
    cost = total_cost(doc["costs"])
    committed = 0
    async for x in db.bookings.find({"campaignId": campaign["id"], "status": {"$in": list(COMMITTED)}}, {"_id": 0}):
        if not existing or x["id"] != existing["id"]:
            committed += total_cost(x.get("costs"))
    remaining = int(campaign.get("budgetRp") or 0) - committed
    if cost > remaining:
        raise HTTPException(400, f"Biaya {fmt_rp(cost)} melebihi sisa budget campaign {campaign['name']} (sisa {fmt_rp(max(remaining, 0))})")
    return doc, campaign, kol


@router.post("/bookings")
async def create_booking(body: BookingIn, user=Depends(require(*EDITORS))):
    doc, campaign, kol = await build_doc(body, user)
    dup = await db.bookings.find_one({"campaignId": body.campaignId, "kolId": body.kolId, "status": {"$ne": "CANCELLED"}})
    if dup:
        raise HTTPException(409, "KOL ini sudah ada di campaign yang sama")
    doc.update({"id": new_id(), "status": "SHORTLIST", "createdAt": now_iso(), "createdBy": user["name"],
                "createdById": user["id"], "approvals": [], "history": [push_hist(None, "SHORTLIST", user)],
                "payment": {"dpRp": 0, "paidRp": 0}, "dealAt": None})
    await db.bookings.insert_one(doc)
    await audit(user, "booking.create", doc["id"], after={"kol": kol["name"], "campaign": campaign["name"], "cost": total_cost(doc["costs"])})
    doc.pop("_id", None)
    return doc


@router.put("/bookings/{bid}")
async def update_booking(bid: str, body: BookingIn, user=Depends(require(*EDITORS))):
    b = await db.bookings.find_one({"id": bid}, {"_id": 0})
    if not b:
        raise HTTPException(404, "Booking tidak ditemukan")
    if b["status"] in ("REPORT_APPROVED", "PAID") and user["role"] not in LEADS:
        raise HTTPException(403, "Booking sudah di-approve; perubahan hanya oleh KOL TL / Manager")
    if body.campaignId != b["campaignId"] or body.kolId != b["kolId"]:
        raise HTTPException(400, "Campaign/KOL tidak bisa diganti; batalkan dan buat booking baru")
    doc, _, _ = await build_doc(body, user, existing=b)
    cost_changed = total_cost(doc["costs"]) != total_cost(b.get("costs"))
    if cost_changed and b.get("dealAt"):
        settings = await get_settings()
        if needs_approval({**b, **doc}, settings) and user["role"] != "Manager":
            # biaya berubah setelah DEAL → approval lama gugur
            doc["approvals"] = [a for a in b.get("approvals", []) if a.get("role") != "Manager"]
    await db.bookings.update_one({"id": bid}, {"$set": doc})
    await audit(user, "booking.update", bid, before={"costs": b.get("costs"), "deliverables": b.get("deliverables")},
                after={"costs": doc["costs"], "deliverables": doc["deliverables"]})
    return {"ok": True}


@router.post("/bookings/{bid}/transition")
async def transition(bid: str, body: TransitionIn, user=Depends(current_user)):
    b = await db.bookings.find_one({"id": bid}, {"_id": 0})
    if not b:
        raise HTTPException(404, "Booking tidak ditemukan")
    nb = await do_transition(b, body.to, user, body.reason)
    return {"ok": True, "status": nb["status"]}


@router.post("/bookings/{bid}/approve")
async def approve(bid: str, body: TransitionIn, user=Depends(require("Manager"))):
    """body.to = 'approve' | 'reject'"""
    b = await db.bookings.find_one({"id": bid}, {"_id": 0})
    if not b:
        raise HTTPException(404, "Booking tidak ditemukan")
    decision = "approve" if body.to != "reject" else "reject"
    entry = {"by": user["name"], "role": "Manager", "at": now_iso(), "note": body.reason, "decision": decision}
    await db.bookings.update_one({"id": bid}, {"$push": {"approvals": entry}})
    await audit(user, f"booking.{decision}", bid, reason=body.reason)
    b = await db.bookings.find_one({"id": bid}, {"_id": 0})
    if decision == "approve" and b["status"] == "WAITING_APPROVAL":
        await do_transition(b, "DEAL", user, "Disetujui Manager")
    if decision == "reject" and b["status"] == "WAITING_APPROVAL":
        await do_transition(b, "NEGO", user, body.reason or "Ditolak Manager")
    return {"ok": True}


# ----------------------------------------------------------------- Pembayaran
@router.get("/payments")
async def payments(user=Depends(require("Finance", "Manager", "KOL TL"))):
    u = await load_universe()
    rows = [enrich(b, u) for b in u["bookings"] if b["status"] in COMMITTED]
    for r in rows:
        r.pop("metrics", None)
        bank = u["kols"].get(r["kolId"], {}).get("bankAccount", "")
        r["kolBank"] = bank if user["role"] in ("Finance", "Manager") else (bank[:3] + "•••" + bank[-3:] if bank else "")
    queue = [r for r in rows if r["status"] == "REPORT_APPROVED"]
    dp = [r for r in rows if r["status"] not in ("REPORT_APPROVED", "PAID")]
    paid = [r for r in rows if r["status"] == "PAID"]
    return {"queue": queue, "running": dp, "paid": paid}


@router.post("/bookings/{bid}/dp")
async def pay_dp(bid: str, body: PayIn, user=Depends(require("Finance", "Manager"))):
    b = await db.bookings.find_one({"id": bid}, {"_id": 0})
    if not b:
        raise HTTPException(404, "Booking tidak ditemukan")
    if b["status"] not in COMMITTED or b["status"] == "PAID":
        raise HTTPException(400, "DP hanya untuk booking berstatus DEAL s/d sebelum lunas")
    if body.amountRp > total_cost(b.get("costs")):
        raise HTTPException(400, "DP melebihi total biaya")
    pay = b.get("payment") or {}
    pay.update({"dpRp": body.amountRp, "dpPaidAt": now_iso(), "dpProof": body.proofFiles, "dpBy": user["name"]})
    await db.bookings.update_one({"id": bid}, {"$set": {"payment": pay}})
    await audit(user, "payment.dp", bid, after={"dpRp": body.amountRp})
    return {"ok": True}


@router.post("/bookings/{bid}/pay")
async def pay_full(bid: str, body: PayIn, user=Depends(require("Finance", "Manager"))):
    b = await db.bookings.find_one({"id": bid}, {"_id": 0})
    if not b:
        raise HTTPException(404, "Booking tidak ditemukan")
    if b["status"] != "REPORT_APPROVED":
        if user["role"] != "Manager" or len(body.overrideReason.strip()) < 10:
            raise HTTPException(400, "Pelunasan hanya untuk booking yang report-nya sudah di-approve (REPORT_APPROVED). Override hanya Manager dengan alasan tertulis.")
        if b["status"] in ("CANCELLED", "SHORTLIST", "NEGO", "WAITING_APPROVAL"):
            raise HTTPException(400, "Booking belum DEAL")
    if not body.proofFiles:
        raise HTTPException(400, "Bukti transfer wajib diunggah")
    pay = b.get("payment") or {}
    pay.update({"paidRp": body.amountRp, "paidAt": now_iso(), "proof": body.proofFiles, "invoice": body.invoiceFiles,
                "paidBy": user["name"], "note": body.note, "overrideReason": body.overrideReason or None})
    await db.bookings.update_one({"id": bid}, {"$set": {"payment": pay, "status": "PAID", "statusAt": now_iso()},
                                               "$push": {"history": push_hist(b["status"], "PAID", user, body.overrideReason)}})
    await audit(user, "payment.paid" if not body.overrideReason else "payment.override", bid, before={"status": b["status"]},
                after={"paidRp": body.amountRp}, reason=body.overrideReason or None)
    return {"ok": True}
