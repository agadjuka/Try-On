#!/usr/bin/env python3
"""Только коллекция Firestore `api_keys` -> SQLite (UPSERT).

Запуск с машины, где есть репозиторий и .env (и доступ к Firestore):

  cd /home/ubuntu/bot_project
  export GOOGLE_APPLICATION_CREDENTIALS=/home/ubuntu/bot_project/secrets/gcp-sa.json
  python3 scripts/sync_api_keys_from_firestore.py

Или одной строкой из корня проекта (Windows PowerShell):

  $env:GOOGLE_APPLICATION_CREDENTIALS="D:\\...\\gcp-sa.json"; python scripts/sync_api_keys_from_firestore.py

Переменные SQLITE_PATH и FIRESTORE_* берутся из .env через Settings.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from google.cloud import firestore  # noqa: E402

from bot.core.config import get_settings  # noqa: E402
from bot.database.sqlite_schema import SCHEMA_SQL, ensure_sqlite_parent_dir  # noqa: E402


def _iso(val) -> str | None:
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def main() -> None:
    settings = get_settings()
    if settings.database_backend != "sqlite":
        print(
            "Внимание: DATABASE_BACKEND не sqlite — ключи всё равно будут записаны в SQLITE_PATH.",
            file=sys.stderr,
        )

    sqlite_path = Path(settings.sqlite_path).expanduser().resolve()
    ensure_sqlite_parent_dir(str(sqlite_path))

    conn = sqlite3.connect(str(sqlite_path))
    conn.executescript(SCHEMA_SQL)
    conn.commit()

    client = firestore.Client(
        project=settings.google_cloud_project_id,
        database=settings.firestore_database_id,
    )

    n = 0
    for doc in client.collection("api_keys").stream():
        d = doc.to_dict() or {}
        key_id = d.get("key_id") or doc.id
        conn.execute(
            """
            INSERT OR REPLACE INTO api_keys (key_id, name, key_hash, is_active, created_at)
            VALUES (?,?,?,?,?)
            """,
            (
                key_id,
                d.get("name") or "",
                d.get("key_hash") or "",
                1 if d.get("is_active") else 0,
                _iso(d.get("created_at")),
            ),
        )
        n += 1

    conn.commit()
    conn.close()
    print(f"OK: синхронизировано записей api_keys: {n} -> {sqlite_path}")


if __name__ == "__main__":
    main()
