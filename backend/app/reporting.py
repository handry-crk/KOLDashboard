"""Penyusunan angka laporan (dipakai API, export Excel/PDF, digest)."""
from collections import defaultdict
from datetime import timedelta
from .db import db, parse_date, today, week_monday, days_since
from .logic import (CATEGORIES, TIERS, COMMITTED, load_universe, aggregate, with_roi, safe_div, total_cost, latest_snap, committed_cost)
from .services import refresh_statuses

DIRECT_CATS = [c for c, v in CATEGORIES.items() if "DIRECT" in v["evidence"]]


def rp(x):
    if x is None:
        return "–"
    x = float(x)
    if abs(x) >= 1e9:
        return f"Rp{x/1e9:,.1f} M".replace(",", "X").replace(".", ",").replace("X", ".")
    if abs(x) >= 1e6:
        return f"Rp{x/1e6:,.1f} jt".replace(",", "X").replace(".", ",").replace("X", ".")
    return "Rp" + f"{int(round(x)):,}".replace(",", ".")


def n(x):
    if x is None:
        return "–"
    x = float(x)
    if abs(x) >= 1e6:
        return f"{x/1e6:,.1f} jt".replace(",", "X").replace(".", ",").replace("X", ".")
    if abs(x) >= 1e3:
        return f"{x/1e3:,.0f} rb".replace(",", ".")
    return f"{int(round(x))}"


def pct(x, d=1):
    return "-" if x is None else f"{x*100:.{d}f}%".replace(".", ",")


def times(x):
    return "-" if x is None else f"{x:.1f}×".replace(".", ",")


def first_post(contents):
    ds = [parse_date(c.get("postedAt")) for c in contents if c.get("postedAt")]
    return min(ds) if ds else None


def bench_weighted(ms, key):
    w = [(m["benchmark"].get(key), m["cost"]) for m in ms if m["benchmark"].get(key)]
    tot = sum(c for _, c in w)
    if not w:
        return None
    if not tot:
        return sum(b for b, _ in w) / len(w)
    return sum(b * c for b, c in w) / tot


def eff_index(m):
    b = m["benchmark"]
    if b.get("cpo") and m["costPerOutcome"]:
        return b["cpo"] / m["costPerOutcome"]
    if m["outcome"] == 0 and m["cost"] and m["reportComplete"]:
        return 0.0
    if b.get("cpv") and m["cpv"]:
        return b["cpv"] / m["cpv"]
    return None


def status_color(actual_cpo, bench_cpo):
    if actual_cpo is None or not bench_cpo:
        return "grey"
    r = actual_cpo / bench_cpo
    return "green" if r <= 1 else ("amber" if r <= 1.5 else "red")


