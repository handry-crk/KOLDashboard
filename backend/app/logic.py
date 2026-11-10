"""Aturan bisnis KOL Ledger: kategori, tier, metrik, atribusi, flag."""
from datetime import timedelta
from collections import defaultdict
import re

from .db import db, parse_date, today, days_since

ENG = ["likes", "comments", "shares", "saves"]

# Konfigurasi kategori: field wajib di report, outcome utama, sumber revenue DIRECT, level bukti
CATEGORIES = {
    "Regular Visit": {
        "code": "RV", "fields": ["views"] + ENG + ["mapsClicks", "redemptions"],
        "outcome": "redemptions", "outcomeLabel": "Redemption kode di outlet",
        "revenue": "redemptions_x_aov", "evidence": ["DIRECT", "ASSISTED"], "assisted": True, "windowDays": 7,
        "objective": "Footfall & transaksi di outlet yang dikunjungi",
    },
    "Frozen": {
        "code": "FZ", "fields": ["views"] + ENG + ["linkClicks", "orders", "gmvRp"],
        "outcome": "orders", "outcomeLabel": "Order via link/voucher KOL",
        "revenue": "gmvRp", "evidence": ["DIRECT"], "assisted": False, "windowDays": 0,
        "objective": "Penjualan Frozen di Tokopedia/Shopee/WA reseller",
    },
    "NPL": {
        "code": "NPL", "fields": ["views", "reach"] + ENG,
        "outcome": "views", "outcomeLabel": "Views",
        "revenue": None, "evidence": ["EXPOSURE", "ASSISTED"], "assisted": True, "windowDays": 7,
        "objective": "Awareness & trial menu baru",
    },
    "Info Lokasi": {
        "code": "IL", "fields": ["views", "reach"] + ENG + ["audienceLocalPct", "mapsClicks"],
        "outcome": "mapsClicks", "outcomeLabel": "Klik Maps / direction",
        "revenue": None, "evidence": ["EXPOSURE", "ASSISTED"], "assisted": True, "windowDays": 14,
        "objective": "Kunjungan pertama ke titik baru/pindah",
    },
    "Keranjang Kuning": {
        "code": "KK", "fields": ["views"] + ENG + ["productClicks", "orders", "gmvRp", "commissionRp"],
        "outcome": "orders", "outcomeLabel": "Order TikTok Shop",
        "revenue": "gmvRp", "evidence": ["DIRECT"], "assisted": False, "windowDays": 0,
        "objective": "Jualan langsung via TikTok Shop affiliate",
    },
    "TikTok GO": {
        "code": "TG", "fields": ["views"] + ENG + ["vouchersSold", "vouchersRedeemed", "gmvRp"],
        "outcome": "vouchersRedeemed", "outcomeLabel": "Voucher TikTok GO ditukar",
        "revenue": "gmvRp", "evidence": ["DIRECT"], "assisted": False, "windowDays": 0,
        "objective": "Voucher TikTok GO terjual & ditukar di outlet",
    },
}

METRIC_LABELS = {
    "views": "Views", "reach": "Reach", "likes": "Likes", "comments": "Komentar", "shares": "Share",
    "saves": "Save", "profileVisits": "Kunjungan profil", "linkClicks": "Klik link", "mapsClicks": "Klik Maps",
    "audienceLocalPct": "% audiens kota target", "productClicks": "Klik produk", "orders": "Order",
    "gmvRp": "GMV (Rp)", "commissionRp": "Komisi (Rp)", "vouchersSold": "Voucher terjual",
    "vouchersRedeemed": "Voucher ditukar", "redemptions": "Redemption kode",
}

TIERS = ["Nano", "Micro", "Macro", "Mega"]
ROLES = ["KOL Officer", "KOL TL", "Manager", "Finance", "Direksi"]
STATUSES = ["SHORTLIST", "NEGO", "WAITING_APPROVAL", "DEAL", "BRIEF_SENT", "DRAFT_REVIEW", "POSTED",
            "REPORT_DUE", "REPORT_SUBMITTED", "REPORT_APPROVED", "PAID", "CANCELLED"]
