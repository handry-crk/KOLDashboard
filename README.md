# KOL Ledger — CRK / Cimol Bojot AA

Dashboard akuntabilitas KOL campaign: listing KOL & tier, booking per kategori objective (Regular Visit, Frozen, NPL, Info Lokasi, Keranjang Kuning, TikTok GO), report wajib H+1/H+3/H+7 dengan screenshot, budget guard, approval, antrean pelunasan Finance, dan laporan direksi (PDF/Excel).

Stack: **FastAPI + MongoDB (Motor) + React (Vite, Tailwind, Recharts)**. Satu service: backend menyajikan API di `/api` sekaligus build frontend.

## Aturan yang ditegakkan sistem
| Aturan | Di mana |
|---|---|
| Tanpa report H+7 yang di-approve KOL TL → tidak bisa dilunasi | `POST /api/bookings/{id}/pay` (override hanya Manager + alasan tertulis, tercatat audit) |
| KPI wajib per kategori; 0 boleh, kosong tidak; screenshot wajib | `POST /api/snapshots` |
| DIRECT / ASSISTED / EXPOSURE tidak pernah dijumlah jadi satu ROI | `logic.py`, `reporting.py` |
| Campaign ≤ sisa plan kategori; total plan ≤ pagu bulanan | `campaigns.py`, `data.py` |
| Booking ≤ sisa budget campaign; Macro/Mega atau ≥ batas → approval Manager; campaign ≥ batas → Gate GO/GWC | `bookings.py` |
| Metrik terkunci setelah H+7 (H+30 untuk snapshot H30); ubah hanya KOL TL + alasan | `services.py`, `contents.py` |
| POSTED tanpa H+7 setelah 7 hari → otomatis REPORT_DUE | `services.refresh_statuses` |
| Tier otomatis dari follower; override KOL TL + alasan | `logic.kol_tier`, `kols.py` |
| Semua perubahan penting tercatat | koleksi `audit`, menu Laporan → Audit log |

Benchmark CPV/ER/cost per outcome/ROAS = *angka ilustrasi*; ubah di Pengaturan setelah 8 minggu data.

## Jalankan lokal
```bash
# MongoDB lokal di 27017
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
cd ../frontend && npm install && npm run dev      # http://localhost:5173 (proxy /api → 8001)
```
Login pertama: **Marketing Manager**, PIN dari `BOOTSTRAP_PIN` (default `123456` — ganti!).
Pengaturan → Pemeliharaan → **Isi data contoh** (hanya DB kosong) membuat user Agoy (KOL TL), Rina & Dimas (Officer), Sari (Finance), Direksi CRK — semua PIN `1234` — plus 30 KOL fiktif, 8 campaign, ~40 booking, dan penjualan outlet 75 hari. Jangan jalankan di produksi.

## Deploy ke Railway
1. Push folder ini ke repo GitHub privat (mis. `crk-kol-ledger`).
2. Railway → **New Project → Deploy from GitHub repo**. Railway membaca `railway.json` + `Dockerfile` (build frontend lalu backend dalam satu image).
3. Database: **+ New → Database → MongoDB** (plugin Railway) lalu set `MONGO_URL=${{MongoDB.MONGO_URL}}`, atau pakai MongoDB Atlas (backup otomatis lebih aman).
4. **Volume**: service → Settings → Volumes → mount path `/data` (menyimpan screenshot insight & backup JSON).
5. **Variables**: salin dari `.env.example` — minimal `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `BOOTSTRAP_PIN`, `PUBLIC_METRICS_API_KEY`.
6. Settings → Networking → **Generate Domain** (atau custom domain `kol.cimolbojotaa.com`).
7. Buka domain → login Marketing Manager → ganti PIN, buat user tim, isi Budget plan bulan berjalan, import outlet & penjualan (CSV) di Pengaturan.

Job terjadwal (WIB, butuh `ENABLE_JOBS=1` dan 1 replica): cek status & kunci 00.10 · reminder officer 09.00 · digest Senin 08.00 · draft Review M+1 tgl 3 · backup Minggu 02.00. Email hanya terkirim bila `SMTP_*` diisi.

## Format import CSV (pemisah `,` atau `;`)
- Outlet: `code,name,area`
- Penjualan harian (export Metabase): `date,outletCode,revenueRp,transactions[,sku:MOZZA,...]` — dipakai untuk uplift ASSISTED (window D0–D+6; Info Lokasi D0–D+13; baseline = rata-rata hari yang sama 4 minggu sebelumnya).

## Integrasi (header `X-API-Key`)
- `GET /api/public-metrics/kol?week=YYYY-MM-DD` → angka tab 8 Meeting Input Pack
- `GET /api/public-metrics/kol-codes` → kode unik KOL aktif (untuk promoCode Stamp Bojot / kasir)

## Test
```bash
cd backend
DB_NAME=kol_test ENABLE_JOBS=0 PUBLIC_METRICS_API_KEY=testkey uvicorn app.main:app --port 8001 &
BASE=http://localhost:8001 pytest -q tests/     # 12 acceptance test (DB harus kosong)
```

## Belum termasuk (iterasi berikutnya)
Import otomatis TikTok Shop Affiliate / TikTok GO / voucher marketplace, halaman brief publik untuk KOL, reminder WhatsApp (Fonnte), estimator pra-booking, cek status post otomatis, tampilan QBR.
