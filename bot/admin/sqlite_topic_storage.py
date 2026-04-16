"""Хранилище топиков админки в SQLite (аналог FirestoreTopicStorage)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from loguru import logger

from bot.admin.topic_storage import BaseTopicStorage
from bot.database.sqlite_schema import SCHEMA_SQL, ensure_sqlite_parent_dir


class SqliteTopicStorage(BaseTopicStorage):
    """Коллекция adminpanel в одной таблице."""

    def __init__(self, sqlite_path: str) -> None:
        self._path = str(Path(sqlite_path).expanduser().resolve())
        ensure_sqlite_parent_dir(self._path)
        self._init_sync_schema()

    def _init_sync_schema(self) -> None:
        conn = sqlite3.connect(self._path)
        try:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
        finally:
            conn.close()

    def save_topic(self, user_id: int, topic_id: int, topic_name: str) -> None:
        uid = str(user_id)
        conn = sqlite3.connect(self._path)
        try:
            conn.execute(
                """
                INSERT INTO adminpanel (user_id, telegram_user_id, topic_id, topic_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    telegram_user_id = excluded.telegram_user_id,
                    topic_id = excluded.topic_id,
                    topic_name = excluded.topic_name
                """,
                (uid, user_id, topic_id, topic_name),
            )
            conn.commit()
        finally:
            conn.close()

    def get_topic_id(self, user_id: int) -> int | None:
        conn = sqlite3.connect(self._path)
        try:
            cur = conn.execute(
                "SELECT topic_id FROM adminpanel WHERE user_id = ?", (str(user_id),)
            )
            row = cur.fetchone()
            if not row or row[0] is None:
                return None
            return int(row[0])
        except Exception:
            return None
        finally:
            conn.close()

    def get_user_id(self, topic_id: int) -> int | None:
        conn = sqlite3.connect(self._path)
        try:
            cur = conn.execute(
                "SELECT telegram_user_id FROM adminpanel WHERE topic_id = ? LIMIT 1",
                (topic_id,),
            )
            row = cur.fetchone()
            if not row or row[0] is None:
                return None
            return int(row[0])
        except Exception as e:
            logger.error("Ошибка get_user_id topic_id=%s: %s", topic_id, e)
            return None
        finally:
            conn.close()
