"""Acceptance test KOL Ledger. Jalankan server dulu dengan DB kosong:
DB_NAME=kol_test ENABLE_JOBS=0 PUBLIC_METRICS_API_KEY=testkey uvicorn app.main:app --port 8001
lalu: BASE=http://localhost:8001 pytest -q tests/"""
import os
import io
import httpx
import pytest
from datetime import date, timedelta

BASE = os.getenv("BASE", "http://localhost:8001")
c = httpx.Client(base_url=BASE, timeout=60)
T = {}


def login(name, pin):
    users = c.get("/api/auth/users").json()
    u = next(x for x in users if x["name"] == name)
    r = c.post("/api/auth/login", json={"userId": u["id"], "pin": pin})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def H(role):
    return T[role]


def test_00_seed_and_login():
    T["mgr"] = login("Marketing Manager", os.getenv("BOOTSTRAP_PIN", "123456"))
    r = c.post("/api/admin/seed", headers=H("mgr"))
    assert r.status_code == 200, r.text
    assert c.post("/api/admin/seed", headers=H("mgr")).status_code == 400  # hanya DB kosong
    T["tl"] = login("Agoy", "1234")
    T["off"] = login("Rina", "1234")
    T["fin"] = login("Sari (Finance)", "1234")
    T["dir"] = login("Direksi CRK", "1234")


def test_01_wrong_pin_lock():
    users = c.get("/api/auth/users").json()
    u = next(x for x in users if x["name"] == "Dimas")
    for i in range(5):
        r = c.post("/api/auth/login", json={"userId": u["id"], "pin": "0000"})
    assert r.status_code == 401 and "dikunci" in r.json()["detail"]
    assert c.post("/api/auth/login", json={"userId": u["id"], "pin": "1234"}).status_code == 423


def test_02_campaign_budget_guard():
    month = (date.today().replace(day=1) + timedelta(days=40)).strftime("%Y-%m")
    body = {"name": "NPL Uji", "category": "NPL", "month": month, "start": f"{month}-01", "end": f"{month}-28", "budgetRp": 20_000_000}
    r = c.post("/api/campaigns", json=body, headers=H("mgr"))
    assert r.status_code == 400 and "Belum ada budget plan" in r.json()["detail"]
    assert c.put("/api/budget", json={"month": month, "category": "NPL", "plannedRp": 15_000_000}, headers=H("mgr")).status_code == 200
    r = c.post("/api/campaigns", json=body, headers=H("mgr"))
    assert r.status_code == 400 and "Melebihi sisa budget NPL bulan ini (sisa Rp15.000.000)" in r.json()["detail"], r.text
    # pagu bulanan
    r = c.put("/api/budget", json={"month": month, "category": "Frozen", "plannedRp": 200_000_000}, headers=H("mgr"))
    assert r.status_code == 400 and "pagu" in r.json()["detail"]
    # officer tidak boleh set budget
    assert c.put("/api/budget", json={"month": month, "category": "Frozen", "plannedRp": 1}, headers=H("off")).status_code == 403
    body["budgetRp"] = 30_000_000
    c.put("/api/budget", json={"month": month, "category": "NPL", "plannedRp": 40_000_000}, headers=H("mgr"))
    r = c.post("/api/campaigns", json=body, headers=H("tl"))
    assert r.status_code == 200, r.text
    T["camp"] = r.json()
    T["month"] = month


