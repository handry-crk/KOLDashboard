import re
import time
from collections import defaultdict, deque
from datetime import timedelta
from fastapi import Request
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..auth import hash_pin, check_pin, make_token, current_user, require
from ..db import db, new_id, now, now_iso, audit
from ..logic import ROLES, get_settings, DEFAULT_SETTINGS
from ..config import ALLOWED_EMAIL_DOMAIN

router = APIRouter(prefix="/api")


class LoginIn(BaseModel):
    userId: str
    pin: str


@router.get("/auth/users")
async def login_users():
    return await db.users.find({"active": True}, {"_id": 0, "id": 1, "name": 1, "role": 1}).sort("name").to_list(None)


@router.post("/auth/login")
async def login(body: LoginIn):
    u = await db.users.find_one({"id": body.userId, "active": True}, {"_id": 0})
    if not u:
        raise HTTPException(404, "User tidak ditemukan")
    lu = u.get("lockedUntil")
    if lu and lu > now_iso():
        raise HTTPException(423, "Terlalu banyak PIN salah. Coba lagi dalam 15 menit.")
    if not check_pin(body.pin, u["pinHash"]):
        failed = (u.get("failed") or 0) + 1
        upd = {"failed": failed}
        if failed >= 5:
            upd = {"failed": 0, "lockedUntil": (now() + timedelta(minutes=15)).isoformat(timespec="seconds")}
        await db.users.update_one({"id": u["id"]}, {"$set": upd})
        raise HTTPException(401, f"PIN salah ({failed}/5)" if failed < 5 else "PIN salah 5 kali. Akun dikunci 15 menit.")
    await db.users.update_one({"id": u["id"]}, {"$set": {"failed": 0, "lockedUntil": None, "lastLogin": now_iso()}})
    u.pop("pinHash", None)
    return {"token": make_token(u), "user": u}


SELF_ROLES = ("KOL TL", "KOL Officer")
_reg_hits = defaultdict(deque)


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    email: str
    role: str
    pin: str


def norm_email(e: str) -> str:
    return (e or "").strip().lower()


@router.get("/auth/register-info")
async def register_info():
    return {"domain": ALLOWED_EMAIL_DOMAIN, "roles": [{"value": "KOL TL", "label": "KOL Team Leader"}, {"value": "KOL Officer", "label": "KOL Officer"}]}


