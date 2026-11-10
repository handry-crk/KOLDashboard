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
    await bootstrap()
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
    return {"ok": True}


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