async def direksi(month: str):
    await refresh_statuses()
    u = await load_universe(campaign_query={"month": month})
    s = u["settings"]
    gm = s["gmBlended"]
    plans = {p["category"]: p["plannedRp"] for p in await db.budget.find({"month": month}, {"_id": 0}).to_list(None)}
    live = [b for b in u["bookings"] if b["status"] != "CANCELLED"]
    committed = [b for b in live if b["status"] in COMMITTED]
    ms_all = [u["metrics"][b["id"]] for b in committed]
    agg = with_roi(aggregate(ms_all), gm)
    paid = sum(int((b.get("payment") or {}).get("paidRp") or 0) + int((b.get("payment") or {}).get("dpRp") or 0) for b in u["bookings"])
    # compliance
    due = []
    for b in committed:
        fp = first_post(u["contents_by_booking"].get(b["id"], []))
        if fp and (today() - fp).days >= s["reportFinalDays"]:
            due.append(b)
    approved = [b for b in due if b["status"] in ("REPORT_APPROVED", "PAID")]
    no_report = [b for b in committed if any(f["code"] == "report_overdue" for f in u["metrics"][b["id"]]["flags"])]
    tiles = {
        "pagu": sum(plans.values()) or s["monthlyKolPagu"], "committed": sum(committed_cost(b) for b in u["bookings"]), "paid": paid,
        "actualCost": agg["cost"],
        "contents": agg["contents"], "views": agg["views"], "revenueDirect": agg["revenueDirect"],
        "revenueAssisted": agg["revenueAssisted"], "roiDirect": agg["roiDirect"], "roiTotal": agg["roiTotal"],
        "roas": agg["roas"], "compliance": safe_div(len(approved), len(due)), "dueCount": len(due),
        "approvedCount": len(approved), "noReport": len(no_report),
        "noReportCost": sum(total_cost(b.get("costs")) for b in no_report),
    }
    # per kategori
    cat_rows = []
    for cat, cfg in CATEGORIES.items():
        ms = [u["metrics"][b["id"]] for b in committed if u["campaigns"][b["campaignId"]]["category"] == cat]
        a = with_roi(aggregate(ms), gm)
        bcpv = bench_weighted(ms, "cpv")
        bcpo = bench_weighted(ms, "cpo")
        cat_rows.append({
            "category": cat, "objective": cfg["objective"], "evidence": cfg["evidence"], "outcomeLabel": cfg["outcomeLabel"],
            "planned": plans.get(cat, 0), "spend": a["cost"], "kols": len({b["kolId"] for b in committed if u["campaigns"][b["campaignId"]]["category"] == cat}),
            "views": a["views"], "cpv": a["cpv"], "benchCpv": bcpv, "er": a["er"], "outcome": a["outcome"],
            "costPerOutcome": a["costPerOutcome"], "benchCpo": bcpo, "revenueDirect": a["revenueDirect"],
            "revenueAssisted": a["revenueAssisted"], "skuUplift": a["skuUplift"], "roiDirect": a["roiDirect"], "roiTotal": a["roiTotal"],
            "roas": a["roas"] if cat in ("Frozen", "Keranjang Kuning", "TikTok GO") else None,
            "status": status_color(a["costPerOutcome"], bcpo) if a["outcome"] else status_color(a["cpv"], bcpv),
            "reportComplete": a["reportComplete"], "bookings": a["bookings"],
        })
    # per tier
    tier_rows = []
    for t in TIERS:
        ms = [m for m in ms_all if m["tier"] == t]
        a = aggregate(ms)
        idx = [eff_index(m) for m in ms if m["reportComplete"]]
        idx = [i for i in idx if i is not None]
        tier_rows.append({"tier": t, "bookings": len(ms), "spend": a["cost"], "spendShare": safe_div(a["cost"], agg["cost"]),
                          "views": a["views"], "cpv": a["cpv"], "er": a["er"], "revenueDirect": a["revenueDirect"],
                          "revenueShare": safe_div(a["revenueDirect"], agg["revenueDirect"]),
                          "effIndex": (sum(idx) / len(idx)) if idx else None})
    # top/bottom
    ranked = []
    for b in committed:
        m = u["metrics"][b["id"]]
        if not m["reportComplete"]:
            continue
        i = eff_index(m)
        if i is None:
            continue
        k = u["kols"].get(b["kolId"], {})
        ranked.append({"bookingId": b["id"], "kol": k.get("name"), "kolId": k.get("id"), "tier": m["tier"], "category": m["category"],
                       "campaign": u["campaigns"][b["campaignId"]]["name"], "cost": m["cost"], "outcome": m["outcome"],
                       "outcomeLabel": m["outcomeLabel"], "costPerOutcome": m["costPerOutcome"], "benchCpo": m["benchmark"].get("cpo"),
                       "cpv": m["cpv"], "roiDirect": m["roiDirect"], "index": i})
    ranked.sort(key=lambda r: r["index"], reverse=True)
    top = ranked[:5]
    bottom = [r for r in reversed(ranked[-5:]) if r not in top] if len(ranked) > 5 else []
    # mingguan
    weeks = defaultdict(lambda: {"spend": 0, "revenueDirect": 0, "revenueAssisted": 0, "views": 0})
    for b in committed:
        fp = first_post(u["contents_by_booking"].get(b["id"], []))
        if not fp:
            continue
        wk = week_monday(fp).isoformat()
        m = u["metrics"][b["id"]]
        weeks[wk]["spend"] += m["cost"]
        weeks[wk]["revenueDirect"] += m["revenueDirect"]
        weeks[wk]["revenueAssisted"] += m["revenueAssisted"]
        weeks[wk]["views"] += m["views"]
    weekly = [{"week": k, "label": f"{parse_date(k).day:02d}/{parse_date(k).month:02d}", **v} for k, v in sorted(weeks.items())]
    # funnel
    funnel = []
    for cat in CATEGORIES:
        ms = [u["metrics"][b["id"]] for b in committed if u["campaigns"][b["campaignId"]]["category"] == cat]
        if not ms:
            continue
        a = aggregate(ms)
        click = sum(m["linkClicks"] + m["productClicks"] + m["mapsClicks"] + m["vouchersSold"] for m in ms)
        funnel.append({"category": cat, "views": a["views"], "clicks": click, "outcome": a["outcome"],
                       "outcomeLabel": CATEGORIES[cat]["outcomeLabel"], "revenueDirect": a["revenueDirect"]})
    # flags
    flags = []
    for b in live:
        m = u["metrics"][b["id"]]
        if m["flags"]:
            k = u["kols"].get(b["kolId"], {})
            flags.append({"bookingId": b["id"], "kol": k.get("name"), "campaign": u["campaigns"][b["campaignId"]]["name"],
                          "status": b["status"], "flags": m["flags"], "cost": m["cost"]})
    for r in cat_rows:
        if r["planned"] and r["spend"] > 0.9 * r["planned"]:
            flags.append({"bookingId": None, "kol": None, "campaign": f"Budget {r['category']}", "status": "",
                          "flags": [{"code": "budget_90", "label": f"Committed {pct(r['spend']/r['planned'],0)} dari plan", "level": "amber"}], "cost": r["spend"]})
    for c in u["campaigns"].values():
        if int(c.get("budgetRp") or 0) >= s["approvalThresholdRp"] and c.get("gateStatus") not in ("GO", "GWC", "SELESAI"):
            if any(b["campaignId"] == c["id"] and b["status"] in COMMITTED for b in live):
                flags.append({"bookingId": None, "kol": None, "campaign": c["name"], "status": c.get("gateStatus"),
                              "flags": [{"code": "no_gate", "label": "Booking DEAL tanpa Gate GO/GWC", "level": "red"}], "cost": c["budgetRp"]})
    flags.sort(key=lambda f: (0 if any(x["level"] == "red" for x in f["flags"]) else 1, -f["cost"]))
    insights = make_insights(tiles, cat_rows, tier_rows, weekly, funnel)
    return {"month": month, "tiles": tiles, "categories": cat_rows, "tiers": tier_rows, "top": top, "bottom": bottom,
            "weekly": weekly, "funnel": funnel, "flags": flags, "insights": insights, "gm": gm}