def test_03_tier_and_approval():
    kol = c.post("/api/kols", json={"name": "Uji Macro", "handles": {"tiktok": "ujimacro"}, "followers": {"tiktok": 450_000}}, headers=H("off")).json()
    assert kol.get("id"), kol
    full = c.get(f"/api/kols/{kol['id']}", headers=H("off")).json()
    assert full["tier"] == "Macro"
    dup = c.post("/api/kols", json={"name": "Duplikat", "handles": {"tiktok": "@UjiMacro"}}, headers=H("off"))
    assert dup.status_code == 409
    T["kol"] = kol
    b = c.post("/api/bookings", json={"campaignId": T["camp"]["id"], "kolId": kol["id"], "costs": {"feeRp": 8_000_000},
                                      "deliverables": [{"format": "Video TikTok", "qty": 1, "dueDate": date.today().isoformat()}]}, headers=H("off"))
    assert b.status_code == 200, b.text
    b = b.json()
    assert b["tierAtBooking"] == "Macro"
    T["booking"] = b
    # campaign 30 jt ≥ threshold 25 jt dan gate PENDING → blok
    r = c.post(f"/api/bookings/{b['id']}/transition", json={"to": "DEAL"}, headers=H("off"))
    assert r.status_code == 400 and "Activity Gate" in r.json()["detail"], r.text
    camp = T["camp"]
    upd = {k: camp[k] for k in ("name", "category", "objective", "month", "start", "end", "target", "budgetRp", "kpiTargets", "gateNote", "linkedInitiativeCode", "promoCodePrefix")}
    upd["gateStatus"] = "GO"
    assert c.put(f"/api/campaigns/{camp['id']}", json=upd, headers=H("tl")).status_code == 403  # gate hanya Manager
    assert c.put(f"/api/campaigns/{camp['id']}", json=upd, headers=H("mgr")).status_code == 200
    r = c.post(f"/api/bookings/{b['id']}/transition", json={"to": "DEAL"}, headers=H("off"))
    assert r.status_code == 400 and "approval Manager" in r.json()["detail"], r.text
    assert c.post(f"/api/bookings/{b['id']}/transition", json={"to": "WAITING_APPROVAL"}, headers=H("off")).status_code == 200
    assert c.post(f"/api/bookings/{b['id']}/approve", json={"to": "approve", "reason": "ok"}, headers=H("tl")).status_code == 403
    assert c.post(f"/api/bookings/{b['id']}/approve", json={"to": "approve", "reason": "ok"}, headers=H("mgr")).status_code == 200
    assert c.get(f"/api/bookings/{b['id']}", headers=H("off")).json()["status"] == "DEAL"


def test_04_booking_over_budget():
    k2 = c.post("/api/kols", json={"name": "Uji Mahal", "handles": {"tiktok": "ujimahal"}, "followers": {"tiktok": 50_000}}, headers=H("off")).json()
    r = c.post("/api/bookings", json={"campaignId": T["camp"]["id"], "kolId": k2["id"], "costs": {"feeRp": 23_000_000}}, headers=H("off"))
    assert r.status_code == 400 and "melebihi sisa budget campaign" in r.json()["detail"], r.text


def png():
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (300, 500), (200, 50, 50)).save(b, "PNG"); return b.getvalue()


def test_05_content_handle_and_snapshot():
    b = T["booking"]
    f = c.post("/api/files", files={"file": ("s.png", png(), "image/png")}, headers=H("off")).json()
    T["proof"] = f["id"]
    posted = (date.today() - timedelta(days=8)).isoformat()
    r = c.post("/api/contents", json={"bookingId": b["id"], "url": "https://www.tiktok.com/@orang.lain/video/123", "postedAt": posted}, headers=H("off"))
    assert r.status_code == 409 and "handle_mismatch" in r.json()["detail"]
    r = c.post("/api/contents", json={"bookingId": b["id"], "url": "https://www.tiktok.com/@orang.lain/video/123", "postedAt": posted, "handleMismatchReason": "Collab post"}, headers=H("off"))
    assert r.status_code == 200, r.text
    T["content"] = r.json()
    assert c.get(f"/api/bookings/{b['id']}", headers=H("off")).json()["status"] == "POSTED"
    # booking otomatis REPORT_DUE (8 hari tanpa H7) dan muncul di Ringkasan
    c.get("/api/bookings", headers=H("off"))
    assert c.get(f"/api/bookings/{b['id']}", headers=H("off")).json()["status"] == "REPORT_DUE"
    d = c.get(f"/api/reports/direksi?month={T['month']}", headers=H("dir")).json()
    assert d["tiles"]["noReport"] >= 1
    # NPL tidak punya field orders; field wajib kosong → ditolak
    vals = {"views": 100000, "reach": 80000, "likes": 5000, "comments": 300, "shares": 200}
    r = c.post("/api/snapshots", json={"contentId": T["content"]["id"], "day": "H7", "values": vals, "proofFiles": [T["proof"]]}, headers=H("off"))
    assert r.status_code == 400 and "Save" in r.json()["detail"], r.text
    vals["saves"] = 0
    r = c.post("/api/snapshots", json={"contentId": T["content"]["id"], "day": "H7", "values": vals, "proofFiles": []}, headers=H("off"))
    assert r.status_code == 400 and "Screenshot" in r.json()["detail"]
    r = c.post("/api/snapshots", json={"contentId": T["content"]["id"], "day": "H7", "values": vals, "proofFiles": [T["proof"]]}, headers=H("off"))
    assert r.status_code == 200, r.text
    assert c.get(f"/api/bookings/{b['id']}", headers=H("off")).json()["status"] == "POSTED"


