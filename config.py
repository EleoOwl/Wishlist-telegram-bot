import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Put it in .env or environment variables.")

DB_PATH = os.getenv("DB_PATH", "./data/app.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

WEBHOOK_BASE = os.getenv("WEBHOOK_BASE", "").rstrip("/")
if WEBHOOK_BASE and not WEBHOOK_BASE.startswith("https://"):
    raise RuntimeError("WEBHOOK_BASE must start with https://")

# Path to receive Telegram updates
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "")
WEBHOOK_URL = f"{WEBHOOK_BASE}{WEBHOOK_PATH}"

# Telegram secret token
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", "")

# Local server bind
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8080"))

_ADMIN_RAW = os.getenv("ADMIN_USER_ID", "0").strip()
try:
    ADMIN_USER_ID = int(_ADMIN_RAW)
except ValueError:
    raise RuntimeError("ADMIN_USER_ID must be an integer (Telegram user id).")