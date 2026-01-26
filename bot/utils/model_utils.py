"""Утилиты для работы с моделями."""

from datetime import datetime
from typing import List, Optional

from aiogram import Bot
from aiogram.types import InputMediaPhoto, BufferedInputFile
from loguru import logger

from bot.database.models import PersonImage
from bot.services.storage import CloudStorageService


async def prepare_models_media_group(
    models: List[PersonImage],
    storage_service: CloudStorageService,
) -> List[InputMediaPhoto]:
    """
    Подготовить медиа-группу из моделей для отправки альбомом.

    Args:
        models: Список моделей
        storage_service: Сервис для работы с GCS

    Returns:
        Список InputMediaPhoto для альбома
    """
    media_group = []
    for idx, model in enumerate(models):
        try:
            photo_bytes = await storage_service.download_file(model.gcs_uri)
            photo_file = BufferedInputFile(
                file=photo_bytes,
                filename=f"model_{idx + 1}.jpg",
            )
            media_group.append(InputMediaPhoto(media=photo_file, caption=None))
        except Exception as e:
            logger.error(f"Ошибка при загрузке фото модели {idx + 1}: {e}")
    
    return media_group


async def process_model_photo(
    bot: Bot,
    photo_bytes: bytes,
    user_id: str,
    repo,
    storage_service: CloudStorageService,
) -> tuple[str, str]:
    """
    Обработать фото модели: загрузить в GCS и сохранить в БД.

    Args:
        bot: Экземпляр бота (не используется, но оставлен для совместимости)
        photo_bytes: Байты фото
        user_id: ID пользователя
        repo: Репозиторий для работы с БД
        storage_service: Сервис для работы с GCS

    Returns:
        Кортеж (model_id, gcs_uri)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination_path = f"bot_uploads/models/{user_id}_{timestamp}.jpg"
    
    logger.info(f"Сохранение фото модели в Cloud Storage: {destination_path}")
    gcs_uri = await storage_service.upload_image(
        file_bytes=photo_bytes,
        destination_path=destination_path,
    )
    logger.info(f"Фото модели сохранено: {gcs_uri}")
    
    model_id = await repo.add_model(
        user_id=user_id,
        gcs_uri=gcs_uri,
    )
    logger.info(f"Модель {model_id} сохранена в БД")
    
    return model_id, gcs_uri