def test_06_keranjang_kuning_fields():
    camps = c.get("/api/campaigns", headers=H("off")).json()
    kk = next(x for x in camps if x["category"] == "Keranjang Kuning")
    d = c.get(f"/api/campaigns/{kk['id']}", headers=H("off")).json()
    f = d["config"]["fields"]
    assert {"views", "productClicks", "orders", "gmvRp", "commissionRp"} <= set(f) and "mapsClicks" not in f


def test_07_report_gating_and_payment():
    b = T["booking"]
    assert c.post(f"/api/bookings/{b['id']}/pay", json={"amountRp": 1, "proofFiles": [T["proof"]]}, headers=H("fin")).status_code == 400
    assert c.post(f"/api/bookings/{b['id']}/transition", json={"to": "REPORT_APPROVED"}, headers=H("tl")).status_code == 400
    assert c.post(f"/api/bookings/{b['id']}/transition", json={"to": "REPORT_SUBMITTED"}, headers=H("off")).status_code == 200
    assert c.post(f"/api/bookings/{b['id']}/transition", json={"to": "REPORT_APPROVED"}, headers=H("off")).status_code == 403
    assert c.post(f"/api/bookings/{b['id']}/transition", json={"to": "REPORT_APPROVED"}, headers=H("tl")).status_code == 200
    q = c.get("/api/payments", headers=H("fin")).json()
    assert any(x["id"] == b["id"] for x in q["queue"])
    assert c.post(f"/api/bookings/{b['id']}/pay", json={"amountRp": 8_000_000, "proofFiles": []}, headers=H("fin")).status_code == 400
    assert c.post(f"/api/bookings/{b['id']}/pay", json={"amountRp": 8_000_000, "proofFiles": [T["proof"]]}, headers=H("fin")).status_code == 200
    assert c.get(f"/api/bookings/{b['id']}", headers=H("fin")).json()["status"] == "PAID"


def test_08_lock_after_h7():
    # snapshot H7 yang diisi untuk konten 8 hari lalu terkunci mulai besok (grace 1 hari) → simulasikan dengan konten seed lama
    bks = c.get("/api/bookings", headers=H("off")).json()
    old = next(x for x in bks if x["status"] == "PAID" and x["campaign"]["category"] == "Regular Visit")
    det = c.get(f"/api/bookings/{old['id']}", headers=H("off")).json()
    snap = next(s for s in det["contents"][0]["snapshots"] if s["day"] == "H7")
    assert snap["locked"]
    vals = {k: snap[k] for k in det["requiredFields"]}
    vals["views"] += 1000
    r = c.post("/api/snapshots", json={"contentId": det["contents"][0]["id"], "day": "H7", "values": vals, "proofFiles": snap["proofFiles"]}, headers=H("off"))
    assert r.status_code == 403
    r = c.post("/api/snapshots", json={"contentId": det["contents"][0]["id"], "day": "H7", "values": vals, "proofFiles": snap["proofFiles"], "reason": "Koreksi typo"}, headers=H("tl"))
    assert r.status_code == 200
    log = c.get(f"/api/audit?ref={snap['id']}", headers=H("tl")).json()
    assert log and log[0]["before"]["views"] == snap["views"] and log[0]["after"]["views"] == snap["views"] + 1000


def test_09_assisted_uplift_and_roi_split():
    camps = c.get("/api/campaigns", headers=H("dir")).json()
    rv = next(x for x in camps if x["name"] == "Regular Visit Bandung Nov")
    d = c.get(f"/api/campaigns/{rv['id']}", headers=H("dir")).json()
    assert d["agg"]["revenueAssisted"] > 0
    rep = c.get(f"/api/reports/direksi?month={rv['month']}", headers=H("dir")).json()
    t = rep["tiles"]
    assert "roiDirect" in t and "roiTotal" in t and t["roiTotal"] >= t["roiDirect"]
    cat = next(x for x in rep["categories"] if x["category"] == "Regular Visit")
    assert cat["evidence"] == ["DIRECT", "ASSISTED"]
    assert any(f["flags"][0]["code"] in ("views_low", "report_overdue") for f in rep["flags"] if f["bookingId"])


