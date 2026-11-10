import json
import os
import smtplib
from email.message import EmailMessage
from datetime import timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pymongo.errors import DuplicateKeyError
from .config import BACKUP_DIR, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM, TZ
from .db import db, now_iso, today, week_monday, month_of
from .logic import get_settings
from .services import refresh_statuses
from . import reporting as R

COLLS = ["users", "kols", "campaigns", "bookings", "contents", "snapshots", "outlets", "outlet_sales", "budget", "settings", "audit", "files"]


async def once(job, key):
    try:
        await db.joblog.insert_one({"job": job, "key": key, "at": now_iso()})
        return True
    except DuplicateKeyError:
        return False


def send_mail(to, subject, body):
    if not SMTP_HOST or not to:
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = SMTP_FROM, to, subject
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        if SMTP_USER:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    return True


async def job_daily_refresh():
    if await once("daily_refresh", today().isoformat()):
        await refresh_statuses()


async def job_reminders():
    if not await once("reminders", today().isoformat()):
        return
    settings = await get_settings()
    async for u in db.users.find({"active": True, "role": {"$in": ["KOL Officer", "KOL TL"]}}, {"_id": 0}):
        t = await R.tasks(u)
        items = [f"- Snapshot {x['day']} {x['kol']} ({x['campaign']}){' TERLAMBAT' if x['late'] else ''}" for x in t["snapshots"]]
        items += [f"- Deliverable {x['kol']} due {x['dueDate']}" for x in t["deliverables"]]
        await db.notifications.insert_one({"userId": u["id"], "date": today().isoformat(), "items": items, "at": now_iso()})
        if items and u.get("email"):
            send_mail(u["email"], f"[KOL Ledger] {len(items)} tugas hari ini", "\n".join(items))


async def job_weekly_digest():
    mon = week_monday(today()) - timedelta(days=7)
    if not await once("weekly_digest", mon.isoformat()):
        return
    w = await R.weekly(mon.isoformat())
    a = w["agg"]
    body = (f"Tab 8 KOL minggu {w['week']} s/d {w['end']}\nBiaya: {R.rp(a['cost'])}\nViews: {R.n(a['views'])}\nRevenue DIRECT: {R.rp(a['revenueDirect'])}\n"
            f"ROI DIRECT: {R.times(a['roiDirect'])}\nTerlambat report/deliverable: {len(w['overdue'])}\n\n" +
            "\n".join(f"- {i['evidence']} → {i['implication']} ({i['owner']}, {i['deadline']})" for i in w["insights"]))
    await db.digests.insert_one({"type": "weekly", "week": w["week"], "body": body, "at": now_iso()})
    settings = await get_settings()
    send_mail(settings.get("digestRecipients"), f"[KOL Ledger] Digest mingguan {w['week']}", body)


async def job_review_draft():
    m = month_of(today().replace(day=1) - timedelta(days=1))
    if today().day != 3 or not await once("review_draft", m):
        return
    d = await R.review(m)
    await db.digests.insert_one({"type": "review", "month": m, "data": json.loads(json.dumps(d, default=str)), "at": now_iso()})


async def backup():
    stamp = now_iso().replace(":", "")[:15]
    path = os.path.join(BACKUP_DIR, f"backup-{stamp}.json")
    data = {c: await db[c].find({}, {"_id": 0}).to_list(None) for c in COLLS}
    with open(path, "w") as f:
        json.dump(data, f, default=str)
    files = sorted(x for x in os.listdir(BACKUP_DIR) if x.startswith("backup-"))
    for old in files[:-8]:
        os.remove(os.path.join(BACKUP_DIR, old))
    return path


async def job_backup():
    if await once("backup", today().isoformat()):
        await backup()


def start_scheduler():
    s = AsyncIOScheduler(timezone=TZ)
    s.add_job(job_daily_refresh, "cron", hour=0, minute=10)
    s.add_job(job_reminders, "cron", hour=9, minute=0)
    s.add_job(job_weekly_digest, "cron", day_of_week="mon", hour=8, minute=0)
    s.add_job(job_review_draft, "cron", hour=8, minute=0)
    s.add_job(job_backup, "cron", day_of_week="sun", hour=2, minute=0)
    s.start()
    return s
