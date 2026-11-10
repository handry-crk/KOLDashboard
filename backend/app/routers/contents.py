import io
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from PIL import Image
from ..auth import current_user, require, EDITORS, LEADS
from ..config import FILE_DIR
from ..db import db, new_id, now_iso, audit, parse_date, today
from ..logic import CATEGORIES, METRIC_LABELS, detect_platform, norm_handle, SNAP_DAYS, COMMITTED
from ..services import snapshot_locked, snapshot_available

router = APIRouter(prefix="/api")


class ContentIn(BaseModel):
    bookingId: str
    url: str
    postedAt: str
    format: str = "Video"
    captionSnippet: str = ""
    isCollab: bool = False
    adsBoosted: bool = False
    boostCostRp: int = 0
    proofFiles: list[str] = []
    handleMismatchReason: str = ""
    status: str = "Live"


class SnapshotIn(BaseModel):
    contentId: str
    day: str
    values: dict
    proofFiles: list[str] = []
    reason: str = ""


@router.post("/contents")
async def add_content(body: ContentIn, user=Depends(require(*EDITORS))):
    b = await db.bookings.find_one({"id": body.bookingId}, {"_id": 0})
    if not b:
        raise HTTPException(404, "Booking tidak ditemukan")
    if b["status"] not in COMMITTED or b["status"] == "PAID":
        raise HTTPException(400, "Konten hanya bisa ditambahkan untuk booking yang sudah DEAL")
    url = body.url.strip().split("?")[0]
    if not url.startswith("http"):
        raise HTTPException(400, "Link post tidak valid")
    if await db.contents.find_one({"url": url}):
        raise HTTPException(409, "Link ini sudah tercatat")
    pd = parse_date(body.postedAt)
    if pd > today():
        raise HTTPException(400, "Tanggal tayang tidak boleh di masa depan")
    platform, handle = detect_platform(url)
    kol = await db.kols.find_one({"id": b["kolId"]}, {"_id": 0})
    kol_handles = {norm_handle(h) for h in (kol.get("handles") or {}).values() if h}
    if handle and norm_handle(handle) not in kol_handles and not body.handleMismatchReason.strip():
        raise HTTPException(409, f"handle_mismatch: Link dari @{handle}, bukan handle {kol['name']}. Isi alasan (mis. collab post) untuk tetap menyimpan.")
    doc = body.model_dump()
    doc.update({"id": new_id(), "url": url, "platform": platform, "detectedHandle": handle,
                "createdAt": now_iso(), "createdBy": user["name"]})
    await db.contents.insert_one(doc)
    if b["status"] in ("DEAL", "BRIEF_SENT", "DRAFT_REVIEW"):
        await db.bookings.update_one({"id": b["id"]}, {"$set": {"status": "POSTED", "statusAt": now_iso()},
                                                       "$push": {"history": {"from": b["status"], "to": "POSTED", "by": user["name"], "at": now_iso(), "reason": "Konten pertama tayang"}}})
    await audit(user, "content.create", doc["id"], after={"url": url, "booking": b["id"]}, reason=body.handleMismatchReason or None)
    doc.pop("_id", None)
    return doc


@router.put("/contents/{cid}")
async def update_content(cid: str, body: ContentIn, user=Depends(require(*EDITORS))):
    ct = await db.contents.find_one({"id": cid}, {"_id": 0})
    if not ct:
        raise HTTPException(404, "Konten tidak ditemukan")
    upd = {"status": body.status, "format": body.format, "captionSnippet": body.captionSnippet, "isCollab": body.isCollab,
           "adsBoosted": body.adsBoosted, "boostCostRp": body.boostCostRp, "proofFiles": body.proofFiles}
    if body.postedAt != ct["postedAt"]:
        if user["role"] not in LEADS:
            raise HTTPException(403, "Tanggal tayang hanya diubah KOL TL / Manager")
        upd["postedAt"] = body.postedAt
    await db.contents.update_one({"id": cid}, {"$set": upd})
    await audit(user, "content.update", cid, before={k: ct.get(k) for k in upd}, after=upd)
    return {"ok": True}


@router.delete("/contents/{cid}")
async def delete_content(cid: str, user=Depends(require(*LEADS))):
    if await db.snapshots.find_one({"contentId": cid}):
        raise HTTPException(400, "Konten sudah punya metrik; tandai Dihapus/Private, jangan dihapus")
    await db.contents.delete_one({"id": cid})
    await audit(user, "content.delete", cid)
    return {"ok": True}