COMMITTED = set(STATUSES[3:11])  # DEAL s/d PAID
POSTED_PLUS = set(STATUSES[6:11])
SNAP_DAYS = ["H1", "H3", "H7", "H30"]
SNAP_OFFSET = {"H1": 1, "H3": 3, "H7": 7, "H30": 30}

DEFAULT_SETTINGS = {
    "id": "settings",
    "monthlyKolPagu": 120_000_000,
    "approvalThresholdRp": 25_000_000,
    "gmBlended": 0.47,
    "aovRp": 15_000,
    "tierThresholds": {"Nano": 1_000, "Micro": 10_000, "Macro": 100_000, "Mega": 1_000_000},
    "reportSubmitDays": 3, "reportFinalDays": 7,
    "erFlagLow": 0.01, "erFlagHigh": 0.25, "viewsFlagRatio": 0.02,
    # *Angka ilustrasi — kalibrasi setelah 8 minggu data
    "benchmarks": {
        "Regular Visit": {"Nano": {"cpv": 70, "er": 0.06, "cpo": 8000}, "Micro": {"cpv": 60, "er": 0.05, "cpo": 9000}, "Macro": {"cpv": 50, "er": 0.04, "cpo": 11000}, "Mega": {"cpv": 40, "er": 0.03, "cpo": 14000}},
        "Frozen": {"Nano": {"cpv": 70, "er": 0.06, "cpo": 30000, "roas": 2.5}, "Micro": {"cpv": 60, "er": 0.05, "cpo": 30000, "roas": 2.5}, "Macro": {"cpv": 50, "er": 0.04, "cpo": 40000, "roas": 2.0}, "Mega": {"cpv": 40, "er": 0.03, "cpo": 50000, "roas": 1.8}},
        "NPL": {"Nano": {"cpv": 70, "er": 0.06, "cpo": 70}, "Micro": {"cpv": 60, "er": 0.05, "cpo": 60}, "Macro": {"cpv": 50, "er": 0.04, "cpo": 50}, "Mega": {"cpv": 40, "er": 0.03, "cpo": 40}},
        "Info Lokasi": {"Nano": {"cpv": 70, "er": 0.06, "cpo": 4000}, "Micro": {"cpv": 60, "er": 0.05, "cpo": 4000}, "Macro": {"cpv": 50, "er": 0.04, "cpo": 5000}, "Mega": {"cpv": 40, "er": 0.03, "cpo": 6000}},
        "Keranjang Kuning": {"Nano": {"cpv": 70, "er": 0.06, "cpo": 25000, "roas": 3.0}, "Micro": {"cpv": 60, "er": 0.05, "cpo": 25000, "roas": 3.0}, "Macro": {"cpv": 50, "er": 0.04, "cpo": 30000, "roas": 2.5}, "Mega": {"cpv": 40, "er": 0.03, "cpo": 40000, "roas": 2.0}},
        "TikTok GO": {"Nano": {"cpv": 70, "er": 0.06, "cpo": 20000, "roas": 2.5}, "Micro": {"cpv": 60, "er": 0.05, "cpo": 20000, "roas": 2.5}, "Macro": {"cpv": 50, "er": 0.04, "cpo": 25000, "roas": 2.0}, "Mega": {"cpv": 40, "er": 0.03, "cpo": 30000, "roas": 1.8}},
    },
    "appName": "KOL Ledger",
    "adminEmail": "",
    "digestRecipients": "",
}


async def get_settings():
    s = await db.settings.find_one({"id": "settings"}, {"_id": 0})
    if not s:
        await db.settings.insert_one(dict(DEFAULT_SETTINGS))
        return dict(DEFAULT_SETTINGS)
    merged = {**DEFAULT_SETTINGS, **s}
    return merged


def tier_for(followers: int, thresholds: dict) -> str:
    f = followers or 0
    if f >= thresholds["Mega"]:
        return "Mega"
    if f >= thresholds["Macro"]:
        return "Macro"
    if f >= thresholds["Micro"]:
        return "Micro"
    return "Nano"


def kol_tier(kol: dict, settings: dict) -> str:
    if kol.get("tierOverride"):
        return kol["tierOverride"]
    fl = (kol.get("followers") or {}).get(kol.get("primaryPlatform") or "tiktok", 0)
    return tier_for(fl, settings["tierThresholds"])


