import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("BIKENGBAO_DATA_DIR", str(BASE_DIR / "data")))
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "db.json"

HOST = os.getenv("BIKENGBAO_HOST", "127.0.0.1")
PORT = int(os.getenv("BIKENGBAO_PORT", "8787"))

DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_PROVIDER = os.getenv("BIKENGBAO_DB_PROVIDER", "postgres" if DATABASE_URL else "json")

FILE_STORAGE_PROVIDER = os.getenv(
    "BIKENGBAO_FILE_STORAGE_PROVIDER",
    "blob" if os.getenv("BLOB_READ_WRITE_TOKEN") else "local",
)
BLOB_READ_WRITE_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN", "")
BLOB_ACCESS = os.getenv("BIKENGBAO_BLOB_ACCESS", "public")

AI_PROVIDER = os.getenv("BIKENGBAO_AI_PROVIDER", "mock")
OCR_PROVIDER = os.getenv("BIKENGBAO_OCR_PROVIDER", "mock")
PAYMENT_PROVIDER = os.getenv("BIKENGBAO_PAYMENT_PROVIDER", "mock")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

WECHAT_APP_ID = os.getenv("WECHAT_APP_ID", "")
WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "")
WECHAT_MCH_ID = os.getenv("WECHAT_MCH_ID", "")
WECHAT_PAY_SERIAL_NO = os.getenv("WECHAT_PAY_SERIAL_NO", "")