@router.post("/snapshots")
async def upsert_snapshot(body: SnapshotIn, user=Depends(require(*EDITORS))):
    if body.day not in SNAP_DAYS:
        raise HTTPException(400, "Hari snapshot tidak dikenal")
    ct = await db.contents.find_one({"id": body.contentId}, {"_id": 0})
    if not ct:
        raise HTTPException(404, "Konten tidak ditemukan")
    b = await db.bookings.find_one({"id": ct["bookingId"]}, {"_id": 0})
    c = await db.campaigns.find_one({"id": b["campaignId"]}, {"_id": 0})
    if not snapshot_available(body.day, ct["postedAt"]):
        raise HTTPException(400, f"Snapshot {body.day} baru bisa diisi {body.day.replace('H', 'H+')} hari setelah tayang")
    fields = CATEGORIES[c["category"]]["fields"]
    vals = {}
    for f in fields:
        v = body.values.get(f)
        if v is None or v == "":
            raise HTTPException(400, f"{METRIC_LABELS[f]} wajib diisi (0 boleh, kosong tidak)")
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise HTTPException(400, f"{METRIC_LABELS[f]} harus angka")
        if v < 0:
            raise HTTPException(400, f"{METRIC_LABELS[f]} tidak boleh negatif")
        if f == "audienceLocalPct" and v > 100:
            raise HTTPException(400, "% audiens maksimal 100")
        vals[f] = int(v) if f != "audienceLocalPct" else v
    for f in ("reach", "profileVisits"):  # opsional
        if f not in fields and body.values.get(f) not in (None, ""):
            vals[f] = int(float(body.values[f]))
    if not body.proofFiles:
        raise HTTPException(400, "Screenshot insight wajib diunggah sebagai bukti")
    if vals.get("views") is not None:
        eng = sum(vals.get(k, 0) for k in ("likes", "comments", "shares", "saves"))
        if eng > vals["views"] * 1.5 and vals["views"] > 0:
            raise HTTPException(400, "Engagement lebih besar dari views, cek kembali angka")
    existing = await db.snapshots.find_one({"contentId": body.contentId, "day": body.day}, {"_id": 0})
    if existing:
        if snapshot_locked(existing, ct["postedAt"]):
            if user["role"] not in LEADS:
                raise HTTPException(403, "Metrik sudah terkunci (lewat H+7). Perubahan harus oleh KOL TL.")
            if len(body.reason.strip()) < 5:
                raise HTTPException(400, "Alasan perubahan metrik terkunci wajib diisi")
    doc = {**vals, "contentId": body.contentId, "day": body.day, "proofFiles": body.proofFiles,
           "enteredBy": user["name"], "enteredAt": existing.get("enteredAt") if existing else now_iso(),
           "updatedAt": now_iso(), "id": existing["id"] if existing else new_id()}
    await db.snapshots.update_one({"contentId": body.contentId, "day": body.day}, {"$set": doc}, upsert=True)
    if existing:
        await audit(user, "snapshot.update", doc["id"], before={k: existing.get(k) for k in vals}, after=vals, reason=body.reason or None)
    else:
        await audit(user, "snapshot.create", doc["id"], after=vals)
    # REPORT_DUE kembali ke POSTED bila H7 sudah masuk
    if body.day in ("H7", "H30") and b["status"] == "REPORT_DUE":
        others = await db.contents.find({"bookingId": b["id"]}, {"_id": 0}).to_list(None)
        ok = True
        for o in others:
            if o["id"] == body.contentId:
                continue
            if not await db.snapshots.find_one({"contentId": o["id"], "day": {"$in": ["H7", "H30"]}}):
                ok = False
        if ok:
            await db.bookings.update_one({"id": b["id"]}, {"$set": {"status": "POSTED", "statusAt": now_iso()},
                                                           "$push": {"history": {"from": "REPORT_DUE", "to": "POSTED", "by": user["name"], "at": now_iso(), "reason": "Snapshot H+7 masuk"}}})
    return {"ok": True, "id": doc["id"]}


# ----------------------------------------------------------------- File
ALLOWED = {"image/jpeg": ".jpg", "image/png": ".jpg", "image/webp": ".jpg", "image/heic": ".jpg", "application/pdf": ".pdf"}


@router.post("/files")
async def upload(file: UploadFile = File(...), user=Depends(current_user)):
    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(400, "File maksimal 8 MB")
    ctype = file.content_type or ""
    if ctype not in ALLOWED:
        raise HTTPException(400, "Format harus JPG/PNG/WEBP/PDF")
    fid = new_id() + new_id()
    if ctype == "application/pdf":
        name = fid + ".pdf"
        with open(os.path.join(FILE_DIR, name), "wb") as f:
            f.write(data)
    else:
        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception:
            raise HTTPException(400, "Gambar tidak bisa dibaca")
        img.thumbnail((1440, 1440))
        name = fid + ".jpg"
        q = 82
        while True:
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=q, optimize=True)
            if buf.tell() <= 500 * 1024 or q <= 40:
                break
            q -= 10
        with open(os.path.join(FILE_DIR, name), "wb") as f:
            f.write(buf.getvalue())
    await db.files.insert_one({"id": name, "by": user["name"], "at": now_iso(), "origName": file.filename})
    return {"id": name, "url": f"/api/files/{name}"}


@router.get("/files/{name}")
async def get_file(name: str):
    if "/" in name or ".." in name:
        raise HTTPException(400, "Nama file tidak valid")
    p = os.path.join(FILE_DIR, name)
    if not os.path.exists(p):
        raise HTTPException(404, "File tidak ditemukan")
    return FileResponse(p)