def total_cost(costs: dict) -> int:
    c = costs or {}
    return int(sum(int(c.get(k) or 0) for k in ["feeRp", "productRp", "transportRp", "otherRp"]))


def detect_platform(url: str):
    u = (url or "").lower()
    handle = None
    m = re.search(r"tiktok\.com/@([\w.\-]+)", u)
    if m:
        handle = m.group(1)
    if "tiktok.com" in u:
        return "tiktok", handle
    if "instagram.com" in u:
        m = re.search(r"instagram\.com/(?!p/|reel/|reels/|stories/)([\w.\-]+)", u)
        if m:
            handle = m.group(1)
        m2 = re.search(r"instagram\.com/stories/([\w.\-]+)", u)
        if m2:
            handle = m2.group(1)
        return "instagram", handle
    if "youtube.com" in u or "youtu.be" in u:
        m = re.search(r"youtube\.com/@([\w.\-]+)", u)
        return "youtube", m.group(1) if m else None
    return "lainnya", None


def norm_handle(h):
    return (h or "").lower().lstrip("@").strip()


def latest_snap(snaps):
    best = None
    for s in snaps:
        if best is None or SNAP_DAYS.index(s["day"]) > SNAP_DAYS.index(best["day"]):
            best = s
    return best


def safe_div(a, b):
    return (a / b) if b else None


# ------------------------------------------------------------------ ASSISTED (uplift outlet)
async def compute_assisted(campaigns: dict, bookings: list, contents_by_booking: dict, views_by_content: dict):
    """Uplift outlet = revenue harian − baseline (rata-rata hari yang sama 4 minggu sebelumnya).
    Uplift harian dibagi ke konten yang window-nya mencakup hari itu, proporsional views.
    Return: {bookingId: {"revenue": x, "skuUnits": y, "days": n}}"""
    windows = defaultdict(list)  # outlet -> [(contentId, bookingId, start, end, sku)]
    for b in bookings:
        c = campaigns.get(b["campaignId"])
        if not c:
            continue
        cfg = CATEGORIES.get(c["category"], {})
        if not cfg.get("assisted"):
            continue
        outlets = (c.get("target") or {}).get("outlets") or []
        for ct in contents_by_booking.get(b["id"], []):
            d0 = parse_date(ct.get("postedAt"))
            if not d0:
                continue
            for o in outlets:
                windows[o].append((ct["id"], b["id"], d0, d0 + timedelta(days=cfg["windowDays"] - 1),
                                   (c.get("target") or {}).get("sku")))
    result = defaultdict(lambda: {"revenue": 0.0, "skuUnits": 0.0, "days": 0})
    if not windows:
        return result
    for outlet, wins in windows.items():
        start = min(w[2] for w in wins) - timedelta(days=28)
        end = max(w[3] for w in wins)
        rows = await db.outlet_sales.find({"outletCode": outlet, "date": {"$gte": start.isoformat(), "$lte": end.isoformat()}}, {"_id": 0}).to_list(None)
        by_date = {r["date"]: r for r in rows}
        days = set()
        for w in wins:
            d = w[2]
            while d <= w[3] and d <= today():
                days.add(d)
                d += timedelta(days=1)
        for d in days:
            r = by_date.get(d.isoformat())
            if not r:
                continue
            base = [by_date.get((d - timedelta(days=7 * k)).isoformat()) for k in range(1, 5)]
            base = [x for x in base if x]
            if not base:
                continue
            inc = r.get("revenueRp", 0) - sum(x.get("revenueRp", 0) for x in base) / len(base)
            covering = [w for w in wins if w[2] <= d <= w[3]]
            tot_views = sum(views_by_content.get(w[0], 0) or 0 for w in covering) or len(covering)
            for w in covering:
                share = (views_by_content.get(w[0], 0) or 1) / tot_views if tot_views else 1 / len(covering)
                result[w[1]]["revenue"] += inc * share
                result[w[1]]["days"] += 1
                if w[4]:
                    sku_today = (r.get("skuUnits") or {}).get(w[4], 0)
                    sku_base = sum((x.get("skuUnits") or {}).get(w[4], 0) for x in base) / len(base)
                    result[w[1]]["skuUnits"] += (sku_today - sku_base) * share
    return result


