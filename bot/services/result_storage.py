"""Сервис для сохранения финальных результатов примерки."""

import asyncio
import uuid
from typing import List, Optional
from datetime import datetime

from loguru import logger

from bot.services.storage import CloudStorageService
from bot.database.repo_factory import UserRepository


class ResultStorageService:
    """Сервис для сохранения финальных результатов примерки в облако и БД."""

    def __init__(
        self,
        storage_service: CloudStorageService,
        repo: UserRepository,
    ):
        """
        Инициализировать сервис.

        Args:
            storage_service: Сервис для работы с облачным хранилищем
            repo: Репозиторий для работы с БД
        """
        self.storage_service = storage_service
        self.repo = repo

    async def save_result(
        self,
        user_id: str,
        result_bytes: bytes,
        model_gcs_uri: Optional[str] = None,
        result_id: Optional[str] = None,
    ) -> str:
        """
        Сохранить один результат примерки в облако и БД.

        Args:
            user_id: ID пользователя
            result_bytes: Байты изображения результата
            model_gcs_uri: URI модели, использованной для примерки (опционально)
            result_id: Кастомный ID результата (если не указан, генерируется автоматически)

        Returns:
            ID результата в Firestore
        """
        if result_id is None:
            # Генерируем уникальный ID с использованием UUID для избежания коллизий при параллельном сохранении
            unique_suffix = str(uuid.uuid4())[:8]
            timestamp = int(datetime.utcnow().timestamp() * 1000)
            result_id = f"result_{timestamp}_{unique_suffix}"

        # Путь в облаке: final_results/{user_id}/{result_id}.png
        destination_path = f"final_results/{user_id}/{result_id}.png"

        try:
            # Загружаем в облако
            gcs_uri = await self.storage_service.upload_image(
                file_bytes=result_bytes,
                destination_path=destination_path,
            )
            logger.info(f"Результат загружен в облако: {gcs_uri}")

            # Сохраняем в БД
            await self.repo.add_final_result(
                user_id=user_id,
                gcs_uri=gcs_uri,
                model_gcs_uri=model_gcs_uri,
                result_id=result_id,
            )
            logger.info(f"Результат сохранен в БД: {result_id}")

            return result_id

        except Exception as e:
            logger.error(f"Ошибка при сохранении результата: {e}")
            raise

    async def save_results_batch(
        self,
        user_id: str,
        results: List[bytes],
        model_gcs_uri: Optional[str] = None,
    ) -> List[str]:
        """
        Сохранить несколько результатов примерки параллельно.

        Args:
            user_id: ID пользователя
            results: Список байтов изображений результатов
            model_gcs_uri: URI модели, использованной для примерки (опционально)

        Returns:
            Список ID результатов в Firestore
        """
        tasks = [
            self.save_result(
                user_id=user_id,
                result_bytes=result_bytes,
                model_gcs_uri=model_gcs_uri,
            )
            for result_bytes in results
        ]

        result_ids = await asyncio.gather(*tasks, return_exceptions=True)

        # Фильтруем успешные результаты
        successful_ids = []
        for idx, result_id in enumerate(result_ids):
            if isinstance(result_id, Exception):
                logger.error(f"Ошибка при сохранении результата {idx + 1}: {result_id}")
            else:
                successful_ids.append(result_id)

        return successful_ids
