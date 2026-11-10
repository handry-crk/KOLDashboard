"""Test aturan: mencoba melanggar setiap aturan bisnis (jalan setelah test_acceptance pada DB yang sama)."""
import httpx, io
from datetime import date, timedelta
from PIL import Image
import os
B=os.getenv("BASE","http://localhost:8001"); c=httpx.Client(base_url=B,timeout=60)
def L(n,p="1234"):
    u=[x for x in c.get("/api/auth/users").json() if x["name"]==n][0]
    return {"Authorization":"Bearer "+c.post("/api/auth/login",json={"userId":u["id"],"pin":p}).json()["token"]}

def test_rules_probe():
    M=L("Marketing Manager","123456")
    c.post("/api/admin/seed",headers=M)
    TL=L("Agoy"); OF=L("Rina"); FI=L("Sari (Finance)"); DI=L("Direksi CRK")
    bs=c.get("/api/bookings",headers=TL).json()
    def by(name, st=None): return [b for b in bs if b["kol"]["name"]==name and (st is None or b["status"]==st)][0]
    def R(tag, r, exp):
        assert r.status_code in exp, f"{tag}: {r.status_code} {r.text[:200]}"
    # 1 mundur dari PAID
    paid=[b for b in bs if b["status"]=="PAID"][0]
    R("TL mundurkan PAID->POSTED", c.post(f"/api/bookings/{paid['id']}/transition",json={"to":"POSTED","reason":"tes mundur"},headers=TL),(400,403))
    # 2 naikkan biaya setelah DEAL melewati batas approval oleh officer
    deal=[b for b in bs if b["status"]=="DEAL" and b["tierAtBooking"] in ("Micro","Nano")][0]
    d=c.get(f"/api/bookings/{deal['id']}",headers=OF).json()
    body={k:d[k] for k in ("campaignId","kolId","platform","deliverables","trackingLink","uniqueCode","contentRights","notes")}
    body["costs"]={**d["costs"],"feeRp":26_000_000}
    R("Officer naikkan fee >batas setelah DEAL", c.put(f"/api/bookings/{deal['id']}",json=body,headers=OF),(400,403))
    # 3 tambah konten ke booking yang sudah REPORT_APPROVED
    ap=[b for b in bs if b["status"]=="REPORT_APPROVED"][0]
    R("Tambah konten ke booking approved", c.post("/api/contents",json={"bookingId":ap["id"],"url":"https://www.tiktok.com/@x/video/1","postedAt":date.today().isoformat(),"handleMismatchReason":"x"},headers=OF),(400,403))
    # 4 officer ubah H7 booking approved (masih grace)  -> cek via snapshot terbaru
    # 5 bayar nominal aneh
    q=c.get("/api/payments",headers=FI).json()["queue"][0]
    img=io.BytesIO(); Image.new("RGB",(50,50)).save(img,"PNG")
    f=c.post("/api/files",files={"file":("a.png",img.getvalue(),"image/png")},headers=FI).json()["id"]
    R("Bayar nominal negatif/lebih", c.post(f"/api/bookings/{q['id']}/pay",json={"amountRp":999_999_999,"proofFiles":[f]},headers=FI),(400,))
    # 6 bukti file palsu
    R("Bukti file id palsu", c.post(f"/api/bookings/{q['id']}/pay",json={"amountRp":1,"proofFiles":["tidakada.jpg"]},headers=FI),(400,))
    # 7 file tanpa login
    R("Download file tanpa login", c.get(f"/api/files/{f}"),(401,403))
    # 8 regex handle
    R("Handle regex aneh", c.post("/api/kols",json={"name":"Regex","handles":{"tiktok":"a(b"}},headers=OF),(200,409))
    # 9 settings rusak
    R("Settings GM 5 (500%)", c.put("/api/settings",json={"gmBlended":5},headers=M),(400,422))
    R("Settings tier tidak urut", c.put("/api/settings",json={"tierThresholds":{"Nano":1000,"Micro":500000,"Macro":100000,"Mega":1000000}},headers=M),(400,422))
    # 10 HOLD campaign dengan booking DEAL membebaskan plan
    camps=c.get("/api/campaigns?month="+date.today().strftime("%Y-%m"),headers=M).json()
    tg=[x for x in camps if x["category"]=="TikTok GO"][0]
    up={k:tg[k] for k in ("name","category","objective","month","start","end","target","budgetRp","kpiTargets","gateNote","linkedInitiativeCode","promoCodePrefix")}
    c.put(f"/api/campaigns/{tg['id']}",json={**up,"gateStatus":"HOLD"},headers=M)
    bud=c.get("/api/budget?month="+tg["month"],headers=M).json()
    row=[r for r in bud["rows"] if r["category"]=="TikTok GO"][0]
    assert row["allocatedRp"] >= tg["committed"], "HOLD harus tetap menghitung committed"
    r=c.post("/api/campaigns",json={"name":"Isi celah HOLD","category":"TikTok GO","month":tg["month"],"start":tg["start"],"end":tg["end"],"budgetRp":15_000_000},headers=M)
    R("Buat campaign memakai plan yang masih terpakai booking HOLD", r,(400,))
    c.put(f"/api/campaigns/{tg['id']}",json={**up,"gateStatus":"PENDING"},headers=M)
    # 11 SELESAI dengan booking masih jalan
    rv=[x for x in camps if x["category"]=="Regular Visit"][0]
    upr={k:rv[k] for k in ("name","category","objective","month","start","end","target","budgetRp","kpiTargets","gateNote","linkedInitiativeCode","promoCodePrefix")}
    c.post(f"/api/campaigns/{rv['id']}/review",json={"review":"KEEP","reviewNote":"uji review panjang"},headers=TL)
    R("Tutup SELESAI saat booking masih DRAFT", c.put(f"/api/campaigns/{rv['id']}",json={**upr,"gateStatus":"SELESAI"},headers=M),(400,))
    # 12 excel injection
    k=c.post("/api/kols",json={"name":"=HYPERLINK(\"http://x\",\"klik\")","handles":{"tiktok":"injeksi"}},headers=OF)
    from openpyxl import load_workbook
    x=c.get("/api/reports/direksi?format=xlsx",headers=M).content
    # 13 cancel booking with DP -> budget
    dp=[b for b in bs if b["status"] in ("DEAL","BRIEF_SENT","DRAFT_REVIEW") and (b.get("payment") or {}).get("dpRp")]

    # 14 direksi tidak bisa upload/akses tulis
    R("Direksi buat booking", c.post("/api/bookings",json={"campaignId":rv["id"],"kolId":bs[0]["kolId"]},headers=DI),(403,))
    # 15 officer lihat rekening penuh?
    ks=c.get("/api/kols",headers=OF).json(); assert all("•" in (k.get("bankAccount") or "•") for k in ks)
    # 16 snapshot dengan engagement > views
    # 17 pending user tidak bisa login
    c.post("/api/auth/register",json={"name":"Probe Pending","email":"probe@citarasakuliner.com","role":"KOL Officer","pin":"1111"})
    pend=[u for u in c.get("/api/users/pending",headers=M).json() if u["email"]=="probe@citarasakuliner.com"][0]
    R("Login user pending", c.post("/api/auth/login",json={"userId":pend["id"],"pin":"1111"}),(403,404))
    # 18 Manager nonaktifkan user lalu token lama
    # ---- putaran 3
    bs=c.get("/api/bookings",headers=TL).json()
    w=[b for b in bs if b["status"]=="WAITING_APPROVAL"][0]
    R("Approve Mega melebihi budget -> tetap WAITING tanpa approval nyangkut", c.post(f"/api/bookings/{w['id']}/approve",json={"to":"approve","reason":"ok"},headers=M),(400,))
    d=c.get(f"/api/bookings/{w['id']}",headers=M).json(); assert d["status"]=="WAITING_APPROVAL" and not d["hasApproval"]
    can=[b for b in bs if b["status"]=="CANCELLED"][0]
    R("Aktifkan CANCELLED langsung ke DEAL", c.post(f"/api/bookings/{can['id']}/transition",json={"to":"DEAL","reason":"aktif lagi"},headers=TL),(400,))
    po=[b for b in bs if b["status"]=="POSTED" and b["metrics"]["contents"]][0]
    dd=c.get(f"/api/bookings/{po['id']}",headers=TL).json(); ct=dd["contents"][0]; s1=[s for s in ct["snapshots"] if s["day"]=="H1"][0]
    vals={k:s1.get(k,0) for k in dd["requiredFields"]}; vals["views"]=max(0,s1["views"]-10)
    day="H3" if any(s["day"]=="H3" for s in ct["snapshots"]) or True else "H3"
    R("Views H3 lebih kecil dari H1", c.post("/api/snapshots",json={"contentId":ct["id"],"day":"H3","values":vals,"proofFiles":s1["proofFiles"],"reason":"tes"},headers=TL),(400,))
    us=c.get("/api/users",headers=M).json(); me=[u for u in us if u["role"]=="Manager"][0]
    R("Nonaktifkan Manager terakhir", c.put(f"/api/users/{me['id']}",json={"name":me["name"],"role":"Manager","active":False},headers=M),(400,))