# ------------------------------------------------------------------ Metrik per booking
def booking_metrics(b, campaign, contents, snaps_by_content, settings, kol, assisted=None):
    cat = campaign["category"] if campaign else None
    cfg = CATEGORIES.get(cat, {})
    tier = b.get("tierAtBooking") or "Nano"
    agg = defaultdict(float)
    has_h7 = True
    missing_h7, missing_h3 = [], []
    for ct in contents:
        snaps = snaps_by_content.get(ct["id"], [])
        ls = latest_snap(snaps)
        if ls:
            for k, v in ls.items():
                if isinstance(v, (int, float)) and k in METRIC_LABELS:
                    if k == "audienceLocalPct":
                        continue
                    agg[k] += v
        ds = days_since(ct.get("postedAt"))
        days_have = {s["day"] for s in snaps}
        if ds is not None and ds >= settings["reportFinalDays"] and "H7" not in days_have:
            missing_h7.append(ct["id"])
        if ds is not None and ds >= settings["reportSubmitDays"] and not ({"H3", "H7", "H30"} & days_have):
            missing_h3.append(ct["id"])
        if "H7" not in days_have:
            has_h7 = False
    # audiens lokal = rata-rata
    locs = [latest_snap(snaps_by_content.get(ct["id"], [])) for ct in contents]
    locs = [s.get("audienceLocalPct") for s in locs if s and s.get("audienceLocalPct") is not None]
    cost = total_cost(b.get("costs")) + int(agg.get("commissionRp", 0)) + sum(int(ct.get("boostCostRp") or 0) for ct in contents)
    views = agg.get("views", 0)
    eng = sum(agg.get(k, 0) for k in ENG)
    outcome = agg.get(cfg.get("outcome"), 0) if cfg else 0
    rev_direct = 0.0
    if cfg.get("revenue") == "gmvRp":
        rev_direct = agg.get("gmvRp", 0)
    elif cfg.get("revenue") == "redemptions_x_aov":
        rev_direct = agg.get("redemptions", 0) * settings["aovRp"]
    a = assisted or {"revenue": 0, "skuUnits": 0, "days": 0}
    gm = settings["gmBlended"]
    bench = (settings["benchmarks"].get(cat) or {}).get(tier) or {}
    m = {
        "bookingId": b["id"], "category": cat, "tier": tier, "cost": cost, "views": views,
        "reach": agg.get("reach", 0), "engagement": eng, "er": safe_div(eng, views),
        "cpv": safe_div(cost, views), "cpm": safe_div(cost * 1000, agg.get("reach", 0)),
        "outcome": outcome, "outcomeLabel": cfg.get("outcomeLabel"),
        "costPerOutcome": safe_div(cost, outcome),
        "revenueDirect": rev_direct, "revenueAssisted": max(a["revenue"], 0) if cfg.get("assisted") else 0,
        "upliftRaw": a["revenue"], "skuUplift": a["skuUnits"], "assistedDays": a["days"],
        "roiDirect": safe_div(rev_direct * gm, cost),
        "roiTotal": safe_div((rev_direct + (max(a["revenue"], 0) if cfg.get("assisted") else 0)) * gm, cost),
        "roas": safe_div(rev_direct, cost) if cfg.get("revenue") == "gmvRp" else None,
        "orders": agg.get("orders", 0), "gmv": agg.get("gmvRp", 0), "linkClicks": agg.get("linkClicks", 0),
        "productClicks": agg.get("productClicks", 0), "mapsClicks": agg.get("mapsClicks", 0),
        "redemptions": agg.get("redemptions", 0), "vouchersSold": agg.get("vouchersSold", 0),
        "vouchersRedeemed": agg.get("vouchersRedeemed", 0),
        "audienceLocalPct": (sum(locs) / len(locs)) if locs else None,
        "contents": len(contents), "reportComplete": bool(contents) and has_h7,
        "missingH7": missing_h7, "missingH3": missing_h3, "benchmark": bench,
    }
    # flags
    flags = []
    st = b.get("status")
    if missing_h7 and st in ("POSTED", "REPORT_DUE"):
        flags.append({"code": "report_overdue", "label": "Report H+7 terlambat", "level": "red"})
    elif missing_h3 and st == "POSTED":
        flags.append({"code": "h3_missing", "label": "Snapshot H+3 belum diisi", "level": "amber"})
    if st in ("DEAL", "BRIEF_SENT", "DRAFT_REVIEW") and not contents:
        dues = [parse_date(d.get("dueDate")) for d in (b.get("deliverables") or []) if d.get("dueDate")]
        if dues and min(dues) < today():
            flags.append({"code": "deliverable_overdue", "label": "Deliverable lewat due date", "level": "red"})
    if views >= 500 and m["er"] is not None:
        if m["er"] < settings["erFlagLow"]:
            flags.append({"code": "er_low", "label": f"ER sangat rendah ({m['er']*100:.1f}%)", "level": "amber"})
        elif m["er"] > settings["erFlagHigh"]:
            flags.append({"code": "er_high", "label": f"ER tidak wajar ({m['er']*100:.1f}%)", "level": "amber"})
    if kol and contents and views:
        fl = (kol.get("followers") or {}).get(kol.get("primaryPlatform") or "tiktok", 0)
        if fl and views / len(contents) < settings["viewsFlagRatio"] * fl:
            flags.append({"code": "views_low", "label": "Views jauh di bawah follower (cek follower palsu)", "level": "amber"})
    if bench.get("cpo") and m["costPerOutcome"] and m["costPerOutcome"] > 2 * bench["cpo"] and m["reportComplete"]:
        flags.append({"code": "cpo_high", "label": "Cost per outcome > 2× benchmark", "level": "amber"})
    if cat in ("Frozen", "Keranjang Kuning", "TikTok GO") and m["reportComplete"] and outcome == 0:
        flags.append({"code": "no_outcome", "label": "Tidak ada outcome DIRECT", "level": "red"})
    if any(ct.get("status") in ("Dihapus", "Private") for ct in contents):
        flags.append({"code": "post_deleted", "label": "Post dihapus/private", "level": "red"})
    m["flags"] = flags
    return m


