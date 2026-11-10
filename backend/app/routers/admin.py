import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from ..auth import require, current_user
from ..db import db
from ..seed import seed
from .. import jobs

router = APIRouter(prefix="/api/admin")


@router.post("/seed")
async def run_seed(user=Depends(require("Manager"))):
    r = await seed()
    if not r["seeded"]:
        raise HTTPException(400, "Data contoh hanya bisa diisi pada database kosong")
    return r


@router.post("/backup")
async def run_backup(user=Depends(require("Manager"))):
    p = await jobs.backup()
    return FileResponse(p, filename=os.path.basename(p), media_type="application/json")


@router.post("/jobs/{name}")
async def run_job(name: str, user=Depends(require("Manager"))):
    fn = {"refresh": jobs.job_daily_refresh, "reminders": jobs.job_reminders, "weekly": jobs.job_weekly_digest}.get(name)
    if not fn:
        raise HTTPException(404, "Job tidak dikenal")
    await db.joblog.delete_many({"job": {"refresh": "daily_refresh", "reminders": "reminders", "weekly": "weekly_digest"}[name]})
    await fn()
    return {"ok": True}


@router.get("/notifications")
async def notifications(user=Depends(current_user)):
    return await db.notifications.find({"userId": user["id"]}, {"_id": 0}).sort("at", -1).limit(7).to_list(None)
