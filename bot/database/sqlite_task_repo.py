"""SQLite-репозиторий api_tasks / api_keys (аналог ApiTaskRepo)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import aiosqlite
from loguru import logger

from bot.api.schemas import TaskStatus
from bot.core.config import Settings
from bot.database.sqlite_schema import init_sqlite_schema

RESULT_TTL_HOURS = 1


def _parse_dt(val: str | datetime | None) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except ValueError:
        return None


class SqliteApiTaskRepo:
    """Те же методы, что у ApiTaskRepo."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._path = str(Path(settings.sqlite_path).expanduser().resolve())
        self._schema_ready = False

    async def _ensure(self) -> None:
        if self._schema_ready:
            return
        await init_sqlite_schema(self._path)
        self._schema_ready = True

    async def create_task(self, garments_count: int) -> str:
        await self._ensure()
        task_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                INSERT INTO api_tasks (task_id, status, garments_count, created_at, completed_at, result_uris, model_temp_uri, error, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    TaskStatus.PENDING.value,
                    garments_count,
                    now,
                    None,
                    json.dumps([]),
                    None,
                    None,
                    None,
                ),
            )
            await db.commit()
        logger.info(f"API задача создана: {task_id} ({garments_count} гарментов)")
        return task_id

    async def set_processing(self, task_id: str, model_temp_uri: str) -> None:
        await self._ensure()
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                UPDATE api_tasks SET status = ?, model_temp_uri = ? WHERE task_id = ?
                """,
                (TaskStatus.PROCESSING.value, model_temp_uri, task_id),
            )
            await db.commit()

    async def set_completed(self, task_id: str, result_uris: list[str]) -> None:
        await self._ensure()
        expires_at = datetime.utcnow() + timedelta(hours=RESULT_TTL_HOURS)
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                UPDATE api_tasks SET status = ?, completed_at = ?, result_uris = ?, expires_at = ?
                WHERE task_id = ?
                """,
                (
                    TaskStatus.COMPLETED.value,
                    now,
                    json.dumps(result_uris),
                    expires_at.isoformat(),
                    task_id,
                ),
            )
            await db.commit()
        logger.info(
            f"Задача {task_id} завершена, результатов: {len(result_uris)}, истекает: {expires_at.isoformat()}"
        )

    async def set_failed(self, task_id: str, error: str) -> None:
        await self._ensure()
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                UPDATE api_tasks SET status = ?, completed_at = ?, error = ? WHERE task_id = ?
                """,
                (TaskStatus.FAILED.value, now, error, task_id),
            )
            await db.commit()
        logger.error(f"Задача {task_id} провалилась: {error}")

    async def get_task(self, task_id: str) -> Optional[dict]:
        await self._ensure()
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM api_tasks WHERE task_id = ?", (task_id,))
            row = await cur.fetchone()
        if not row:
            return None
        d = dict(row)
        uris = d.get("result_uris")
        if isinstance(uris, str):
            try:
                d["result_uris"] = json.loads(uris) if uris else []
            except json.JSONDecodeError:
                d["result_uris"] = []
        d["created_at"] = _parse_dt(d.get("created_at")) or datetime.utcnow()
        d["completed_at"] = _parse_dt(d.get("completed_at"))
        d["expires_at"] = _parse_dt(d.get("expires_at"))
        return d

    async def is_key_active(self, key_hash: str) -> bool:
        await self._ensure()
        async with aiosqlite.connect(self._path) as db:
            cur = await db.execute(
                """
                SELECT 1 FROM api_keys WHERE key_hash = ? AND is_active = 1 LIMIT 1
                """,
                (key_hash,),
            )
            row = await cur.fetchone()
        return row is not None

    async def create_key(self, name: str, key_hash: str) -> str:
        await self._ensure()
        key_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                INSERT INTO api_keys (key_id, name, key_hash, is_active, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (key_id, name, key_hash, now),
            )
            await db.commit()
        logger.info(f"Создан API ключ: name={name}, id={key_id}")
        return key_id

    async def revoke_key(self, name: str) -> bool:
        await self._ensure()
        async with aiosqlite.connect(self._path) as db:
            cur = await db.execute(
                "SELECT key_id FROM api_keys WHERE name = ? AND is_active = 1",
                (name,),
            )
            found = await cur.fetchone() is not None
            if found:
                await db.execute(
                    "UPDATE api_keys SET is_active = 0 WHERE name = ? AND is_active = 1",
                    (name,),
                )
            await db.commit()
        if found:
            logger.info(f"Ключ '{name}' отозван")
        return found

    async def list_keys(self) -> list[dict]:
        await self._ensure()
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT key_id, name, is_active, created_at FROM api_keys"
            )
            rows = await cur.fetchall()
        keys = []
        for row in rows:
            d = dict(row)
            ca = d.get("created_at")
            d["created_at"] = _parse_dt(ca) if ca else None
            keys.append(
                {
                    "key_id": d.get("key_id"),
                    "name": d.get("name"),
                    "is_active": d.get("is_active"),
                    "created_at": d["created_at"],
                }
            )
        return keys
