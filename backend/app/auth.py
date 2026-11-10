from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import Depends, HTTPException, Header
from .config import JWT_SECRET, JWT_HOURS
from .db import db

ALG = "HS256"


def hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()


def check_pin(pin: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(pin.encode(), h.encode())
    except Exception:
        return False


def make_token(user: dict) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=JWT_HOURS)
    return jwt.encode({"sub": user["id"], "role": user["role"], "exp": exp}, JWT_SECRET, algorithm=ALG)


async def current_user(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Silakan login dulu")
    try:
        data = jwt.decode(authorization[7:], JWT_SECRET, algorithms=[ALG])
    except jwt.PyJWTError:
        raise HTTPException(401, "Sesi berakhir, silakan login lagi")
    u = await db.users.find_one({"id": data["sub"], "active": True}, {"_id": 0, "pinHash": 0})
    if not u:
        raise HTTPException(401, "User tidak aktif")
    return u


def require(*roles):
    async def dep(user=Depends(current_user)):
        if roles and user["role"] not in roles:
            raise HTTPException(403, f"Akses ditolak untuk role {user['role']}")
        return user
    return dep


EDITORS = ("KOL Officer", "KOL TL", "Manager")
LEADS = ("KOL TL", "Manager")
