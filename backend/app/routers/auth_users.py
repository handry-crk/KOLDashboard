from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..auth import hash_pin, check_pin, make_token, current_user, require
from ..db import db, new_id, now, now_iso, audit
from ..logic import ROLES, get_settings, DEFAULT_SETTINGS

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
    return await db.users.find({}, {"_id": 0, "pinHash": 0}).sort("name").to_list(None)


@router.post("/users")
async def create_user(body: UserIn, user=Depends(require("Manager"))):
    if body.role not in ROLES:
        raise HTTPException(400, "Role tidak dikenal")
    if not body.pin or len(body.pin) < 4:
        raise HTTPException(400, "PIN minimal 4 digit")
    doc = {"id": new_id(), "name": body.name, "role": body.role, "email": body.email, "active": body.active,
           "pinHash": hash_pin(body.pin), "createdAt": now_iso()}
    await db.users.insert_one(doc)
    await audit(user, "user.create", doc["id"], after={"name": body.name, "role": body.role})
    doc.pop("_id", None); doc.pop("pinHash")
    return doc


@router.put("/users/{uid}")
async def update_user(uid: str, body: UserIn, user=Depends(require("Manager"))):
    upd = {"name": body.name, "role": body.role, "email": body.email, "active": body.active}
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
