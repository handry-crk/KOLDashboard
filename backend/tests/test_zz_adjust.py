"""Penyesuaian 23 Nov: kategori Media, indikator KOL, PIC, produk teks, platform mirroring, IG Carousel."""
import os
from datetime import date
import httpx

B = os.getenv("BASE", "http://localhost:8001")
c = httpx.Client(base_url=B, timeout=60)


def L(n, p="1234"):
    u = [x for x in c.get("/api/auth/users").json() if x["name"] == n][0]
    return {"Authorization": "Bearer " + c.post("/api/auth/login", json={"userId": u["id"], "pin": p}).json()["token"]}


def test_adjustments():
    M = L("Marketing Manager", "123456"); TL = L("Agoy"); OF = L("Rina")
    meta = c.get("/api/meta", headers=OF).json()
    assert "Media" in meta["categories"] and meta["categories"]["Media"]["evidence"] == ["EXPOSURE"]
    pics = c.get("/api/users/pic", headers=OF).json()
    rina = next(u for u in pics if u["name"] == "Rina"); dimas = next(u for u in pics if u["name"] == "Dimas")
    # KOL baru: PIC default pembuat; indikator dari avg views insight
    k = c.post("/api/kols", json={"name": "Info Bandung Uji", "handles": {"instagram": "infobdg.uji"}, "primaryPlatform": "instagram",
                                 "followers": {"instagram": 200_000}, "rateCard": {"Video TikTok": 0, "Reels": 3_000_000}}, headers=OF).json()
    d = c.get(f"/api/kols/{k['id']}", headers=OF).json()
    assert d["picName"] == "Rina" and d["indicator"]["status"] == "nodata"
    body = {k2: d.get(k2) for k2 in ("name", "handles", "primaryPlatform", "followers", "rateCard", "city", "niche")}
    body.update({"avgViews30D": 80_000, "picOfficerId": dimas["id"]})
    assert c.put(f"/api/kols/{k['id']}", json=body, headers=OF).status_code == 200
    d = c.get(f"/api/kols/{k['id']}", headers=OF).json()
    # 80rb/200rb = 40% follower; CPM = 3jt/80rb*1000 = 37.500 <= 50.000 (Macro) -> approved
    assert d["indicator"]["status"] == "approved", d["indicator"]
    assert round(d["indicator"]["estCpm"]) == 37500 and d["indicator"]["rateName"] == "Reels" and d["picName"] == "Dimas"
    body["avgViews30D"] = 2_000  # 1% follower, CPM 1,5jt -> tidak approved
    c.put(f"/api/kols/{k['id']}", json=body, headers=OF)
    assert c.get(f"/api/kols/{k['id']}", headers=OF).json()["indicator"]["status"] == "rejected"
    body["picOfficerId"] = "tidakada"
    assert c.put(f"/api/kols/{k['id']}", json=body, headers=OF).status_code == 400
    # kategori Media: plan -> campaign -> booking mirroring + produk teks + PIC
    m = date.today().strftime("%Y-%m")
    assert c.put("/api/budget", json={"month": m, "category": "Media", "plannedRp": 0}, headers=M).status_code in (200, 400)
    st = c.get("/api/settings", headers=M).json()
    r = c.put("/api/budget", json={"month": m, "category": "Media", "plannedRp": 5_000_000}, headers=M)
    if r.status_code == 400:  # pagu penuh -> naikkan pagu dulu
        c.put("/api/settings", json={"monthlyKolPagu": st["monthlyKolPagu"] + 5_000_000}, headers=M)
        assert c.put("/api/budget", json={"month": m, "category": "Media", "plannedRp": 5_000_000}, headers=M).status_code == 200
    camp = c.post("/api/campaigns", json={"name": "Media Uji", "category": "Media", "month": m, "start": f"{m}-01", "end": f"{m}-28", "budgetRp": 5_000_000}, headers=TL)
    assert camp.status_code == 200, camp.text
    camp = camp.json()
    b = c.post("/api/bookings", json={"campaignId": camp["id"], "kolId": k["id"], "platform": "mirroring", "costs": {"feeRp": 3_000_000},
                                      "productItems": "2 pack Cimol Frozen Original, 1 Mozza Duo",
                                      "deliverables": [{"format": "IG Carousel", "qty": 1, "dueDate": m + "-20"}]}, headers=OF)
    assert b.status_code == 200, b.text
    b = b.json()
    assert b["uniqueCode"].startswith("MD-INFOBDG") and b["picId"] == dimas["id"]  # ikut PIC KOL
    det = c.get(f"/api/bookings/{b['id']}", headers=OF).json()
    assert det["productItems"].startswith("2 pack") and det["picName"] == "Dimas" and det["lockInfo"]["listedBy"] == "Rina"
    assert c.post("/api/bookings", json={"campaignId": camp["id"], "kolId": k["id"], "platform": "fax"}, headers=OF).status_code in (400, 409)
    # lock (DEAL) tercatat
    for to in ("NEGO", "WAITING_APPROVAL"):
        c.post(f"/api/bookings/{b['id']}/transition", json={"to": to}, headers=OF)
    assert c.post(f"/api/bookings/{b['id']}/approve", json={"to": "approve", "reason": "ok"}, headers=M).status_code == 200
    det = c.get(f"/api/bookings/{b['id']}", headers=OF).json()
    assert det["status"] == "DEAL" and det["lockInfo"]["lockedBy"] == "Marketing Manager"
    # tugas officer berdasarkan PIC
    rep = c.get(f"/api/reports/direksi?month={m}", headers=M).json()
    assert any(x["category"] == "Media" for x in rep["categories"])
    assert c.put("/api/settings", json={"kolApproval": {"minViewsPctFollowers": 5, "maxCpm": {}}}, headers=M).status_code == 400
