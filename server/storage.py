import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List

from .config import DATABASE_URL, DATA_DIR, DB_PATH, DB_PROVIDER, UPLOAD_DIR

DEFAULT_DB: Dict[str, Dict[str, Any]] = {
    "users": {},
    "files": {},
    "reports": {},
    "orders": {},
}


def ensure_storage() -> None:
    if use_postgres():
        ensure_postgres()
        return
    ensure_json_storage()


def load_db() -> Dict[str, Any]:
    if use_postgres():
        return load_postgres_db()
    return load_json_db()


def save_db(db: Dict[str, Any]) -> None:
    if use_postgres():
        save_postgres_db(db)
        return
    save_json_db(db)


def use_postgres() -> bool:
    return DB_PROVIDER == "postgres" and bool(DATABASE_URL)


def active_db_provider() -> str:
    return "postgres" if use_postgres() else "json"


def ensure_json_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        save_json_db(empty_db())


def empty_db() -> Dict[str, Dict[str, Any]]:
    return {key: dict(value) for key, value in DEFAULT_DB.items()}


def load_json_db() -> Dict[str, Any]:
    ensure_storage()
    with DB_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json_db(db: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = Path(f"{DB_PATH}.tmp")
    with tmp_path.open("w", encoding="utf-8") as file:
        json.dump(db, file, ensure_ascii=False, indent=2)
    tmp_path.replace(DB_PATH)


@contextmanager
def postgres_connection() -> Iterator[Any]:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Postgres storage requires psycopg. Install requirements.txt first.") from exc

    with psycopg.connect(DATABASE_URL) as conn:
        yield conn


def ensure_postgres() -> None:
    with postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                create table if not exists users (
                    id text primary key,
                    data jsonb not null,
                    created_at_ms bigint not null default 0
                )
                """
            )
            cur.execute(
                """
                create table if not exists files (
                    id text primary key,
                    user_id text not null,
                    data jsonb not null,
                    created_at_ms bigint not null default 0,
                    deleted boolean not null default false
                )
                """
            )
            cur.execute(
                """
                create table if not exists reports (
                    id text primary key,
                    user_id text not null,
                    data jsonb not null,
                    created_at_ms bigint not null default 0,
                    deleted boolean not null default false
                )
                """
            )
            cur.execute(
                """
                create table if not exists orders (
                    id text primary key,
                    user_id text not null,
                    report_id text not null default '',
                    status text not null default '',
                    data jsonb not null,
                    created_at_ms bigint not null default 0
                )
                """
            )
            cur.execute("create index if not exists idx_files_user_id on files (user_id)")
            cur.execute("create index if not exists idx_reports_user_id_created on reports (user_id, created_at_ms desc)")
            cur.execute("create index if not exists idx_orders_user_id on orders (user_id)")
        conn.commit()


def load_postgres_db() -> Dict[str, Any]:
    ensure_postgres()
    db = empty_db()
    with postgres_connection() as conn:
        with conn.cursor() as cur:
            for table in ["users", "files", "reports", "orders"]:
                cur.execute(f"select id, data from {table}")
                db[table] = {row[0]: row[1] for row in cur.fetchall()}
    return db


def save_postgres_db(db: Dict[str, Any]) -> None:
    ensure_postgres()
    try:
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise RuntimeError("Postgres JSONB support requires psycopg.") from exc

    with postgres_connection() as conn:
        with conn.cursor() as cur:
            for user in db.get("users", {}).values():
                cur.execute(
                    """
                    insert into users (id, data, created_at_ms)
                    values (%s, %s, %s)
                    on conflict (id) do update set
                        data = excluded.data,
                        created_at_ms = excluded.created_at_ms
                    """,
                    (user["id"], Jsonb(user), created_ms(user)),
                )
            for file_record in db.get("files", {}).values():
                cur.execute(
                    """
                    insert into files (id, user_id, data, created_at_ms, deleted)
                    values (%s, %s, %s, %s, %s)
                    on conflict (id) do update set
                        user_id = excluded.user_id,
                        data = excluded.data,
                        created_at_ms = excluded.created_at_ms,
                        deleted = excluded.deleted
                    """,
                    (
                        file_record["id"],
                        file_record.get("userId", ""),
                        Jsonb(file_record),
                        created_ms(file_record),
                        bool(file_record.get("deleted")),
                    ),
                )
            for report in db.get("reports", {}).values():
                cur.execute(
                    """
                    insert into reports (id, user_id, data, created_at_ms, deleted)
                    values (%s, %s, %s, %s, %s)
                    on conflict (id) do update set
                        user_id = excluded.user_id,
                        data = excluded.data,
                        created_at_ms = excluded.created_at_ms,
                        deleted = excluded.deleted
                    """,
                    (
                        report["id"],
                        report.get("userId", ""),
                        Jsonb(report),
                        created_ms(report),
                        bool(report.get("deleted")),
                    ),
                )
            for order in db.get("orders", {}).values():
                cur.execute(
                    """
                    insert into orders (id, user_id, report_id, status, data, created_at_ms)
                    values (%s, %s, %s, %s, %s, %s)
                    on conflict (id) do update set
                        user_id = excluded.user_id,
                        report_id = excluded.report_id,
                        status = excluded.status,
                        data = excluded.data,
                        created_at_ms = excluded.created_at_ms
                    """,
                    (
                        order["id"],
                        order.get("userId", ""),
                        order.get("reportId", ""),
                        order.get("status", ""),
                        Jsonb(order),
                        created_ms(order),
                    ),
                )
        conn.commit()


def created_ms(record: Dict[str, Any]) -> int:
    value = record.get("createdAtMs")
    if isinstance(value, int):
        return value
    return 0


def now_ms() -> int:
    return int(time.time() * 1000)


def now_text() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def reports_for_user(user_id: str) -> List[Dict[str, Any]]:
    if use_postgres():
        ensure_postgres()
        with postgres_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select data
                    from reports
                    where user_id = %s and deleted = false
                    order by created_at_ms desc
                    """,
                    (user_id,),
                )
                return [row[0] for row in cur.fetchall()]

    db = load_db()
    reports = [
        report
        for report in db["reports"].values()
        if report.get("userId") == user_id and not report.get("deleted")
    ]
    return sorted(reports, key=lambda report: report.get("createdAtMs", 0), reverse=True)