def make_insights(t, cats, tiers, weekly, funnel):
    ins = {}
    d = [c for c in cats if c["category"] in DIRECT_CATS and c["spend"] > 0 and c["roiDirect"] is not None]
    lines = []
    if d:
        best = max(d, key=lambda c: c["roiDirect"])
        worst = min(d, key=lambda c: c["roiDirect"])
        lines.append(f"ROI DIRECT tertinggi di {best['category']} ({times(best['roiDirect'])} GM per Rp1 biaya)"
                     + (f"; terendah {worst['category']} ({times(worst['roiDirect'])})." if worst is not best else "."))
    if t["noReport"]:
        lines.append(f"{t['noReport']} booking senilai {rp(t['noReportCost'])} belum punya report H+7 — belum boleh dilunasi.")
    if t["compliance"] is not None:
        lines.append(f"Report compliance {pct(t['compliance'],0)} ({t['approvedCount']} dari {t['dueCount']} booking yang sudah lewat H+7).")
    ins["summary"] = lines
    if weekly:
        tot_s = sum(w["spend"] for w in weekly); tot_r = sum(w["revenueDirect"] for w in weekly)
        bw = max(weekly, key=lambda w: w["revenueDirect"])
        ins["weekly"] = f"Total biaya {rp(tot_s)} menghasilkan revenue DIRECT {rp(tot_r)}; minggu terkuat mulai {bw['label']} ({rp(bw['revenueDirect'])})."
    tv = [x for x in tiers if x["cpv"]]
    if tv:
        lo = min(tv, key=lambda x: x["cpv"])
        big = [x for x in tiers if x["tier"] in ("Macro", "Mega")]
        bs = sum(x["spend"] for x in big); br = sum(x["revenueDirect"] for x in big)
        s = f"{lo['tier']} memberi CPV terendah ({rp(lo['cpv'])})"
        if bs and t["committed"]:
            s += f"; Macro+Mega menyerap {pct(bs/t['committed'],0)} budget dengan {pct(safe_div(br, t['revenueDirect']) or 0,0)} revenue DIRECT"
        ins["tier"] = s + "."
    if funnel:
        f = [x for x in funnel if x["views"] and CATEGORIES[x["category"]]["outcome"] != "views"]
        if f:
            best = max(f, key=lambda x: (x["outcome"] / x["views"]) if x["views"] else 0)
            ins["funnel"] = f"Konversi views → outcome terbaik di {best['category']} ({n(best['outcome'])} {best['outcomeLabel'].lower()} dari {n(best['views'])} views)."
    return ins