def recommend(metrics_list):
    """SCALE/KEEP/STOP dari histori booking yang report-nya lengkap."""
    done = [m for m in metrics_list if m["reportComplete"]]
    if not done:
        return None
    scores = []
    for m in done:
        b = m["benchmark"]
        if b.get("cpo") and m["costPerOutcome"]:
            scores.append(b["cpo"] / m["costPerOutcome"])
        elif b.get("cpv") and m["cpv"]:
            scores.append(b["cpv"] / m["cpv"])
        elif m["outcome"] == 0 and m["cost"] > 0:
            scores.append(0)
    if not scores:
        return None
    s = sum(scores) / len(scores)
    return "SCALE" if s >= 1.2 else ("STOP" if s < 0.5 else "KEEP")


# ------------------------------------------------------------------ Loader bersama
async def load_universe(campaign_query=None, booking_query=None):
    """Muat semua data (skala ratusan booking), hitung metrik global agar uplift outlet
    terbagi benar antar campaign, lalu saring sesuai query."""
    settings = await get_settings()
    campaigns = {c["id"]: c for c in await db.campaigns.find({}, {"_id": 0}).to_list(None)}
    bookings = await db.bookings.find({}, {"_id": 0}).to_list(None)
    bids = [b["id"] for b in bookings]
    contents = await db.contents.find({"bookingId": {"$in": bids}}, {"_id": 0}).to_list(None)
    cids = [c["id"] for c in contents]
    snaps = await db.snapshots.find({"contentId": {"$in": cids}}, {"_id": 0}).to_list(None)
    kols = {k["id"]: k for k in await db.kols.find({"id": {"$in": list({b["kolId"] for b in bookings})}}, {"_id": 0}).to_list(None)}
    cb = defaultdict(list)
    for c in contents:
        cb[c["bookingId"]].append(c)
    sbc = defaultdict(list)
    for s in snaps:
        sbc[s["contentId"]].append(s)
    views_by_content = {}
    for c in contents:
        ls = latest_snap(sbc.get(c["id"], []))
        views_by_content[c["id"]] = (ls or {}).get("views", 0) or 0
    # assisted perlu semua campaign yang menyentuh outlet yang sama -> cukup pakai universe yang dimuat
    assisted = await compute_assisted(campaigns, [b for b in bookings if b.get("status") != "CANCELLED"], cb, views_by_content)
    metrics = {}
    for b in bookings:
        metrics[b["id"]] = booking_metrics(b, campaigns.get(b["campaignId"]), cb.get(b["id"], []), sbc, settings, kols.get(b["kolId"]), assisted.get(b["id"]))
    if campaign_query is not None:
        keep = {c["id"] for c in await db.campaigns.find(campaign_query, {"id": 1}).to_list(None)}
        campaigns = {k: v for k, v in campaigns.items() if k in keep}
        bookings = [b for b in bookings if b["campaignId"] in keep]
    if booking_query:
        keep_b = {b["id"] for b in await db.bookings.find(booking_query, {"id": 1}).to_list(None)}
        bookings = [b for b in bookings if b["id"] in keep_b]
    return {"settings": settings, "campaigns": campaigns, "bookings": bookings, "contents_by_booking": cb,
            "snaps_by_content": sbc, "kols": kols, "metrics": metrics}


