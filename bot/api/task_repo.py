"""Firestore-репозиторий для API-задач и ключей."""
import uuid
import warnings
from datetime import datetime, timedelta
from typing import Optional

RESULT_TTL_HOURS = 1

from google.cloud.firestore_v1 import AsyncClient
from loguru import logger

from bot.api.schemas import TaskStatus
from bot.core.config import Settings

warnings.filterwarnings(
    "ignore",
    message=".*synchronous google.api_core.retry.Retry with asynchronous calls.*",
    category=UserWarning,
)

_TASKS = "api_tasks"
_KEYS = "api_keys"


class ApiTaskRepo:
    """CRUD-операции для коллекций api_tasks и api_keys в Firestore."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Optional[AsyncClient] = None

    def _get_client(self) -> AsyncClient:
        if self._client is None:
            self._client = AsyncClient(
                project=self._settings.google_cloud_project_id,
                database=self._settings.firestore_database_id,
            )
        return self._client

    # ------------------------------------------------------------------ #
    # Tasks
    # ------------------------------------------------------------------ #

    async def create_task(self, garments_count: int) -> str:
        """Создать задачу со статусом pending. Возвращает task_id."""
        task_id = str(uuid.uuid4())
        await self._get_client().collection(_TASKS).document(task_id).set(
            {
                "task_id": task_id,
                "status": TaskStatus.PENDING.value,
                "garments_count": garments_count,
                "created_at": datetime.utcnow(),
                "completed_at": None,
                "result_uris": [],
                "model_temp_uri": None,
                "error": None,
            }
        )
        logger.info(f"API задача создана: {task_id} ({garments_count} гарментов)")
        return task_id

    async def set_processing(self, task_id: str, model_temp_uri: str) -> None:
        await self._get_client().collection(_TASKS).document(task_id).update(
            {
                "status": TaskStatus.PROCESSING.value,
                "model_temp_uri": model_temp_uri,
            }
        )

    async def set_completed(self, task_id: str, result_uris: list[str]) -> None:
        expires_at = datetime.utcnow() + timedelta(hours=RESULT_TTL_HOURS)
        await self._get_client().collection(_TASKS).document(task_id).update(
            {
                "status": TaskStatus.COMPLETED.value,
                "completed_at": datetime.utcnow(),
                "result_uris": result_uris,
                "expires_at": expires_at,
            }
        )
        logger.info(f"Задача {task_id} завершена, результатов: {len(result_uris)}, истекает: {expires_at.isoformat()}")

    async def set_failed(self, task_id: str, error: str) -> None:
        await self._get_client().collection(_TASKS).document(task_id).update(
            {
                "status": TaskStatus.FAILED.value,
                "completed_at": datetime.utcnow(),
                "error": error,
            }
        )
        logger.error(f"Задача {task_id} провалилась: {error}")

    async def get_task(self, task_id: str) -> Optional[dict]:
        doc = await self._get_client().collection(_TASKS).document(task_id).get()
        return doc.to_dict() if doc.exists else None

    # ------------------------------------------------------------------ #
    # API Keys
    # ------------------------------------------------------------------ #

    async def is_key_active(self, key_hash: str) -> bool:
        """Проверить, активен ли ключ по его SHA-256 хэшу."""
        query = (
            self._get_client()
            .collection(_KEYS)
            .where("key_hash", "==", key_hash)
            .where("is_active", "==", True)
            .limit(1)
        )
        results = [doc async for doc in query.stream()]
        return len(results) > 0

    async def create_key(self, name: str, key_hash: str) -> str:
        """Сохранить новый ключ (только хэш). Возвращает ID записи."""
        key_id = str(uuid.uuid4())
        await self._get_client().collection(_KEYS).document(key_id).set(
            {
                "key_id": key_id,
                "name": name,
                "key_hash": key_hash,
                "is_active": True,
                "created_at": datetime.utcnow(),
            }
        )
        logger.info(f"Создан API ключ: name={name}, id={key_id}")
        return key_id

    async def revoke_key(self, name: str) -> bool:
        """Отозвать ключ по имени. Возвращает True, если ключ был найден."""
        query = (
            self._get_client()
            .collection(_KEYS)
            .where("name", "==", name)
            .where("is_active", "==", True)
        )
        found = False
        async for doc in query.stream():
            await doc.reference.update({"is_active": False})
            found = True
            logger.info(f"Ключ '{name}' отозван")
        return found

    async def list_keys(self) -> list[dict]:
        """Список всех ключей (без хэшей)."""
        keys = []
        async for doc in self._get_client().collection(_KEYS).stream():
            data = doc.to_dict()
            if data:
                keys.append(
                    {
                        "key_id": data.get("key_id"),
                        "name": data.get("name"),
                        "is_active": data.get("is_active"),
                        "created_at": data.get("created_at"),
                    }
                )
        return keys
