from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import Response
from ..auth import current_user
from ..config import PUBLIC_METRICS_API_KEY
from ..db import db, today, week_monday, month_of
from .. import reporting as R
from ..exports import xlsx_direksi, pdf_direksi, xlsx_weekly, xlsx_simple, r0

router = APIRouter(prefix="/api")
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def file_resp(data, name, mime):
    return Response(content=data, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/reports/direksi")
async def direksi(month: str | None = None, format: str = "json", user=Depends(current_user)):
    month = month or month_of(today())
    d = await R.direksi(month)
    if format == "xlsx":
        return file_resp(xlsx_direksi(d), f"KOL_Laporan_Direksi_{month}.xlsx", XLSX)
    if format == "pdf":
        return file_resp(pdf_direksi(d), f"KOL_Laporan_Direksi_{month}.pdf", "application/pdf")
    return d


@router.get("/reports/campaign/{cid}")
async def campaign(cid: str, format: str = "json", user=Depends(current_user)):
    d = await R.campaign_report(cid)
    if not d:
        raise HTTPException(404, "Campaign tidak ditemukan")
    if format == "xlsx":
        c = d["campaign"]
        rows = [[p["metric"], r0(p["target"]), r0(p["actual"]), r0(p["achievement"])] for p in d["pva"]]
        rows += [[], ["KOL", "Tier", "Status", "Biaya", "Views", "ER", "CPV", "Outcome", "Cost/outcome", "Rev DIRECT", "Rev ASSISTED", "ROI DIRECT", "Kode", "Flag"]]
        rows += [[r["kol"], r["tier"], r["status"], r["cost"], r["views"], r0(r["er"]), r0(r["cpv"]), r["outcome"], r0(r["costPerOutcome"]),
                  r0(r["revenueDirect"]), r0(r["revenueAssisted"]), r0(r["roiDirect"]), r["code"], "; ".join(r["flags"])] for r in d["rows"]]
        rows += [[], ["Review", c.get("review") or "-"], ["Catatan", c.get("reviewNote") or "-"], ["What worked", c.get("whatWorked") or "-"],
                 ["What didn't", c.get("whatDidnt") or "-"], ["Next action", c.get("nextAction") or "-"]]
        return file_resp(xlsx_simple("Report Campaign", ["Metric", "Target", "Actual", "Achievement"], rows, [30, 14, 14, 14, 12, 8, 10, 10, 12, 14, 14, 10, 16, 40],
                                     note=f"{c['code']} · {c['name']} · {c['category']} · {c['start']} s/d {c['end']}"), f"KOL_Report_{c['code']}.xlsx", XLSX)
    return d


@router.get("/reports/weekly")
async def weekly(week: str | None = None, format: str = "json", user=Depends(current_user)):
    week = week or (week_monday(today()) - timedelta(days=7)).isoformat()
    d = await R.weekly(week)
    if format == "xlsx":
        return file_resp(xlsx_weekly(d), f"KOL_Tab8_{d['week']}.xlsx", XLSX)
    return d


@router.get("/reports/review")
async def review(month: str, format: str = "json", user=Depends(current_user)):
    d = await R.review(month)
    if format == "xlsx":
        rows = [[r["category"], r["planned"], r["spend"], r0(r["cpv"]), r0(r["benchCpv"]), r["outcome"], r0(r["costPerOutcome"]), r0(r["benchCpo"]),
                 r0(r["revenueDirect"]), r0(r["revenueAssisted"]), r0(r["roiDirect"]), r0(r["index"]), r["suggestion"] or "-"] for r in d["rows"]]
        return file_resp(xlsx_simple("Review M+1", ["Kategori", "Plan", "Actual spend", "CPV", "Bench CPV", "Outcome", "Cost/outcome", "Bench", "Rev DIRECT",
                                                    "Rev ASSISTED", "ROI DIRECT", "Indeks", "Saran"], rows, [18, 14, 14, 9, 9, 10, 12, 10, 14, 14, 10, 8, 10],
                                     note=f"Review M+1 KOL {month} — saran otomatis, keputusan akhir SCALE/KEEP/STOP oleh KOL TL & Manager"), f"KOL_Review_{month}.xlsx", XLSX)
    return d


@router.get("/tasks")
async def tasks(user=Depends(current_user)):
    return await R.tasks(user)


# ----------------------------------------------------------------- Integrasi
def check_key(key):
    if not PUBLIC_METRICS_API_KEY or key != PUBLIC_METRICS_API_KEY:
        raise HTTPException(401, "API key tidak valid")


@router.get("/public-metrics/kol")
async def pm_kol(week: str | None = None, x_api_key: str = Header(default="")):
    check_key(x_api_key)
    w = await R.weekly(week or today().isoformat())
    a = w["agg"]
    return {"week": w["week"], "bookings": a["bookings"], "cost": a["cost"], "views": a["views"], "cpv": a["cpv"],
            "revenueDirect": a["revenueDirect"], "roiDirect": a["roiDirect"], "overdueReports": len(w["overdue"])}


@router.get("/public-metrics/kol-codes")
async def pm_codes(x_api_key: str = Header(default="")):
    check_key(x_api_key)
    out = []
    async for b in db.bookings.find({"status": {"$in": ["DEAL", "BRIEF_SENT", "DRAFT_REVIEW", "POSTED", "REPORT_DUE"]}}, {"_id": 0}):
        c = await db.campaigns.find_one({"id": b["campaignId"]}, {"_id": 0, "start": 1, "end": 1, "category": 1, "target": 1})
        out.append({"code": b.get("uniqueCode"), "category": c.get("category"), "start": c.get("start"), "end": c.get("end"),
                    "outlets": (c.get("target") or {}).get("outlets", [])})
    return out
