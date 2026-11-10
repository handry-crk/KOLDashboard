import uuid
from datetime import datetime, date, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from .config import MONGO_URL, DB_NAME, TZ

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now() -> datetime:
    return datetime.now(TZ)


def now_iso() -> str:
    return now().isoformat(timespec="seconds")


def today() -> date:
    return now().date()


def parse_date(s) -> date | None:
    if not s:
        return None
    if isinstance(s, date) and not isinstance(s, datetime):
        return s
    return date.fromisoformat(str(s)[:10])


def days_since(s) -> int | None:
    d = parse_date(s)
    return None if d is None else (today() - d).days


def clean(doc):
    if doc is None:
        return None
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


async def find_all(coll, query=None, sort=None, limit=0):
    cur = db[coll].find(query or {}, {"_id": 0})
    if sort:
        cur = cur.sort(sort)
    if limit:
        cur = cur.limit(limit)
    return await cur.to_list(length=None)


async def audit(user, what, ref=None, before=None, after=None, reason=None):
    await db.audit.insert_one({
        "id": new_id(), "at": now_iso(), "by": user.get("name") if user else "system",
        "role": user.get("role") if user else "system", "what": what, "ref": ref,
        "before": before, "after": after, "reason": reason,
    })


async def ensure_indexes():
    await db.users.create_index("id", unique=True)
    await db.kols.create_index("id", unique=True)
    await db.campaigns.create_index("id", unique=True)
    await db.bookings.create_index("id", unique=True)
    await db.bookings.create_index("campaignId")
    await db.contents.create_index("id", unique=True)
    await db.contents.create_index("url", unique=True)
    await db.contents.create_index("bookingId")
    await db.snapshots.create_index([("contentId", 1), ("day", 1)], unique=True)
    await db.outlet_sales.create_index([("outletCode", 1), ("date", 1)], unique=True)
    await db.outlets.create_index("code", unique=True)
    await db.budget.create_index([("month", 1), ("category", 1)], unique=True)
    await db.joblog.create_index([("job", 1), ("key", 1)], unique=True)


def month_of(d) -> str:
    return str(d)[:7]


def week_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())
