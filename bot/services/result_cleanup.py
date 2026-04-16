"""Сервис для очистки результатов примерки."""

import asyncio
from typing import List

from loguru import logger

from bot.services.storage import CloudStorageService
from bot.database.repo_factory import UserRepository


async def cleanup_user_results(
    user_id: str,
    repo: UserRepository,
    storage_service: CloudStorageService,
) -> None:
    """
    Удалить все результаты пользователя из облака и Firestore в фоне.

    Args:
        user_id: ID пользователя
        repo: Репозиторий для работы с БД
        storage_service: Сервис для работы с облачным хранилищем
    """
    try:
        # Получаем все URI результатов из Firestore перед удалением
        gcs_uris = await repo.delete_all_user_final_results(user_id)
        
        # Удаляем файлы из облака параллельно
        if gcs_uris:
            delete_tasks = [
                storage_service.delete_file(gcs_uri)
                for gcs_uri in gcs_uris
            ]
            await asyncio.gather(*delete_tasks, return_exceptions=True)
            logger.info(f"Удалено {len(gcs_uris)} файлов из облака для пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при очистке результатов пользователя {user_id}: {e}", exc_info=True)