async def campaign_report(cid: str):
    u = await load_universe(campaign_query={"id": cid})
    c = u["campaigns"].get(cid)
    if not c:
        return None
    gm = u["settings"]["gmBlended"]
    rows = []
    for b in u["bookings"]:
        if b["status"] == "CANCELLED":
            continue
        m = u["metrics"][b["id"]]
        k = u["kols"].get(b["kolId"], {})
        rows.append({"kol": k.get("name"), "tier": m["tier"], "status": b["status"], "cost": m["cost"], "views": m["views"],
                     "er": m["er"], "cpv": m["cpv"], "outcome": m["outcome"], "costPerOutcome": m["costPerOutcome"],
                     "revenueDirect": m["revenueDirect"], "revenueAssisted": m["revenueAssisted"], "roiDirect": m["roiDirect"],
                     "flags": [f["label"] for f in m["flags"]], "code": b.get("uniqueCode")})
    ms = [u["metrics"][b["id"]] for b in u["bookings"] if b["status"] in COMMITTED]
    a = with_roi(aggregate(ms), gm)
    t = c.get("kpiTargets") or {}
    cfg = CATEGORIES[c["category"]]

    def ach(actual, target, lower_better=False):
        if not target or actual is None:
            return None
        return (target / actual) if lower_better and actual else (actual / target if not lower_better else None)
    pva = [
        {"metric": "Biaya", "target": c.get("budgetRp"), "actual": a["cost"], "fmt": "rp", "achievement": safe_div(a["cost"], c.get("budgetRp"))},
        {"metric": "Views", "target": t.get("views"), "actual": a["views"], "fmt": "n", "achievement": ach(a["views"], t.get("views"))},
        {"metric": "CPV", "target": t.get("cpv"), "actual": a["cpv"], "fmt": "rp", "achievement": ach(a["cpv"], t.get("cpv"), True)},
        {"metric": cfg["outcomeLabel"], "target": t.get("outcome"), "actual": a["outcome"], "fmt": "n", "achievement": ach(a["outcome"], t.get("outcome"))},
        {"metric": "Cost per outcome", "target": t.get("costPerOutcome"), "actual": a["costPerOutcome"], "fmt": "rp", "achievement": ach(a["costPerOutcome"], t.get("costPerOutcome"), True)},
        {"metric": "Revenue DIRECT", "target": t.get("revenueDirect"), "actual": a["revenueDirect"], "fmt": "rp", "achievement": ach(a["revenueDirect"], t.get("revenueDirect"))},
    ]
    if cfg["assisted"]:
        pva.append({"metric": "Revenue ASSISTED (uplift outlet)", "target": None, "actual": a["revenueAssisted"], "fmt": "rp", "achievement": None})
    if c["category"] in ("Frozen", "Keranjang Kuning", "TikTok GO"):
        pva.append({"metric": "ROAS", "target": t.get("roas"), "actual": a["roas"], "fmt": "x", "achievement": ach(a["roas"], t.get("roas"))})
    pva.append({"metric": "ROI DIRECT (GM)", "target": None, "actual": a["roiDirect"], "fmt": "x", "achievement": None})
    return {"campaign": c, "config": cfg, "agg": a, "rows": rows, "pva": pva}


