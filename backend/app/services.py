from datetime import timedelta
from .db import db, now_iso, days_since, parse_date, now, audit
from .logic import get_settings, SNAP_OFFSET

SYSTEM = {"name": "system", "role": "system"}


async def refresh_statuses():
    """POSTED dengan konten ≥ H+7 tanpa snapshot H7 → REPORT_DUE."""
    settings = await get_settings()
    changed = 0
    async for b in db.bookings.find({"status": "POSTED"}, {"_id": 0}):
        contents = await db.contents.find({"bookingId": b["id"]}, {"_id": 0}).to_list(None)
        for ct in contents:
            ds = days_since(ct.get("postedAt"))
            if ds is not None and ds >= settings["reportFinalDays"]:
                has = await db.snapshots.find_one({"contentId": ct["id"], "day": {"$in": ["H7", "H30"]}})
                if not has:
                    await db.bookings.update_one({"id": b["id"]}, {"$set": {"status": "REPORT_DUE", "statusAt": now_iso()},
                                                                  "$push": {"history": {"from": "POSTED", "to": "REPORT_DUE", "by": "system", "at": now_iso()}}})
                    await audit(SYSTEM, "booking.auto_report_due", b["id"])
                    changed += 1
                    break
    return changed


def snapshot_locked(snap: dict, posted_at: str) -> bool:
    if not snap or not snap.get("enteredAt"):
        return False
    d0 = parse_date(posted_at)
    lock_days = 30 if snap.get("day") == "H30" else 7
    lock_at = max(d0 + timedelta(days=lock_days + 1), parse_date(snap["enteredAt"]) + timedelta(days=1))
    return now().date() >= lock_at


def snapshot_available(day: str, posted_at: str) -> bool:
    ds = days_since(posted_at)
    return ds is not None and ds >= SNAP_OFFSET[day]
