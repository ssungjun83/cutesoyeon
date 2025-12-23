from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import hashlib
import sqlite3
from pathlib import Path

from kakao_parser import KakaoMessage, normalize_text_for_dedup


SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dt TEXT NOT NULL,
  dt_minute TEXT NOT NULL,
  sender TEXT NOT NULL,
  text TEXT NOT NULL,
  norm_text TEXT NOT NULL,
  dedup_key TEXT NOT NULL UNIQUE,
  source TEXT,
  imported_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);

CREATE INDEX IF NOT EXISTS idx_messages_dt ON messages(dt);
"""


def _dt_minute(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M")


def _dedup_key(dt_minute: str, norm_text: str) -> str:
    raw = f"{dt_minute}\n{norm_text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def import_messages(db_path: Path, messages: list[KakaoMessage], source: str | None = None) -> dict:
    init_db(db_path)
    inserted = 0
    skipped = 0
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        for msg in messages:
            dt_iso = msg.dt.isoformat(timespec="seconds")
            dt_minute = _dt_minute(msg.dt)
            norm_text = normalize_text_for_dedup(msg.text)
            key = _dedup_key(dt_minute, norm_text)
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO messages
                (dt, dt_minute, sender, text, norm_text, dedup_key, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (dt_iso, dt_minute, msg.sender, msg.text, norm_text, key, source),
            )
            if cur.rowcount == 1:
                inserted += 1
            else:
                skipped += 1
        conn.commit()

    return {"inserted": inserted, "skipped": skipped, "total": len(messages)}


def fetch_messages(
    db_path: Path,
    limit: int | None = None,
    before_dt: str | None = None,
    order: str = "asc",
) -> list[dict]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        params: list[object] = []
        where = ""
        if before_dt:
            where = "WHERE dt < ?"
            params.append(before_dt)

        order_sql = "ASC" if order.lower() == "asc" else "DESC"
        limit_sql = ""
        if limit is not None:
            limit_sql = "LIMIT ?"
            params.append(int(limit))
        rows = conn.execute(
            f"""
            SELECT id, dt, sender, text, source, imported_at
            FROM messages
            {where}
            ORDER BY dt {order_sql}, id {order_sql}
            {limit_sql}
            """,
            params,
        ).fetchall()
    items = [dict(r) for r in rows]
    return items


def fetch_senders(db_path: Path, limit: int = 50) -> list[dict]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT sender, COUNT(*) AS count
            FROM messages
            GROUP BY sender
            ORDER BY count DESC, sender ASC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [dict(r) for r in rows]


def get_latest_dt(db_path: Path) -> str | None:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT dt FROM messages ORDER BY dt DESC, id DESC LIMIT 1").fetchone()
    return row[0] if row else None


def get_oldest_dt(db_path: Path) -> str | None:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT dt FROM messages ORDER BY dt ASC, id ASC LIMIT 1").fetchone()
    return row[0] if row else None

