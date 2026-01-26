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
        try:
            _topic_storage = FirestoreTopicStorage()
        except Exception as e:
            logger.error(f"Ошибка инициализации хранилища топиков: {e}")
            raise
    
    return _topic_storage
