"""Data contoh (fiktif) untuk uji coba. Hanya jalan bila database kosong."""
import asyncio
import os
import random
from datetime import timedelta
from PIL import Image, ImageDraw
from .auth import hash_pin
from .config import FILE_DIR, BOOTSTRAP_NAME, BOOTSTRAP_PIN
from .db import db, new_id, now_iso, today, ensure_indexes
from .logic import DEFAULT_SETTINGS, CATEGORIES, tier_for

R = random.Random(42)

KOL_NAMES = [
    ("Rara Jajan Bandung", "rarajajan.bdg", "Bandung", 6500), ("Kang Ujang Kuliner", "kangujang.makan", "Bandung", 8200),
    ("Teh Nia Ngemil", "tehnia.ngemil", "Bandung", 4800), ("Bima Food Trip", "bimafoodtrip", "Jakarta", 9100),
    ("Salsa Cobain Dulu", "salsacobaindulu", "Bandung", 18500), ("Doni Laper Terus", "donilaperterus", "Bandung", 42000),
    ("Mamah Gita Masak", "mamahgita.dapur", "Bekasi", 27000), ("Kuliner Depok Hits", "kulinerdepok.hits", "Depok", 64000),
    ("Arsy Review Jujur", "arsyreviewjujur", "Jakarta", 88000), ("Fikri Jajan Murah", "fikrijajanmurah", "Bogor", 23500),
    ("Mahasiswa Laper", "mahasiswalaper.id", "Bandung", 51000), ("Nadya Snack Time", "nadyasnacktime", "Tangerang", 15800),
    ("Bang Jaka Explore", "bangjaka.explore", "Jakarta", 33000), ("Putri Ngemil Mulu", "putringemilmulu", "Bandung", 71000),
    ("Raka Foodvlog", "rakafoodvlog", "Bandung", 145000), ("Jelajah Jajanan", "jelajahjajanan", "Jakarta", 310000),
    ("Mbak Sekar Kitchen", "sekarkitchen", "Bekasi", 520000), ("Kuliner Bandung Raya", "kulinerbandungraya", "Bandung", 780000),
    ("Dimas Makan Enak", "dimasmakanenak", "Jakarta", 230000), ("Tasya Eats", "tasyaeats", "Jakarta", 1450000),
    ("Om Kuliner Nusantara", "omkulinernusantara", "Jakarta", 2300000), ("Ghea Ngonten", "gheangonten", "Bandung", 12500),
    ("Ilham Cari Makan", "ilhamcarimakan", "Depok", 9800), ("Sinta Lapar Malam", "sintalaparmalam", "Bandung", 38000),
    ("Abi Frozen Hacks", "abifrozenhacks", "Bogor", 47000), ("Lulu Belanja Hemat", "lulubelanjahemat", "Jakarta", 96000),
    ("Reza Unboxing Food", "rezaunboxing", "Tangerang", 85000), ("Citra Mom Snack", "citramomsnack", "Bekasi", 61000),
    ("Viral Followers Food", "viralfollowersfood", "Jakarta", 95000), ("Bocil Jajan", "bociljajan", "Bandung", 7300),
]
NICHES = ["Kuliner", "Lifestyle", "Mom", "Mahasiswa", "Komedi", "Review jujur", "Lokal Bandung", "Lokal Jabodetabek"]
OUTLETS = [("BDG-BRG-01", "Gerobak AA – Braga", "Bandung", 4_200_000), ("BDG-DGO-02", "Gerobak AA – Dago", "Bandung", 3_600_000),
           ("BDG-BKR-03", "Gerobak AA – Buah Batu", "Bandung", 3_100_000), ("JKT-TBT-01", "Gerobak AA – Tebet", "Jakarta", 3_800_000),
           ("DPK-MRG-01", "Gerobak AA – Margonda", "Depok", 2_400_000), ("BKS-GLX-01", "Gerobak AA – Galaxy", "Bekasi", 2_700_000)]
