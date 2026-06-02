import json
import time
from pathlib import Path
from typing import Any, Dict, List

from .config import DATA_DIR, DB_PATH, UPLOAD_DIR


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        save_db(
            {
                "users": {},
                "files": {},
                "reports": {},
                "orders": {}
            }
        )


def load_db() -> Dict[str, Any]:
    ensure_storage()
    with DB_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_db(db: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = Path(f"{DB_PATH}.tmp")
    with tmp_path.open("w", encoding="utf-8") as file:
        json.dump(db, file, ensure_ascii=False, indent=2)
    tmp_path.replace(DB_PATH)


def now_ms() -> int:
    return int(time.time() * 1000)


def now_text() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def reports_for_user(user_id: str) -> List[Dict[str, Any]]:
    db = load_db()
    reports = [
        report
        for report in db["reports"].values()
        if report.get("userId") == user_id and not report.get("deleted")
    ]
    return sorted(reports, key=lambda report: report.get("createdAtMs", 0), reverse=True)