def test_10_roles_and_exports():
    assert c.post("/api/kols", json={"name": "Direksi coba"}, headers=H("dir")).status_code == 403
    ks = c.get("/api/kols", headers=H("dir")).json()
    assert all("•" in (k.get("bankAccount") or "•") for k in ks)
    ks_f = c.get("/api/kols", headers=H("fin")).json()
    assert any("•" not in (k.get("bankAccount") or "•") for k in ks_f)
    m = date.today().strftime("%Y-%m")
    r = c.get(f"/api/reports/direksi?month={m}&format=pdf", headers=H("dir"))
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    open("/tmp/direksi.pdf", "wb").write(r.content)
    r = c.get(f"/api/reports/direksi?month={m}&format=xlsx", headers=H("dir"))
    assert r.status_code == 200 and r.content[:2] == b"PK"
    assert c.get("/api/reports/weekly?format=xlsx", headers=H("tl")).status_code == 200
    assert c.get(f"/api/reports/review?month={m}&format=xlsx", headers=H("tl")).status_code == 200
    camps = c.get("/api/campaigns", headers=H("tl")).json()
    assert c.get(f"/api/reports/campaign/{camps[0]['id']}?format=xlsx", headers=H("tl")).status_code == 200
    assert c.get("/api/public-metrics/kol", headers={"X-API-Key": "salah"}).status_code == 401
    assert c.get("/api/public-metrics/kol", headers={"X-API-Key": "testkey"}).status_code == 200
    assert c.get("/api/public-metrics/kol-codes", headers={"X-API-Key": "testkey"}).json()
    t = c.get("/api/tasks", headers=H("off")).json()
    assert "snapshots" in t


def test_11_blacklist_and_cancel():
    ks = c.get("/api/kols", headers=H("off")).json()
    bl = next(k for k in ks if k["status"] == "Blacklist")
    camps = c.get("/api/campaigns", headers=H("off")).json()
    cid = next(x["id"] for x in camps if x["gateStatus"] == "GO")
    r = c.post("/api/bookings", json={"campaignId": cid, "kolId": bl["id"], "costs": {"feeRp": 100000}}, headers=H("off"))
    assert r.status_code == 400 and "Blacklist" in r.json()["detail"]
    bks = c.get("/api/bookings?status=SHORTLIST", headers=H("off")).json()
    r = c.post(f"/api/bookings/{bks[0]['id']}/transition", json={"to": "CANCELLED"}, headers=H("off"))
    assert r.status_code == 400
    r = c.post(f"/api/bookings/{bks[0]['id']}/transition", json={"to": "CANCELLED", "reason": "Rate card tidak cocok"}, headers=H("off"))
    assert r.status_code == 200


def test_12_self_registration():
    base = {"name": "Uji Daftar", "role": "KOL Officer", "pin": "2468"}
    r = c.post("/api/auth/register", json={**base, "email": "uji@gmail.com"})
    assert r.status_code == 400 and "citarasakuliner.com" in r.json()["detail"]
    r = c.post("/api/auth/register", json={**base, "email": "uji@citarasakuliner.com.evil.id"})
    assert r.status_code == 400
    r = c.post("/api/auth/register", json={**base, "email": "uji@citarasakuliner.com", "role": "Manager"})
    assert r.status_code == 400 and "Role" in r.json()["detail"]
    r = c.post("/api/auth/register", json={**base, "email": "Uji@CitarasaKuliner.com"})
    assert r.status_code == 200, r.text
    assert c.post("/api/auth/register", json={**base, "name": "Lain", "email": "uji@citarasakuliner.com"}).status_code == 409
    # pending: tidak muncul di daftar login
    assert not any(u["name"] == "Uji Daftar" for u in c.get("/api/auth/users").json())
    assert c.get("/api/users/pending", headers=H("tl")).status_code == 403
    pend = c.get("/api/users/pending", headers=H("mgr")).json()
    u = next(x for x in pend if x["email"] == "uji@citarasakuliner.com")
    assert any(x["id"] == u["id"] for x in c.get("/api/tasks", headers=H("mgr")).json()["registrations"])
    assert c.post(f"/api/users/{u['id']}/approve", json={"role": "Manager"}, headers=H("mgr")).status_code == 400
    assert c.post(f"/api/users/{u['id']}/approve", json={"role": "KOL TL"}, headers=H("mgr")).status_code == 200
    h = login("Uji Daftar", "2468")
    assert c.get("/api/auth/me", headers=h).json()["role"] == "KOL TL"
    # tolak pendaftar lain
    c.post("/api/auth/register", json={"name": "Uji Tolak", "email": "tolak@citarasakuliner.com", "role": "KOL Officer", "pin": "1357"})
    p2 = next(x for x in c.get("/api/users/pending", headers=H("mgr")).json() if x["email"] == "tolak@citarasakuliner.com")
    assert c.post(f"/api/users/{p2['id']}/reject", json={"reason": ""}, headers=H("mgr")).status_code == 400
    assert c.post(f"/api/users/{p2['id']}/reject", json={"reason": "Bukan tim KOL"}, headers=H("mgr")).status_code == 200
    assert not any(u["name"] == "Uji Tolak" for u in c.get("/api/auth/users").json())