VIEW_RATE = {"Nano": (0.8, 2.5), "Micro": (0.3, 1.0), "Macro": (0.1, 0.4), "Mega": (0.05, 0.2)}
FEE = {"Nano": (300_000, 800_000), "Micro": (1_000_000, 3_000_000), "Macro": (5_000_000, 8_000_000), "Mega": (16_000_000, 22_000_000)}


def proof_image():
    name = "contoh-insight-screenshot.jpg"
    p = os.path.join(FILE_DIR, name)
    if not os.path.exists(p):
        img = Image.new("RGB", (540, 960), (250, 245, 245))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 540, 90], fill=(215, 25, 31))
        d.text((24, 34), "CONTOH - Screenshot insight", fill=(255, 255, 255))
        for i, t in enumerate(["Views", "Likes", "Komentar", "Share", "Save", "Klik"]):
            d.text((40, 140 + i * 90), t, fill=(60, 60, 60))
            d.rectangle([200, 140 + i * 90, 200 + R.randint(120, 300), 160 + i * 90], fill=(215, 25, 31))
        img.save(p, "JPEG", quality=80)
    return name


def fee(t):
    lo, hi = FEE[t]
    return int(R.randint(lo, hi) // 50_000 * 50_000)


def outcome_values(cat, views):
    likes = int(views * R.uniform(0.03, 0.08)); comments = int(views * R.uniform(0.002, 0.008))
    shares = int(views * R.uniform(0.002, 0.01)); saves = int(views * R.uniform(0.003, 0.015))
    v = {"views": views, "likes": likes, "comments": comments, "shares": shares, "saves": saves}
    if cat == "Regular Visit":
        v["mapsClicks"] = int(views * R.uniform(0.003, 0.01)); v["redemptions"] = int(views * R.uniform(0.003, 0.012))
    elif cat == "Frozen":
        v["linkClicks"] = int(views * R.uniform(0.01, 0.03)); v["orders"] = int(v["linkClicks"] * R.uniform(0.08, 0.2)); v["gmvRp"] = v["orders"] * R.choice([59_000, 65_000, 89_000])
    elif cat == "NPL":
        v["reach"] = int(views * R.uniform(0.7, 0.9))
    elif cat == "Info Lokasi":
        v["reach"] = int(views * R.uniform(0.7, 0.9)); v["audienceLocalPct"] = round(R.uniform(30, 78), 1); v["mapsClicks"] = int(views * R.uniform(0.004, 0.012))
    elif cat == "Keranjang Kuning":
        v["productClicks"] = int(views * R.uniform(0.015, 0.04)); v["orders"] = int(v["productClicks"] * R.uniform(0.06, 0.15))
        v["gmvRp"] = v["orders"] * 55_000; v["commissionRp"] = int(v["gmvRp"] * 0.1)
    elif cat == "TikTok GO":
        v["vouchersSold"] = int(views * R.uniform(0.003, 0.01)); v["vouchersRedeemed"] = int(v["vouchersSold"] * R.uniform(0.55, 0.85)); v["gmvRp"] = v["vouchersSold"] * 25_000
    return v


def scale(v, f):
    return {k: (x if k == "audienceLocalPct" else int(x * f)) for k, x in v.items()}


async def seed(force=False):
    await ensure_indexes()
    if not force and (await db.kols.count_documents({}) or await db.bookings.count_documents({})):
        return {"seeded": False, "reason": "Database sudah berisi data"}
    T = today()
    proof = proof_image()
    await db.settings.update_one({"id": "settings"}, {"$set": {k: v for k, v in DEFAULT_SETTINGS.items()}}, upsert=True)
    # users
    users = [("Agoy", "KOL TL"), ("Rina", "KOL Officer"), ("Dimas", "KOL Officer"), ("Sari (Finance)", "Finance"), ("Direksi CRK", "Direksi")]
    uids = {}
    for name, role in users:
        if not await db.users.find_one({"name": name}):
            uid = new_id()
            await db.users.insert_one({"id": uid, "name": name, "role": role, "active": True, "pinHash": hash_pin("1234"), "createdAt": now_iso(), "email": ""})
            uids[name] = uid
        else:
            uids[name] = (await db.users.find_one({"name": name}))["id"]
    mgr = await db.users.find_one({"role": "Manager"})
    officers = [("Rina", uids["Rina"]), ("Dimas", uids["Dimas"])]
    for code, name, area, _ in OUTLETS:
        await db.outlets.update_one({"code": code}, {"$set": {"code": code, "name": name, "area": area}}, upsert=True)
    # KOL
    kols = []
    for i, (name, h, city, fl) in enumerate(KOL_NAMES):
        ig = int(fl * R.uniform(0.3, 1.1))
        k = {"id": new_id(), "name": name, "handles": {"tiktok": h, "instagram": h.replace(".", "_")}, "primaryPlatform": "tiktok",
             "followers": {"tiktok": fl, "instagram": ig}, "city": city, "audienceCityTop3": [city, "Jakarta" if city != "Jakarta" else "Bandung", "Bekasi"],
             "niche": R.sample(NICHES, 2), "contactWa": f"0812{R.randint(10000000, 99999999)}", "agency": "" if fl < 100000 else "Talent Agency (contoh)",
             "rateCard": {"Video TikTok": fee(tier_for(fl, DEFAULT_SETTINGS["tierThresholds"])), "Story": 0}, "avgViews30D": None, "avgER30D": None,
             "bankAccount": f"BCA {R.randint(1000000000, 9999999999)}", "npwp": "", "status": "Aktif", "blacklistReason": "",
             "picOfficerId": officers[i % 2][1], "notes": "", "tierOverride": None, "tierOverrideReason": "", "recommendationOverride": None,
             "createdAt": now_iso(), "createdBy": "seed"}
        if h == "bociljajan":
            k["status"] = "Blacklist"; k["blacklistReason"] = "Konten dihapus H+2 pada campaign Oktober, tidak bisa dihubungi"
        kols.append(k)
    await db.kols.insert_many([dict(k) for k in kols])
    by_h = {k["handles"]["tiktok"]: k for k in kols}

    def tier(k):
        return tier_for(k["followers"]["tiktok"], DEFAULT_SETTINGS["tierThresholds"])
    # budget
    cur = T.strftime("%Y-%m")
    prev_d = T.replace(day=1) - timedelta(days=1)
    prev = prev_d.strftime("%Y-%m")
    plans = {"Regular Visit": 25, "Frozen": 15, "NPL": 30, "Info Lokasi": 15, "Keranjang Kuning": 20, "TikTok GO": 15}
    for m in (prev, cur):
        for cat, jt in plans.items():
            await db.budget.update_one({"month": m, "category": cat}, {"$set": {"month": m, "category": cat, "plannedRp": jt * 1_000_000, "notes": "", "updatedBy": "seed", "updatedAt": now_iso()}}, upsert=True)
    first = T.replace(day=1)
    last = (first + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    pfirst = prev_d.replace(day=1)

    def camp(name, cat, month, start, end, budget, gate, target, kpi, review=None):
        c = {"id": new_id(), "name": name, "category": cat, "objective": CATEGORIES[cat]["objective"], "month": month,
             "start": start.isoformat(), "end": end.isoformat(), "target": target, "budgetRp": budget, "kpiTargets": kpi,
             "gateStatus": gate, "gateNote": "", "linkedInitiativeCode": "", "promoCodePrefix": CATEGORIES[cat]["code"],
             "code": f"KOL-{month[2:4]}{month[5:7]}-{CATEGORIES[cat]['code']}-{name.upper().replace(' ', '-')[:14]}",
             "createdAt": now_iso(), "ownerId": uids["Agoy"], "ownerName": "Agoy", "review": None}
        if review:
            c.update(review)
        return c
    C = [
        camp("Regular Visit Braga Okt", "Regular Visit", prev, pfirst, prev_d, 18_000_000, "SELESAI", {"outlets": ["BDG-BRG-01", "BDG-DGO-02"]},
             {"views": 250_000, "cpv": 30, "outcome": 600, "costPerOutcome": 25_000},
             {"review": "KEEP", "reviewNote": "Redemption kode bagus di Braga, Dago lemah karena kode jarang disebut crew.", "whatWorked": "Nano lokal Bandung, posting jam makan siang",
              "whatDidnt": "Crew Dago tidak menanyakan kode", "nextAction": "Briefing crew Dago + tent card kode KOL", "reviewedBy": "Agoy", "reviewedAt": now_iso()}),
        camp("Frozen Payday Okt", "Frozen", prev, pfirst, prev_d, 15_000_000, "SELESAI", {"store": "Tokopedia & Shopee CBAA Frozen"},
             {"views": 200_000, "outcome": 500, "roas": 2.5},
             {"review": "SCALE", "reviewNote": "ROAS di atas target, micro mom-niche paling efisien.", "whatWorked": "Voucher toko unik per KOL", "whatDidnt": "Macro lifestyle CTR rendah",
              "nextAction": "Tambah 3 micro mom-niche di November", "reviewedBy": "Agoy", "reviewedAt": now_iso()}),
        camp("Regular Visit Bandung Nov", "Regular Visit", cur, first, last, 22_000_000, "GO", {"outlets": ["BDG-BRG-01", "BDG-BKR-03"]},
             {"views": 300_000, "cpv": 25, "outcome": 800, "costPerOutcome": 22_000}),
        camp("Frozen Gajian Nov", "Frozen", cur, first, last, 14_000_000, "GO", {"store": "Tokopedia & Shopee CBAA Frozen"},
             {"views": 250_000, "outcome": 600, "roas": 2.5, "revenueDirect": 35_000_000}),
        camp("Launch Mozza Duo", "NPL", cur, first, last, 30_000_000, "GO", {"outlets": ["BDG-BRG-01", "BDG-DGO-02", "JKT-TBT-01"], "sku": "MOZZA"},
             {"views": 1_500_000, "cpv": 18}),
        camp("Info Lokasi Margonda", "Info Lokasi", cur, first, last, 14_000_000, "GO", {"outlets": ["DPK-MRG-01"], "area": "Depok"},
             {"views": 400_000, "cpv": 22, "outcome": 2500}),
        camp("TikTok Shop 11.11", "Keranjang Kuning", cur, first, last, 20_000_000, "GO", {"store": "TikTok Shop CBAA Frozen"},
             {"views": 900_000, "outcome": 900, "roas": 3, "revenueDirect": 50_000_000}),
        camp("Voucher TikTok GO Jabodetabek", "TikTok GO", cur, first, last, 15_000_000, "PENDING", {"outlets": ["JKT-TBT-01", "BKS-GLX-01"]},
             {"views": 500_000, "outcome": 1500, "roas": 2.5}),
    ]
    await db.campaigns.insert_many([dict(c) for c in C])
    # rencana booking: (campaign idx, handle, status, posted days ago or None)
    plan = [
        (0, "rarajajan.bdg", "PAID", 25), (0, "kangujang.makan", "PAID", 22), (0, "salsacobaindulu", "PAID", 20), (0, "donilaperterus", "PAID", 18), (0, "bociljajan", "CANCELLED", None),
        (1, "mamahgita.dapur", "PAID", 28), (1, "abifrozenhacks", "PAID", 24), (1, "citramomsnack", "PAID", 21), (1, "nadyasnacktime", "PAID", 19),
        (2, "tehnia.ngemil", "REPORT_APPROVED", 10), (2, "mahasiswalaper.id", "PAID", 12), (2, "putringemilmulu", "REPORT_DUE", 9),
        (2, "gheangonten", "POSTED", 5), (2, "sintalaparmalam", "DRAFT_REVIEW", None), (2, "rarajajan.bdg", "POSTED", 2),
        (3, "mamahgita.dapur", "REPORT_SUBMITTED", 8), (3, "lulubelanjahemat", "POSTED", 4), (3, "citramomsnack", "BRIEF_SENT", None), (3, "abifrozenhacks", "REPORT_APPROVED", 9),
        (4, "rakafoodvlog", "REPORT_APPROVED", 9), (4, "kulinerbandungraya", "POSTED", 6), (4, "donilaperterus", "PAID", 10),
        (4, "arsyreviewjujur", "REPORT_DUE", 8), (4, "bimafoodtrip", "POSTED", 3), (4, "tasyaeats", "WAITING_APPROVAL", None),
        (5, "kulinerdepok.hits", "REPORT_APPROVED", 9), (5, "ilhamcarimakan", "POSTED", 5), (5, "fikrijajanmurah", "DEAL", None),
        (5, "viralfollowersfood", "REPORT_SUBMITTED", 8),
        (6, "lulubelanjahemat", "REPORT_APPROVED", 9), (6, "nadyasnacktime", "POSTED", 4), (6, "rezaunboxing", "POSTED", 1),
        (6, "sekarkitchen", "REPORT_DUE", 8), (6, "bangjaka.explore", "NEGO", None), (6, "omkulinernusantara", "SHORTLIST", None),
        (7, "dimasmakanenak", "POSTED", 3), (7, "bangjaka.explore", "DEAL", None), (7, "fikrijajanmurah", "POSTED", 2), (7, "salsacobaindulu", "SHORTLIST", None),
    ]
    order = ["SHORTLIST", "NEGO", "WAITING_APPROVAL", "DEAL", "BRIEF_SENT", "DRAFT_REVIEW", "POSTED", "REPORT_DUE", "REPORT_SUBMITTED", "REPORT_APPROVED", "PAID"]
    outlet_uplift = {}  # (outlet, date) -> rp
    for ci, h, status, posted in plan:
        c = C[ci]; k = by_h[h]; t = tier(k); cat = c["category"]
        off_name, off_id = officers[(ci + len(h)) % 2]
        costs = {"feeRp": fee(t), "productRp": R.choice([0, 100_000, 150_000]), "transportRp": 150_000 if cat in ("Regular Visit", "Info Lokasi") else 0, "otherRp": 0}
        if cat == "Keranjang Kuning":
            costs["commissionPct"] = 10
        hist = []
        idx_to = order.index(status) if status in order else 0
        for st in order[: idx_to + 1]:
            hist.append({"from": None, "to": st, "by": off_name, "at": now_iso(), "reason": ""})
        due = (T - timedelta(days=posted + 1) if posted is not None else T + timedelta(days=R.randint(-2, 6))).isoformat()
        if h == "sintalaparmalam":
            due = (T - timedelta(days=2)).isoformat()
        b = {"id": new_id(), "campaignId": c["id"], "kolId": k["id"], "platform": "tiktok", "tierAtBooking": t,
             "deliverables": [{"format": "Video TikTok", "qty": 1, "dueDate": due}], "costs": costs, "trackingLink": "",
             "uniqueCode": f"{CATEGORIES[cat]['code']}-{h.upper().replace('.', '')[:12]}", "contentRights": {"repostDays": 30, "adsUsage": t in ("Micro", "Nano")},
             "notes": "", "status": status, "statusAt": now_iso(), "createdAt": now_iso(), "createdBy": off_name, "createdById": off_id,
             "approvals": [], "history": hist, "payment": {"dpRp": 0, "paidRp": 0}, "dealAt": now_iso() if status in order[3:] else None}
        if status == "CANCELLED":
            b["history"].append({"from": "DEAL", "to": "CANCELLED", "by": "Agoy", "at": now_iso(), "reason": "KOL tidak bisa dihubungi setelah DEAL"})
        if t in ("Macro", "Mega") and status in order[3:]:
            b["approvals"].append({"by": mgr["name"], "role": "Manager", "at": now_iso(), "note": "OK sesuai plan", "decision": "approve"})
        if status in order[3:] and costs["feeRp"] >= 5_000_000:
            b["payment"]["dpRp"] = costs["feeRp"] // 2; b["payment"]["dpPaidAt"] = now_iso()
        if status == "PAID":
            b["payment"]["paidRp"] = sum(v for kk, v in costs.items() if kk.endswith("Rp")) - b["payment"]["dpRp"]; b["payment"]["paidAt"] = now_iso(); b["payment"]["proof"] = [proof]
        if status in ("REPORT_APPROVED", "PAID"):
            b["reportApprovedBy"] = "Agoy"; b["reportApprovedAt"] = now_iso()
        await db.bookings.insert_one(b)
        if posted is None:
            continue
        posted_at = T - timedelta(days=posted)
        ct = {"id": new_id(), "bookingId": b["id"], "url": f"https://www.tiktok.com/@{h}/video/7{R.randint(10**17, 10**18 - 1)}",
              "postedAt": posted_at.isoformat(), "format": "Video", "captionSnippet": "", "isCollab": False, "adsBoosted": False,
              "boostCostRp": 0, "proofFiles": [proof], "handleMismatchReason": "", "status": "Live", "platform": "tiktok",
              "detectedHandle": h, "createdAt": now_iso(), "createdBy": off_name}
        await db.contents.insert_one(ct)
        fl = k["followers"]["tiktok"]
        lo, hi = VIEW_RATE[t]
        views = int(fl * R.uniform(lo, hi))
        if h == "viralfollowersfood":
            views = int(fl * 0.012)  # pola follower palsu
        final = outcome_values(cat, views)
        if h == "sekarkitchen":
            final.update({"orders": 0, "gmvRp": 0, "commissionRp": 0, "productClicks": int(views * 0.002)})
        days = [d for d, off in (("H1", 1), ("H3", 3), ("H7", 7), ("H30", 30)) if posted >= off]
        if status in ("REPORT_DUE",):
            days = [d for d in days if d in ("H1", "H3")]
        if h == "putringemilmulu":
            days = ["H1"]
        for d in days:
            f = {"H1": 0.45, "H3": 0.8, "H7": 1.0, "H30": 1.1}[d]
            vals = scale(final, f)
            await db.snapshots.insert_one({"id": new_id(), "contentId": ct["id"], "day": d, **vals, "proofFiles": [proof],
                                           "enteredBy": off_name, "enteredAt": (posted_at + timedelta(days={"H1": 1, "H3": 3, "H7": 7, "H30": 30}[d])).isoformat(),
                                           "updatedAt": now_iso()})
        if CATEGORIES[cat]["assisted"]:
            for o in c["target"].get("outlets", []):
                base = dict((x[0], x[3]) for x in OUTLETS)[o]
                for dd in range(CATEGORIES[cat]["windowDays"]):
                    day = posted_at + timedelta(days=dd)
                    up = min(views * R.uniform(2, 6) / len(c["target"]["outlets"]), base * 0.18) * (1 - dd / 10)
                    outlet_uplift[(o, day.isoformat())] = outlet_uplift.get((o, day.isoformat()), 0) + up
    # outlet sales 75 hari terakhir
    start = T - timedelta(days=75)
    docs = []
    for code, _, _, base in OUTLETS:
        d = start
        while d < T:
            if code == "DPK-MRG-01" and d < T - timedelta(days=55):
                d += timedelta(days=1); continue
            wk = 1.25 if d.weekday() >= 5 else (1.1 if d.weekday() == 4 else 1.0)
            rev = base * wk * R.uniform(0.9, 1.1) + outlet_uplift.get((code, d.isoformat()), 0)
            mozza = 0
            if d >= first and code in ("BDG-BRG-01", "BDG-DGO-02", "JKT-TBT-01"):
                mozza = int(R.uniform(15, 30) + outlet_uplift.get((code, d.isoformat()), 0) / 20000)
            docs.append({"date": d.isoformat(), "outletCode": code, "revenueRp": int(rev), "transactions": int(rev / 15000),
                         "skuUnits": {"MOZZA": mozza} if mozza else {}, "importedAt": now_iso()})
            d += timedelta(days=1)
    await db.outlet_sales.insert_many(docs)
    return {"seeded": True, "kols": len(kols), "campaigns": len(C), "bookings": len(plan)}


async def bootstrap():
    await ensure_indexes()
    if not await db.users.find_one({"role": "Manager"}):
        await db.users.insert_one({"id": new_id(), "name": BOOTSTRAP_NAME, "role": "Manager", "active": True,
                                   "pinHash": hash_pin(BOOTSTRAP_PIN), "createdAt": now_iso(), "email": ""})
    if not await db.settings.find_one({"id": "settings"}):
        await db.settings.insert_one(dict(DEFAULT_SETTINGS))


if __name__ == "__main__":
    async def main():
        await bootstrap()
        print(await seed())
    asyncio.run(main())
