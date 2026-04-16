"""Репозиторий пользователей/моделей/результатов на SQLite (аналог FirestoreRepo)."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import aiosqlite
from loguru import logger

from bot.core.config import Settings
from bot.database.models import PersonImage, TryOnResult
from bot.database.sqlite_schema import init_sqlite_schema


def _dt_to_iso(v: datetime | str | None) -> str | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)


def _iso_to_dt(s: str | datetime | None) -> datetime:
    if isinstance(s, datetime):
        return s
    if not s:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return datetime.utcnow()


class SqliteRepo:
    """Те же методы, что у FirestoreRepo, данные в SQLite."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._path = str(Path(settings.sqlite_path).expanduser().resolve())
        self._schema_ready = False

    async def _ensure_schema(self) -> None:
        if self._schema_ready:
            return
        await init_sqlite_schema(self._path)
        self._schema_ready = True

    async def add_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        await self._ensure_schema()
        doc_id = user_id or str(telegram_id)
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE id = ?", (doc_id,))
            row = await cur.fetchone()
            existing = dict(row) if row else None

            if existing:
                raw_ca = existing.get("created_at")
                if raw_ca:
                    if isinstance(raw_ca, str):
                        try:
                            created_at_value = datetime.fromisoformat(
                                raw_ca.replace("Z", "+00:00")
                            )
                        except (ValueError, AttributeError):
                            created_at_value = datetime.utcnow()
                    else:
                        created_at_value = datetime.utcnow()
                else:
                    created_at_value = datetime.utcnow()
                merged_lang = existing.get("language")
                merged_priv = int(existing.get("privacy_consent_accepted") or 0)
                merged_priv_at = existing.get("privacy_consent_at")
            else:
                created_at_value = datetime.utcnow()
                merged_lang = None
                merged_priv = 0
                merged_priv_at = None

            merged_username = (
                username if username is not None else (existing.get("username") if existing else None)
            )

            await db.execute(
                """
                INSERT INTO users (id, telegram_id, username, language, created_at, privacy_consent_accepted, privacy_consent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    telegram_id = excluded.telegram_id,
                    username = COALESCE(excluded.username, users.username),
                    language = COALESCE(users.language, excluded.language),
                    created_at = users.created_at,
                    privacy_consent_accepted = users.privacy_consent_accepted,
                    privacy_consent_at = users.privacy_consent_at
                """,
                (
                    doc_id,
                    telegram_id,
                    merged_username,
                    merged_lang,
                    _dt_to_iso(created_at_value),
                    merged_priv,
                    merged_priv_at,
                ),
            )
            await db.commit()
        logger.info(f"Пользователь {doc_id} добавлен/обновлён в SQLite")
        return doc_id

    async def get_user_language(self, user_id: str) -> Optional[str]:
        await self._ensure_schema()
        async with aiosqlite.connect(self._path) as db:
            cur = await db.execute(
                "SELECT language FROM users WHERE id = ?", (user_id,)
            )
            row = await cur.fetchone()
            return row[0] if row and row[0] is not None else None

    async def set_user_language(self, user_id: str, language: str) -> None:
        await self._ensure_schema()
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "UPDATE users SET language = ? WHERE id = ?", (language, user_id)
            )
            await db.commit()
        logger.info(f"Язык пользователя {user_id} установлен: {language}")

    async def get_privacy_consent_accepted(self, user_id: str) -> bool:
        await self._ensure_schema()
        async with aiosqlite.connect(self._path) as db:
            cur = await db.execute(
                "SELECT privacy_consent_accepted FROM users WHERE id = ?", (user_id,)
            )
            row = await cur.fetchone()
            if not row:
                return False
            return bool(row[0])

    async def get_user_language_and_privacy(
        self, user_id: str
    ) -> tuple[Optional[str], bool]:
        await self._ensure_schema()
        async with aiosqlite.connect(self._path) as db:
            cur = await db.execute(
                "SELECT language, privacy_consent_accepted FROM users WHERE id = ?",
                (user_id,),
            )
            row = await cur.fetchone()
            if not row:
                return None, False
            lang, priv = row[0], row[1]
            return lang, bool(priv)

    async def set_privacy_consent_accepted(self, user_id: str) -> None:
        await self._ensure_schema()
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                UPDATE users SET privacy_consent_accepted = 1, privacy_consent_at = ?
                WHERE id = ?
                """,
                (now, user_id),
            )
            await db.commit()
        logger.info(f"Согласие сохранено для пользователя {user_id}")

    async def add_model(
        self,
        user_id: str,
        gcs_uri: str,
        model_id: Optional[str] = None,
    ) -> str:
        await self._ensure_schema()
        if model_id is None:
            model_id = f"model_{int(datetime.utcnow().timestamp() * 1000)}"
        created = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO user_models (id, user_id, gcs_uri, is_active, created_at)
                VALUES (?, ?, ?, 0, ?)
                """,
                (model_id, user_id, gcs_uri, created),
            )
            await db.commit()
        logger.info(f"Модель {model_id} добавлена для пользователя {user_id}")
        return model_id

    async def get_user_models(self, user_id: str) -> list[PersonImage]:
        await self._ensure_schema()
        async with aiosqlite.connect(self._path) as db:
            cur = await db.execute(
                """
                SELECT id, user_id, gcs_uri, is_active, created_at FROM user_models
                WHERE user_id = ? ORDER BY created_at DESC
                """,
                (user_id,),
            )
            rows = await cur.fetchall()
        models: list[PersonImage] = []
        for r in rows:
            models.append(
                PersonImage(
                    id=r[0],
                    user_id=r[1],
                    gcs_uri=r[2],
                    is_active=bool(r[3]),
                    created_at=_iso_to_dt(r[4]),
                )
            )
        logger.info(f"Найдено {len(models)} моделей для пользователя {user_id}")
        return models

    async def delete_model(self, user_id: str, model_id: str) -> None:
        await self._ensure_schema()
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "DELETE FROM user_models WHERE user_id = ? AND id = ?",
                (user_id, model_id),
            )
            await db.commit()
        logger.info(f"Модель {model_id} удалена для пользователя {user_id}")

    async def add_final_result(
        self,
        user_id: str,
        gcs_uri: str,
        model_gcs_uri: Optional[str] = None,
        result_id: Optional[str] = None,
    ) -> str:
        await self._ensure_schema()
        if result_id is None:
            unique_suffix = str(uuid.uuid4())[:8]
            timestamp = int(datetime.utcnow().timestamp() * 1000)
            result_id = f"result_{timestamp}_{unique_suffix}"
        created = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO final_results (id, user_id, gcs_uri, model_gcs_uri, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (result_id, user_id, gcs_uri, model_gcs_uri, created),
            )
            await db.commit()
        logger.info(f"Финальный результат {result_id} добавлен для пользователя {user_id}")
        return result_id

    async def get_user_final_results(self, user_id: str) -> list[TryOnResult]:
        await self._ensure_schema()
        async with aiosqlite.connect(self._path) as db:
            cur = await db.execute(
                """
                SELECT id, user_id, gcs_uri, model_gcs_uri, created_at FROM final_results
                WHERE user_id = ? ORDER BY created_at DESC
                """,
                (user_id,),
            )
            rows = await cur.fetchall()
        results: list[TryOnResult] = []
        for r in rows:
            results.append(
                TryOnResult(
                    id=r[0],
                    user_id=r[1],
                    gcs_uri=r[2],
                    model_gcs_uri=r[3],
                    created_at=_iso_to_dt(r[4]),
                )
            )
        logger.info(f"Найдено {len(results)} финальных результатов для пользователя {user_id}")
        return results

    async def get_final_result(
        self, user_id: str, result_id: str
    ) -> Optional[TryOnResult]:
        await self._ensure_schema()
        async with aiosqlite.connect(self._path) as db:
            cur = await db.execute(
                """
                SELECT id, user_id, gcs_uri, model_gcs_uri, created_at FROM final_results
                WHERE user_id = ? AND id = ?
                """,
                (user_id, result_id),
            )
            r = await cur.fetchone()
        if not r:
            return None
        return TryOnResult(
            id=r[0],
            user_id=r[1],
            gcs_uri=r[2],
            model_gcs_uri=r[3],
            created_at=_iso_to_dt(r[4]),
        )

    async def delete_all_user_final_results(self, user_id: str) -> List[str]:
        await self._ensure_schema()
        async with aiosqlite.connect(self._path) as db:
            cur = await db.execute(
                "SELECT gcs_uri FROM final_results WHERE user_id = ?", (user_id,)
            )
            rows = await cur.fetchall()
            gcs_uris = [row[0] for row in rows if row[0]]
            await db.execute("DELETE FROM final_results WHERE user_id = ?", (user_id,))
            await db.commit()
        logger.info(f"Удалено {len(gcs_uris)} финальных результатов из SQLite для {user_id}")
        return gcs_uris

    async def close(self) -> None:
        logger.info("SQLite repo: close (no persistent pool)")

