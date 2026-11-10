import os
from zoneinfo import ZoneInfo

MONGO_URL = os.getenv("MONGO_URL", "").strip() or "mongodb://127.0.0.1:27017"
MONGO_URL_SET = bool(os.getenv("MONGO_URL", "").strip())
DB_NAME = os.getenv("DB_NAME", "kol_ledger")
JWT_SECRET = os.getenv("JWT_SECRET", "ganti-secret-ini-di-railway")
JWT_HOURS = int(os.getenv("JWT_HOURS", "12"))
FILE_DIR = os.getenv("FILE_DIR", os.path.join(os.path.dirname(__file__), "..", "data", "files"))
BACKUP_DIR = os.getenv("BACKUP_DIR", os.path.join(os.path.dirname(__file__), "..", "data", "backups"))
PUBLIC_METRICS_API_KEY = os.getenv("PUBLIC_METRICS_API_KEY", "")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
BOOTSTRAP_NAME = os.getenv("BOOTSTRAP_NAME", "Marketing Manager")
BOOTSTRAP_PIN = os.getenv("BOOTSTRAP_PIN", "123456")
FRONTEND_DIST = os.getenv("FRONTEND_DIST", os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
ENABLE_JOBS = os.getenv("ENABLE_JOBS", "1") == "1"
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
TZ = ZoneInfo("Asia/Jakarta")

os.makedirs(FILE_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