def committed_cost(b):
    """Biaya yang mengikat budget: total kontrak untuk DEAL s/d PAID; untuk booking batal hanya DP yang sudah keluar."""
    if b.get("status") in COMMITTED:
        return total_cost(b.get("costs"))
    if b.get("status") == "CANCELLED":
        return int((b.get("payment") or {}).get("dpRp") or 0)
    return 0


async def committed_for_campaign(campaign_id, exclude_booking=None):
    tot = 0
    async for b in db.bookings.find({"campaignId": campaign_id}, {"_id": 0}):
        if b["id"] != exclude_booking:
            tot += committed_cost(b)
    return tot


async def campaign_budgets_in_month(month, category, exclude_campaign=None):
    tot = 0
    async for c in db.campaigns.find({"month": month, "category": category}, {"_id": 0}):
        if c["id"] != exclude_campaign:
            tot += await campaign_allocation(c)
    return tot


async def campaign_allocation(c):
    """Plan yang dipakai campaign: budget penuh; bila HOLD, cukup biaya yang sudah terikat."""
    if c.get("gateStatus") == "HOLD":
        return await committed_for_campaign(c["id"])
    return int(c.get("budgetRp") or 0)


def aggregate(ms):
    """Agregasi metrik beberapa booking (tidak termasuk CANCELLED)."""
    cost = sum(m["cost"] for m in ms)
    views = sum(m["views"] for m in ms)
    reach = sum(m["reach"] for m in ms)
    eng = sum(m["engagement"] for m in ms)
    outcome = sum(m["outcome"] for m in ms)
    rd = sum(m["revenueDirect"] for m in ms)
    ra = sum(m["revenueAssisted"] for m in ms)
    gmv_cats = [m for m in ms if m["roas"] is not None or m["category"] in ("Frozen", "Keranjang Kuning", "TikTok GO")]
    gmv_cost = sum(m["cost"] for m in gmv_cats)
    return {
        "bookings": len(ms), "cost": cost, "views": views, "reach": reach, "engagement": eng,
        "er": safe_div(eng, views), "cpv": safe_div(cost, views), "cpm": safe_div(cost * 1000, reach),
        "outcome": outcome, "costPerOutcome": safe_div(cost, outcome),
        "revenueDirect": rd, "revenueAssisted": ra, "skuUplift": sum(m["skuUplift"] for m in ms),
        "orders": sum(m["orders"] for m in ms), "gmv": sum(m["gmv"] for m in ms),
        "redemptions": sum(m["redemptions"] for m in ms), "mapsClicks": sum(m["mapsClicks"] for m in ms),
        "vouchersRedeemed": sum(m["vouchersRedeemed"] for m in ms), "vouchersSold": sum(m["vouchersSold"] for m in ms),
        "contents": sum(m["contents"] for m in ms),
        "roas": safe_div(sum(m["revenueDirect"] for m in gmv_cats), gmv_cost),
        "reportComplete": sum(1 for m in ms if m["reportComplete"]),
        "flags": sum(len(m["flags"]) for m in ms),
    }


def with_roi(a, gm):
    a["roiDirect"] = safe_div(a["revenueDirect"] * gm, a["cost"])
    a["roiTotal"] = safe_div((a["revenueDirect"] + a["revenueAssisted"]) * gm, a["cost"])
    return a
