"""Фабрика для создания экземпляра хранилища топиков."""

import os
from loguru import logger

from bot.admin.firestore_topic_storage import FirestoreTopicStorage
from bot.admin.topic_storage import BaseTopicStorage

# Глобальный экземпляр хранилища
_topic_storage: BaseTopicStorage | None = None


def get_topic_storage() -> BaseTopicStorage:
    """
    Получает или создает экземпляр хранилища топиков.
    
    Returns:
        Экземпляр хранилища топиков (по умолчанию FirestoreTopicStorage)
    """
    global _topic_storage
    
    if _topic_storage is None:
        logger.info("🔧 Инициализация хранилища топиков...")
        try:
            _topic_storage = FirestoreTopicStorage()
            logger.success("✅ FirestoreTopicStorage успешно инициализирован")
        except ValueError as e:
            logger.error(
                f"❌ Не удалось инициализировать FirestoreTopicStorage: {e}. "
                "Убедитесь, что GOOGLE_CLOUD_PROJECT установлен."
            )
            raise
        except Exception as e:
            logger.error(
                f"❌ Ошибка при инициализации хранилища топиков: {e}",
                exc_info=True
            )
            raise
    
    return _topic_storage
