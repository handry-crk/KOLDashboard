import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from .reporting import rp, n, pct, times

RED = "B32E26"
HEAD = Font(bold=True, color="FFFFFF")
FILL = PatternFill("solid", fgColor=RED)
THIN = Border(bottom=Side(style="thin", color="EBD9DA"))


def sheet(wb, title, headers, rows, widths=None, note=None):
    ws = wb.create_sheet(title[:31])
    r0 = 1
    if note:
        ws.cell(1, 1, note).font = Font(italic=True, color="666666")
        r0 = 3
    for i, h in enumerate(headers, 1):
        c = ws.cell(r0, i, h)
        c.font, c.fill = HEAD, FILL
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for ri, row in enumerate(rows, r0 + 1):
        for ci, v in enumerate(row, 1):
            c = ws.cell(ri, ci, v)
            if isinstance(v, str) and v[:1] in ("=", "+", "-", "@"):
                c.value = v
                c.data_type = "s"  # cegah formula injection dari input user
            c.border = THIN
            if isinstance(v, float) and abs(v) < 50 and ci <= len(headers) and headers[ci - 1].lower().startswith(("er", "share", "compliance", "%")):
                c.number_format = "0.0%"
            elif isinstance(v, (int, float)):
                c.number_format = "#,##0" if abs(v) >= 50 else "0.00"
    for i, w in enumerate(widths or [], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(r0 + 1, 1)
    return ws


def r0(x):
    return None if x is None else round(float(x), 4)


def xlsx_direksi(d):
    wb = Workbook()
    wb.remove(wb.active)
    t = d["tiles"]
    sheet(wb, "Ringkasan", ["Metrik", "Nilai"], [
        ["Bulan", d["month"]], ["Pagu / plan KOL", t["pagu"]], ["Committed (DEAL+)", t["committed"]], ["Sudah dibayar (DP+lunas)", t["paid"]],
        ["Konten tayang", t["contents"]], ["Total views", t["views"]], ["Revenue DIRECT", r0(t["revenueDirect"])],
        ["Revenue ASSISTED (estimasi uplift outlet)", r0(t["revenueAssisted"])], ["ROI DIRECT (GM)", r0(t["roiDirect"])],
        ["ROI DIRECT+ASSISTED (GM)", r0(t["roiTotal"])], ["ROAS (Frozen+KK+TikTok GO)", r0(t["roas"])],
        ["Report compliance", r0(t["compliance"])], ["Booking tanpa report H+7", t["noReport"]], ["Nilai booking tanpa report", t["noReportCost"]],
    ], [40, 22], note=f"Laporan KOL {d['month']} — GM blended {d['gm']:.0%}. DIRECT dan ASSISTED tidak dijumlahkan dalam satu ROI.")
    sheet(wb, "Per Kategori", ["Kategori", "Objective", "Level bukti", "Plan", "Spend", "# KOL", "Views", "CPV", "Bench CPV", "ER",
                               "Outcome", "Label outcome", "Cost/outcome", "Bench cost/outcome", "Revenue DIRECT", "Revenue ASSISTED",
                               "ROI DIRECT", "ROI DIRECT+ASSISTED", "ROAS", "Status"],
          [[c["category"], c["objective"], " + ".join(c["evidence"]), c["planned"], c["spend"], c["kols"], c["views"], r0(c["cpv"]), r0(c["benchCpv"]),
            r0(c["er"]), c["outcome"], c["outcomeLabel"], r0(c["costPerOutcome"]), r0(c["benchCpo"]), r0(c["revenueDirect"]),
            r0(c["revenueAssisted"]), r0(c["roiDirect"]), r0(c["roiTotal"]), r0(c["roas"]), c["status"]] for c in d["categories"]],
          [18, 34, 18, 14, 14, 7, 12, 9, 9, 8, 10, 28, 12, 12, 15, 15, 10, 12, 8, 8])
    sheet(wb, "Per Tier", ["Tier", "Booking", "Spend", "Share spend", "Views", "CPV", "ER", "Revenue DIRECT", "Share revenue DIRECT", "Indeks efisiensi"],
          [[x["tier"], x["bookings"], x["spend"], r0(x["spendShare"]), x["views"], r0(x["cpv"]), r0(x["er"]), r0(x["revenueDirect"]),
            r0(x["revenueShare"]), r0(x["effIndex"])] for x in d["tiers"]], [10, 9, 14, 12, 12, 9, 8, 15, 15, 12])
    sheet(wb, "Top & Bottom KOL", ["Grup", "KOL", "Tier", "Kategori", "Campaign", "Biaya", "Outcome", "Label", "Cost/outcome", "Benchmark", "ROI DIRECT", "Indeks"],
          [["Top", r["kol"], r["tier"], r["category"], r["campaign"], r["cost"], r["outcome"], r["outcomeLabel"], r0(r["costPerOutcome"]), r["benchCpo"], r0(r["roiDirect"]), r0(r["index"])] for r in d["top"]] +
          [["Bottom", r["kol"], r["tier"], r["category"], r["campaign"], r["cost"], r["outcome"], r["outcomeLabel"], r0(r["costPerOutcome"]), r["benchCpo"], r0(r["roiDirect"]), r0(r["index"])] for r in d["bottom"]],
          [8, 22, 8, 16, 28, 12, 9, 26, 12, 10, 10, 8])
    sheet(wb, "Perlu Dicek", ["KOL", "Campaign", "Status", "Biaya", "Catatan"],
          [[f["kol"] or "-", f["campaign"], f["status"], f["cost"], "; ".join(x["label"] for x in f["flags"])] for f in d["flags"]], [22, 30, 18, 12, 60])
    ins = d["insights"]
    sheet(wb, "Insight", ["Insight"], [[x] for x in ins.get("summary", [])] + [[ins[k]] for k in ("weekly", "tier", "funnel") if ins.get(k)], [120])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def xlsx_simple(title, headers, rows, widths=None, note=None):
    wb = Workbook()
    wb.remove(wb.active)
    sheet(wb, title, headers, rows, widths, note)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def xlsx_weekly(w):
    wb = Workbook(); wb.remove(wb.active)
    a = w["agg"]
    sheet(wb, "Tab 8 KOL", ["Metrik", "Nilai"], [["Minggu", f"{w['week']} s/d {w['end']}"], ["Booking dengan post minggu ini", a["bookings"]],
          ["Biaya", a["cost"]], ["Views", a["views"]], ["CPV", r0(a["cpv"])], ["Revenue DIRECT", r0(a["revenueDirect"])],
          ["ROI DIRECT", r0(a["roiDirect"])], ["Report/deliverable terlambat", len(w["overdue"])]], [36, 24])
    sheet(wb, "Detail", ["KOL", "Tier", "Campaign", "Kategori", "Post", "Biaya", "Views", "Outcome", "Label", "Revenue DIRECT", "Status"],
          [[r["kol"], r["tier"], r["campaign"], r["category"], r["posts"], r["cost"], r["views"], r["outcome"], r["outcomeLabel"], r0(r["revenueDirect"]), r["status"]] for r in w["rows"]],
          [22, 8, 28, 16, 6, 12, 12, 9, 26, 14, 18])
    sheet(wb, "Terlambat", ["KOL", "Campaign", "Status", "Catatan", "Officer"], [[o["kol"], o["campaign"], o["status"], o["flag"], o["officer"]] for o in w["overdue"]], [22, 28, 16, 40, 16])
    sheet(wb, "Insight", ["Evidence", "Diagnosis", "Implikasi", "Owner", "Deadline"],
          [[i["evidence"], i["diagnosis"], i["implication"], i["owner"], i["deadline"]] for i in w["insights"]], [60, 12, 50, 14, 12])
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()


# ----------------------------------------------------------------- PDF Direksi
def pdf_direksi(d):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                            title=f"Laporan KOL {d['month']}")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], textColor=colors.HexColor("#B32E26"), fontSize=18, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=colors.HexColor("#1F1A1A"), fontSize=12, spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9, leading=12)
    small = ParagraphStyle("s", parent=body, fontSize=7.5, textColor=colors.HexColor("#666666"))
    cell = ParagraphStyle("c", parent=body, fontSize=7.5, leading=9)
    t = d["tiles"]
    el = [Paragraph(f"Laporan KOL Campaign — {d['month']}", h1),
          Paragraph("Cimol Bojot AA · CRK Group · Akuntabilitas budget KOL & dampak per objective", small), Spacer(1, 6)]
    tiles = [["Budget plan", "Committed", "Dibayar", "Konten", "Views", "Revenue DIRECT", "ROI DIRECT", "ROI +ASSISTED", "ROAS", "Compliance", "Tanpa report"],
             [rp(t["pagu"]), rp(t["committed"]), rp(t["paid"]), n(t["contents"]), n(t["views"]), rp(t["revenueDirect"]), times(t["roiDirect"]),
              times(t["roiTotal"]), times(t["roas"]), pct(t["compliance"], 0), f"{t['noReport']} ({rp(t['noReportCost'])})"]]
    tb = Table(tiles, hAlign="LEFT")
    tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7D4D5")), ("FONTSIZE", (0, 0), (-1, -1), 8),
                            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"), ("FONTSIZE", (0, 1), (-1, 1), 10),
                            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#EBD9DA")), ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#EBD9DA")),
                            ("TEXTCOLOR", (10, 1), (10, 1), colors.HexColor("#D7191F") if t["noReport"] else colors.black)]))
    el += [tb, Spacer(1, 6)]
    for s in d["insights"].get("summary", []):
        el.append(Paragraph("• " + s, body))
    el.append(Paragraph("ROI = revenue × GM blended ÷ biaya. DIRECT = terhitung dari kode/link/TikTok Shop/TikTok GO; ASSISTED = estimasi uplift penjualan outlet vs baseline 4 minggu; EXPOSURE = views/reach. Tidak dijumlahkan dalam satu angka.", small))

    # header cell paragraphs on red need white text
    cell_w = ParagraphStyle("cw", parent=cell, textColor=colors.white)

    def table2(headers, rows, widths):
        data = [[Paragraph(f"<b>{h}</b>", cell_w) for h in headers]] + [[Paragraph(str(v), cell) for v in r] for r in rows]
        tb = Table(data, colWidths=[w * mm for w in widths], repeatRows=1)
        tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#B32E26")),
                                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FBF1F1")]),
                                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#EBD9DA")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        return tb
    el.append(Paragraph("Per kategori (objective)", h2))
    st = {"green": "Sesuai", "amber": "Waspada", "red": "Di atas benchmark", "grey": "-"}
    el.append(table2(["Kategori", "Bukti", "Plan", "Spend", "Views", "CPV (bench)", "Outcome", "Cost/outcome (bench)", "Rev. DIRECT", "Rev. ASSISTED", "ROI DIRECT", "ROI +ASS.", "ROAS", "Status"],
                     [[c["category"], "+".join(c["evidence"]), rp(c["planned"]), rp(c["spend"]), n(c["views"]), f"{rp(c['cpv'])} ({rp(c['benchCpv'])})",
                       f"{n(c['outcome'])} {c['outcomeLabel'].split('(')[0].lower()}", f"{rp(c['costPerOutcome'])} ({rp(c['benchCpo'])})", rp(c["revenueDirect"]),
                       rp(c["revenueAssisted"]) if "ASSISTED" in c["evidence"] else "–", times(c["roiDirect"]), times(c["roiTotal"]), times(c["roas"]), st[c["status"]]]
                      for c in d["categories"]], [24, 22, 16, 16, 14, 24, 32, 28, 17, 17, 14, 14, 11, 20]))
    el.append(Paragraph("Per tier", h2))
    el.append(table2(["Tier", "Booking", "Spend", "Share spend", "Views", "CPV", "ER", "Rev. DIRECT", "Share rev. DIRECT", "Indeks efisiensi*"],
                     [[x["tier"], x["bookings"], rp(x["spend"]), pct(x["spendShare"], 0), n(x["views"]), rp(x["cpv"]), pct(x["er"]), rp(x["revenueDirect"]),
                       pct(x["revenueShare"], 0), times(x["effIndex"])] for x in d["tiers"]], [20, 16, 26, 22, 22, 20, 18, 26, 26, 26]))
    if d["insights"].get("tier"):
        el.append(Paragraph(d["insights"]["tier"], small))
    el.append(Paragraph("*Indeks efisiensi = benchmark cost per outcome ÷ aktual (≥ 1 = lebih efisien dari benchmark). Benchmark masih *angka ilustrasi sampai dikalibrasi.", small))
    el.append(PageBreak())
    el.append(Paragraph("Top 5 & Bottom 5 KOL (cost per outcome vs benchmark kategori & tier)", h2))
    rows = [["TOP", r["kol"], r["tier"], r["category"], rp(r["cost"]), f"{n(r['outcome'])}", rp(r["costPerOutcome"]), rp(r["benchCpo"]), times(r["roiDirect"]), times(r["index"])] for r in d["top"]]
    rows += [["BOTTOM", r["kol"], r["tier"], r["category"], rp(r["cost"]), f"{n(r['outcome'])}", rp(r["costPerOutcome"]), rp(r["benchCpo"]), times(r["roiDirect"]), times(r["index"])] for r in d["bottom"]]
    el.append(table2(["", "KOL", "Tier", "Kategori", "Biaya", "Outcome", "Cost/outcome", "Benchmark", "ROI DIRECT", "Indeks"], rows, [18, 40, 16, 30, 22, 18, 24, 22, 20, 16]))
    el.append(Paragraph("Perlu dicek", h2))
    el.append(table2(["KOL", "Campaign", "Status", "Biaya", "Catatan"],
                     [[f["kol"] or "-", f["campaign"], f["status"], rp(f["cost"]), "; ".join(x["label"] for x in f["flags"])] for f in d["flags"][:25]],
                     [40, 60, 30, 22, 110]))
    for k in ("weekly", "funnel"):
        if d["insights"].get(k):
            el.append(Spacer(1, 4)); el.append(Paragraph(d["insights"][k], body))
    doc.build(el)
    return buf.getvalue()