async def weekly(week: str):
    await refresh_statuses()
    mon = week_monday(parse_date(week))
    sun = mon + timedelta(days=6)
    u = await load_universe()
    s = u["settings"]
    rows, ms = [], []
    for b in u["bookings"]:
        if b["status"] == "CANCELLED":
            continue
        all_cts = u["contents_by_booking"].get(b["id"], [])
        fp = first_post(all_cts)
        if not fp or not (mon <= fp <= sun):
            continue  # booking dihitung sekali, di minggu konten pertamanya tayang
        cts = [c for c in all_cts if mon <= parse_date(c["postedAt"]) <= sun]
        m = u["metrics"][b["id"]]
        ms.append(m)
        k = u["kols"].get(b["kolId"], {})
        c = u["campaigns"][b["campaignId"]]
        rows.append({"kol": k.get("name"), "tier": m["tier"], "campaign": c["name"], "category": c["category"], "posts": len(cts),
                     "cost": m["cost"], "views": m["views"], "outcome": m["outcome"], "outcomeLabel": m["outcomeLabel"],
                     "revenueDirect": m["revenueDirect"], "status": b["status"]})
    a = with_roi(aggregate(ms), s["gmBlended"])
    overdue = []
    for b in u["bookings"]:
        m = u["metrics"][b["id"]]
        if any(f["code"] in ("report_overdue", "deliverable_overdue") for f in m["flags"]):
            k = u["kols"].get(b["kolId"], {})
            overdue.append({"kol": k.get("name"), "campaign": u["campaigns"][b["campaignId"]]["name"], "status": b["status"],
                            "flag": ", ".join(f["label"] for f in m["flags"] if f["level"] == "red"), "officer": b.get("createdBy")})
    insights = []
    anchor = max(sun, today())
    if rows:
        by_cat = defaultdict(list)
        for r in rows:
            by_cat[r["category"]].append(r)
        top = max(rows, key=lambda r: r["revenueDirect"])
        if top["revenueDirect"]:
            insights.append({"evidence": f"{top['kol']} ({top['category']}) menghasilkan revenue DIRECT {rp(top['revenueDirect'])} dari biaya {rp(top['cost'])}.",
                             "diagnosis": "Demand", "implication": "Pertimbangkan repeat booking / naikkan deliverable.", "owner": "KOL TL", "deadline": (anchor + timedelta(days=7)).isoformat()})
        low = [r for r in rows if r["category"] in DIRECT_CATS and r["outcome"] == 0 and r["cost"] > 0]
        if low:
            insights.append({"evidence": f"{len(low)} KOL kategori DIRECT belum menghasilkan outcome ({', '.join(r['kol'] for r in low[:3])}).",
                             "diagnosis": "Data" if any(r['status'] == 'POSTED' for r in low) else "Demand",
                             "implication": "Cek kode/link terpasang & lengkapi snapshot sebelum menilai.", "owner": "KOL Officer", "deadline": (anchor + timedelta(days=3)).isoformat()})
    if overdue:
        insights.append({"evidence": f"{len(overdue)} booking terlambat report/deliverable.", "diagnosis": "Struktural",
                         "implication": "Tahan pelunasan sampai report H+7 lengkap; follow up KOL hari ini.", "owner": "KOL TL", "deadline": (anchor + timedelta(days=2)).isoformat()})
    return {"week": mon.isoformat(), "end": sun.isoformat(), "agg": a, "rows": rows, "overdue": overdue, "insights": insights[:3]}


