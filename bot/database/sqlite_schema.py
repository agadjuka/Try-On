"""Создание таблиц SQLite (аналог коллекций Firestore)."""

import os
from pathlib import Path

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    telegram_id INTEGER NOT NULL,
    username TEXT,
    language TEXT,
    created_at TEXT,
    privacy_consent_accepted INTEGER NOT NULL DEFAULT 0,
    privacy_consent_at TEXT
);

CREATE TABLE IF NOT EXISTS user_models (
    id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    gcs_uri TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS final_results (
    id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    gcs_uri TEXT NOT NULL,
    model_gcs_uri TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS api_tasks (
    task_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    garments_count INTEGER,
    created_at TEXT,
    completed_at TEXT,
    result_uris TEXT,
    model_temp_uri TEXT,
    error TEXT,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS api_keys (
    key_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash_active ON api_keys(key_hash, is_active);
CREATE INDEX IF NOT EXISTS idx_api_keys_name_active ON api_keys(name, is_active);

CREATE TABLE IF NOT EXISTS adminpanel (
    user_id TEXT PRIMARY KEY,
    telegram_user_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    topic_name TEXT
);

CREATE INDEX IF NOT EXISTS idx_adminpanel_topic ON adminpanel(topic_id);
"""


def ensure_sqlite_parent_dir(sqlite_path: str) -> None:
    Path(sqlite_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


async def init_sqlite_schema(sqlite_path: str) -> None:
    """Создать файл БД и таблицы, если их ещё нет."""
    import aiosqlite

    ensure_sqlite_parent_dir(sqlite_path)
    path = str(Path(sqlite_path).expanduser().resolve())
    async with aiosqlite.connect(path) as db:
        await db.executescript(SCHEMA_SQL)
        await db.commit()
