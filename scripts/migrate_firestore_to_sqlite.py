#!/usr/bin/env python3
"""Перенос данных Firestore -> SQLite (как в проде). Запуск из корня репозитория:

  python scripts/migrate_firestore_to_sqlite.py

Нужны: рабочие ADC / GOOGLE_APPLICATION_CREDENTIALS, .env с GCP и FIRESTORE_DATABASE_ID.
После переноса выставь DATABASE_BACKEND=sqlite и SQLITE_PATH к этому же файлу.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
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
    sqlite_path = Path(settings.sqlite_path).expanduser().resolve()
    ensure_sqlite_parent_dir(str(sqlite_path))

    conn = sqlite3.connect(str(sqlite_path))
    conn.executescript(SCHEMA_SQL)
    conn.commit()

    client = firestore.Client(
        project=settings.google_cloud_project_id,
        database=settings.firestore_database_id,
    )

    for doc in client.collection("users").stream():
        data = doc.to_dict() or {}
        uid = doc.id
        conn.execute(
            """
            INSERT OR REPLACE INTO users (id, telegram_id, username, language, created_at, privacy_consent_accepted, privacy_consent_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                uid,
                int(data.get("telegram_id") or 0),
                data.get("username"),
                data.get("language"),
                _iso(data.get("created_at")),
                1 if data.get("privacy_consent_accepted") else 0,
                _iso(data.get("privacy_consent_at")),
            ),
        )
        for m in doc.reference.collection("models").stream():
            md = m.to_dict() or {}
            conn.execute(
                """
                INSERT OR REPLACE INTO user_models (id, user_id, gcs_uri, is_active, created_at)
                VALUES (?,?,?,?,?)
                """,
                (
                    m.id,
                    uid,
                    md.get("gcs_uri") or "",
                    int(md.get("is_active") or 0),
                    _iso(md.get("created_at")) or datetime.utcnow().isoformat(),
                ),
            )
        for fr in doc.reference.collection("final_results").stream():
            fd = fr.to_dict() or {}
            conn.execute(
                """
                INSERT OR REPLACE INTO final_results (id, user_id, gcs_uri, model_gcs_uri, created_at)
                VALUES (?,?,?,?,?)
                """,
                (
                    fr.id,
                    uid,
                    fd.get("gcs_uri") or "",
                    fd.get("model_gcs_uri"),
                    _iso(fd.get("created_at")) or datetime.utcnow().isoformat(),
                ),
            )

    for doc in client.collection("api_tasks").stream():
        d = doc.to_dict() or {}
        uris = d.get("result_uris") or []
        if isinstance(uris, list):
            uris_json = json.dumps(uris)
        else:
            uris_json = uris if isinstance(uris, str) else json.dumps([])
        conn.execute(
            """
            INSERT OR REPLACE INTO api_tasks (task_id, status, garments_count, created_at, completed_at, result_uris, model_temp_uri, error, expires_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                doc.id,
                d.get("status"),
                d.get("garments_count"),
                _iso(d.get("created_at")),
                _iso(d.get("completed_at")),
                uris_json,
                d.get("model_temp_uri"),
                d.get("error"),
                _iso(d.get("expires_at")),
            ),
        )

    for doc in client.collection("api_keys").stream():
        d = doc.to_dict() or {}
        conn.execute(
            """
            INSERT OR REPLACE INTO api_keys (key_id, name, key_hash, is_active, created_at)
            VALUES (?,?,?,?,?)
            """,
            (
                doc.id,
                d.get("name"),
                d.get("key_hash"),
                1 if d.get("is_active") else 0,
                _iso(d.get("created_at")),
            ),
        )

    for doc in client.collection("adminpanel").stream():
        d = doc.to_dict() or {}
        tid = d.get("user_id")
        if tid is None:
            try:
                tid = int(doc.id)
            except ValueError:
                tid = 0
        conn.execute(
            """
            INSERT OR REPLACE INTO adminpanel (user_id, telegram_user_id, topic_id, topic_name)
            VALUES (?,?,?,?)
            """,
            (
                doc.id,
                int(tid),
                int(d.get("topic_id") or 0),
                d.get("topic_name") or "",
            ),
        )

    conn.commit()
    conn.close()
    print(f"OK: данные перенесены в {sqlite_path}")


if __name__ == "__main__":
    main()
