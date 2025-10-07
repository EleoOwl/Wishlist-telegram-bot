import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Put it in .env or environment variables.")

DB_PATH = os.getenv("DB_PATH", "./data/app.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

_ADMIN_RAW = os.getenv("ADMIN_USER_ID", "0").strip()
try:
    ADMIN_USER_ID = int(_ADMIN_RAW)
except ValueError:
    raise RuntimeError("ADMIN_USER_ID must be an integer (Telegram user id).")