import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .config import CORS_ORIGINS, FRONTEND_DIST, ENABLE_JOBS
from .seed import bootstrap
from .routers import auth_users, kols, campaigns, bookings, contents, data, reports, admin


@asynccontextmanager
async def lifespan(app):
    app.state.db_error = None
    try:
        await bootstrap()
    except Exception as e:  # jangan crash: tampilkan penyebab di /api/health
        app.state.db_error = f"{type(e).__name__}: {str(e)[:300]}"
        logging.getLogger("uvicorn.error").error("Gagal konek MongoDB saat start — cek MONGO_URL. %s", app.state.db_error)
    sched = None
    if ENABLE_JOBS:
        from .jobs import start_scheduler
        sched = start_scheduler()
    yield
    if sched:
        sched.shutdown(wait=False)

app = FastAPI(title="KOL Ledger — CRK", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
for r in (auth_users, kols, campaigns, bookings, contents, data, reports, admin):
    app.include_router(r.router)


@app.get("/api/health")
async def health():
    from .db import client
    from .config import MONGO_URL
    if not os.getenv("MONGO_URL", "").strip():
        return {"ok": False, "db": "GAGAL", "detail": "Variable MONGO_URL kosong atau referensinya tidak ter-resolve, jadi aplikasi mencoba localhost.",
                "hint": "Di Railway, isi MONGO_URL lewat 'Add Reference' ke service MongoDB (mis. ${{MongoDB.MONGO_URL}}) — nama service harus sama persis."}
    try:
        await client.admin.command("ping")
        if app.state.db_error:
            await bootstrap()
            app.state.db_error = None
        return {"ok": True, "db": "terhubung"}
    except Exception as e:
        return JSONResponse(status_code=200, content={"ok": False, "db": "GAGAL", "detail": f"{type(e).__name__}: {str(e)[:300]}",
                                                      "hint": "Cek variable MONGO_URL di Railway (bukan nilai contoh user:pass@cluster)."})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": f"Terjadi kesalahan server: {type(exc).__name__}"})


# Frontend build (satu service di Railway)
dist = os.path.abspath(FRONTEND_DIST)
if os.path.isdir(dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist, "assets")), name="assets")

    @app.get("/{path:path}")
    async def spa(path: str):
        if path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Tidak ditemukan"})
        f = os.path.join(dist, path)
        if path and os.path.isfile(f):
            return FileResponse(f)
        return FileResponse(os.path.join(dist, "index.html"))