@router.post("/auth/register")
async def register(body: RegisterIn, request: Request):
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()
    q = _reg_hits[ip]
    t = time.time()
    while q and t - q[0] > 3600:
        q.popleft()
    if len(q) >= 10:
        raise HTTPException(429, "Terlalu banyak percobaan pendaftaran. Coba lagi nanti.")
    q.append(t)
    email = norm_email(body.email)
    if not re.fullmatch(r"[a-z0-9._%+\-]+@" + re.escape(ALLOWED_EMAIL_DOMAIN), email):
        raise HTTPException(400, f"Hanya email @{ALLOWED_EMAIL_DOMAIN} yang bisa mendaftar")
    if body.role not in SELF_ROLES:
        raise HTTPException(400, "Role pendaftaran hanya KOL Team Leader atau KOL Officer")
    if not re.fullmatch(r"\d{4,8}", body.pin or ""):
        raise HTTPException(400, "PIN harus 4–8 digit angka")
    name = " ".join(body.name.split())
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        st = existing.get("status") or ("active" if existing.get("active") else "inactive")
        if st == "pending":
            raise HTTPException(409, "Email ini sudah mendaftar dan sedang menunggu approval admin")
        if st != "rejected":
            raise HTTPException(409, "Email ini sudah terdaftar. Silakan login atau hubungi admin.")
        await db.users.delete_one({"id": existing["id"]})  # boleh daftar ulang setelah ditolak
    if await db.users.find_one({"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}, "status": {"$ne": "rejected"}}):
        raise HTTPException(409, "Nama ini sudah dipakai. Tambahkan nama belakang/inisial.")
    doc = {"id": new_id(), "name": name, "email": email, "role": body.role, "requestedRole": body.role, "active": False,
           "status": "pending", "pinHash": hash_pin(body.pin), "registeredAt": now_iso(), "createdAt": now_iso(), "source": "self"}
    await db.users.insert_one(doc)
    await audit({"name": name, "role": "pendaftar"}, "user.register", doc["id"], after={"email": email, "role": body.role})
    return {"ok": True, "status": "pending", "message": "Pendaftaran terkirim. Akun aktif setelah di-approve admin."}


class ApproveIn(BaseModel):
    role: str | None = None
    reason: str = ""


@router.get("/users/pending")
async def pending_users(user=Depends(require("Manager"))):
    return await db.users.find({"status": "pending"}, {"_id": 0, "pinHash": 0}).sort("registeredAt", 1).to_list(None)


@router.post("/users/{uid}/approve")
async def approve_user(uid: str, body: ApproveIn, user=Depends(require("Manager"))):
    u = await db.users.find_one({"id": uid, "status": "pending"}, {"_id": 0})
    if not u:
        raise HTTPException(404, "Pendaftaran tidak ditemukan / sudah diproses")
    role = body.role or u["role"]
    if role not in SELF_ROLES:
        raise HTTPException(400, "Role hanya KOL Team Leader atau KOL Officer")
    await db.users.update_one({"id": uid}, {"$set": {"status": "active", "active": True, "role": role, "approvedBy": user["name"], "approvedAt": now_iso()}})
    await audit(user, "user.approve", uid, after={"email": u.get("email"), "role": role})
    return {"ok": True}


@router.post("/users/{uid}/reject")
async def reject_user(uid: str, body: ApproveIn, user=Depends(require("Manager"))):
    u = await db.users.find_one({"id": uid, "status": "pending"}, {"_id": 0})
    if not u:
        raise HTTPException(404, "Pendaftaran tidak ditemukan / sudah diproses")
    if len(body.reason.strip()) < 3:
        raise HTTPException(400, "Alasan penolakan wajib diisi")
    await db.users.update_one({"id": uid}, {"$set": {"status": "rejected", "active": False, "rejectedBy": user["name"], "rejectedAt": now_iso(), "rejectReason": body.reason}})
    await audit(user, "user.reject", uid, after={"email": u.get("email")}, reason=body.reason)
    return {"ok": True}


@router.get("/auth/me")
async def me(user=Depends(current_user)):
    return user


class UserIn(BaseModel):
    name: str = Field(min_length=2)
    role: str
    pin: str | None = None
    email: str | None = ""
    active: bool = True


@router.get("/users")
async def list_users(user=Depends(require("Manager", "KOL TL"))):
    return await db.users.find({"status": {"$nin": ["pending", "rejected"]}}, {"_id": 0, "pinHash": 0}).sort("name").to_list(None)


@router.post("/users")
async def create_user(body: UserIn, user=Depends(require("Manager"))):
    if body.role not in ROLES:
        raise HTTPException(400, "Role tidak dikenal")
    if not body.pin or len(body.pin) < 4:
        raise HTTPException(400, "PIN minimal 4 digit")
    if body.email and await db.users.find_one({"email": body.email.strip().lower()}):
        raise HTTPException(409, "Email sudah dipakai user lain")
    doc = {"id": new_id(), "name": body.name, "role": body.role, "email": (body.email or "").strip().lower(), "active": body.active, "status": "active" if body.active else "inactive",
           "pinHash": hash_pin(body.pin), "createdAt": now_iso()}
    await db.users.insert_one(doc)
    await audit(user, "user.create", doc["id"], after={"name": body.name, "role": body.role})
    doc.pop("_id", None); doc.pop("pinHash")
    return doc


@router.put("/users/{uid}")
async def update_user(uid: str, body: UserIn, user=Depends(require("Manager"))):
    upd = {"name": body.name, "role": body.role, "email": (body.email or "").strip().lower(), "active": body.active,
           "status": "active" if body.active else "inactive"}
    if body.pin:
        if len(body.pin) < 4:
            raise HTTPException(400, "PIN minimal 4 digit")
        upd["pinHash"] = hash_pin(body.pin)
    r = await db.users.update_one({"id": uid}, {"$set": upd})
    if not r.matched_count:
        raise HTTPException(404, "User tidak ditemukan")
    await audit(user, "user.update", uid, after={k: v for k, v in upd.items() if k != "pinHash"})
    return {"ok": True}


@router.get("/settings")
async def read_settings(user=Depends(current_user)):
    return await get_settings()


@router.put("/settings")
async def write_settings(body: dict, user=Depends(require("Manager"))):
    before = await get_settings()
    allowed = set(DEFAULT_SETTINGS.keys()) - {"id"}
    upd = {k: v for k, v in body.items() if k in allowed}
    await db.settings.update_one({"id": "settings"}, {"$set": upd}, upsert=True)
    await audit(user, "settings.update", "settings", before={k: before.get(k) for k in upd}, after=upd)
    return await get_settings()


@router.get("/meta")
async def meta(user=Depends(current_user)):
    from ..logic import CATEGORIES, METRIC_LABELS, TIERS, STATUSES, SNAP_DAYS
    return {"categories": CATEGORIES, "metricLabels": METRIC_LABELS, "tiers": TIERS, "statuses": STATUSES,
            "roles": ROLES, "snapDays": SNAP_DAYS}