async def review(month: str):
    d = await direksi(month)
    rows = []
    for c in d["categories"]:
        if not c["spend"] and not c["planned"]:
            continue
        idx = None
        if c["benchCpo"] and c["costPerOutcome"]:
            idx = c["benchCpo"] / c["costPerOutcome"]
        elif c["benchCpv"] and c["cpv"]:
            idx = c["benchCpv"] / c["cpv"]
        dec = None if idx is None else ("SCALE" if idx >= 1.2 else ("STOP" if idx < 0.5 else "KEEP"))
        rows.append({**c, "index": idx, "suggestion": dec})
    camps = await db.campaigns.find({"month": month}, {"_id": 0}).to_list(None)
    return {"month": month, "rows": rows, "tiles": d["tiles"], "insights": d["insights"],
            "campaigns": [{"name": c["name"], "category": c["category"], "gateStatus": c.get("gateStatus"), "review": c.get("review"),
                           "reviewNote": c.get("reviewNote")} for c in camps]}


async def tasks(user):
    await refresh_statuses()
    u = await load_universe()
    s = u["settings"]
    role = user["role"]
    out = {"snapshots": [], "deliverables": [], "approvals": [], "reports": [], "payments": [], "registrations": []}
    if role == "Manager":
        out["registrations"] = await db.users.find({"status": "pending"}, {"_id": 0, "pinHash": 0}).sort("registeredAt", 1).to_list(None)
    for b in u["bookings"]:
        if b["status"] in ("CANCELLED", "PAID"):
            continue
        mine = role != "KOL Officer" or b.get("createdById") == user["id"]
        k = u["kols"].get(b["kolId"], {})
        c = u["campaigns"][b["campaignId"]]
        base = {"bookingId": b["id"], "kol": k.get("name"), "campaign": c["name"], "category": c["category"]}
        if mine and role in ("KOL Officer", "KOL TL", "Manager"):
            for ct in u["contents_by_booking"].get(b["id"], []):
                have = {x["day"] for x in u["snaps_by_content"].get(ct["id"], [])}
                ds = days_since(ct["postedAt"])
                due = [(d, off) for d, off in (("H1", 1), ("H3", 3), ("H7", 7)) if ds >= off]
                if due:
                    day, off = due[-1]
                    later = {"H1": {"H1", "H3", "H7", "H30"}, "H3": {"H3", "H7", "H30"}, "H7": {"H7", "H30"}}[day]
                    if not (have & later):
                        out["snapshots"].append({**base, "contentId": ct["id"], "url": ct["url"], "day": day,
                                                 "late": ds > off + (0 if day != "H1" else 1), "dueDate": (parse_date(ct["postedAt"]) + timedelta(days=off)).isoformat()})
            if b["status"] in ("DEAL", "BRIEF_SENT", "DRAFT_REVIEW") and not u["contents_by_booking"].get(b["id"]):
                for d in b.get("deliverables") or []:
                    dd = parse_date(d.get("dueDate"))
                    if dd and dd <= today() + timedelta(days=2):
                        out["deliverables"].append({**base, "format": d.get("format"), "dueDate": dd.isoformat(), "late": dd < today()})
        if role == "Manager" and b["status"] == "WAITING_APPROVAL":
            out["approvals"].append({**base, "cost": total_cost(b.get("costs")), "tier": b.get("tierAtBooking")})
        if role in ("KOL TL", "Manager") and b["status"] == "REPORT_SUBMITTED":
            out["reports"].append(base)
        if role in ("Finance", "Manager") and b["status"] == "REPORT_APPROVED":
            out["payments"].append({**base, "cost": total_cost(b.get("costs"))})
    out["snapshots"].sort(key=lambda x: x["dueDate"])
    return out
