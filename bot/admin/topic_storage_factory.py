"""Фабрика для создания экземпляра хранилища топиков."""

from loguru import logger

from bot.admin.firestore_topic_storage import FirestoreTopicStorage
from bot.admin.sqlite_topic_storage import SqliteTopicStorage
from bot.admin.topic_storage import BaseTopicStorage

# Глобальный экземпляр хранилища
_topic_storage: BaseTopicStorage | None = None


def get_topic_storage() -> BaseTopicStorage:
    """
    Получает или создает экземпляр хранилища топиков.
    
    Returns:
        Firestore или SQLite в зависимости от DATABASE_BACKEND
    """
    global _topic_storage
    
    if _topic_storage is None:
        try:
            from bot.core.config import get_settings

            settings = get_settings()
            if settings.database_backend == "sqlite":
                _topic_storage = SqliteTopicStorage(settings.sqlite_path)
            else:
                _topic_storage = FirestoreTopicStorage()
        except Exception as e:
            logger.error(f"Ошибка инициализации хранилища топиков: {e}")
            raise
    
    return _topic_storage
