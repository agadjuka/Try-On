"""Реализация хранилища топиков на базе Firestore."""

import os
from typing import Optional

from dotenv import load_dotenv
from google.cloud import firestore
from loguru import logger

from bot.admin.topic_storage import BaseTopicStorage

# Загружаем переменные окружения из .env файла
load_dotenv()


class FirestoreTopicStorage(BaseTopicStorage):
    """
    Реализация хранилища топиков на базе Firestore.
    
    Структура хранения:
    - Коллекция: adminpanel
    - Документ: {user_id} - содержит topic_id и topic_name
    - Индекс: по topic_id для обратного поиска (через запрос)
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        database_id: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        """
        Инициализирует хранилище топиков в Firestore.
        
        Args:
            project_id: ID проекта GCP (если None, берется из GOOGLE_CLOUD_PROJECT)
            database_id: ID базы данных Firestore (если None, берется из FIRESTORE_DATABASE или "(default)")
            collection_name: Название коллекции (если None, используется "adminpanel")
        """
        # Проверяем все возможные варианты имени переменной
        project_id = (
            project_id or 
            os.getenv("GOOGLE_CLOUD_PROJECT") or 
            os.getenv("GOOGLE_CLOUD_PROJECT_ID") or
            os.getenv("google_cloud_project_id")
        )
        
        if not project_id:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT должен быть установлен для использования FirestoreTopicStorage"
            )
        
        if database_id is None:
            database_id = (
                os.getenv("FIRESTORE_DATABASE_ID") or
                os.getenv("FIRESTORE_DATABASE") or
                os.getenv("firestore_database_id")
            )
            if not database_id:
                try:
                    from bot.core.config import get_settings
                    settings = get_settings()
                    database_id = settings.firestore_database_id
                except Exception:
                    database_id = "(default)"
        
        collection_name = collection_name or "adminpanel"
        
        self.client = firestore.Client(project=project_id, database=database_id)
        self.collection = self.client.collection(collection_name)

    def save_topic(self, user_id: int, topic_id: int, topic_name: str) -> None:
        """
        Сохраняет связь между пользователем и топиком.
        
        Args:
            user_id: ID пользователя Telegram
            topic_id: ID топика в Telegram Forum
            topic_name: Название топика
        """
        try:
            doc_ref = self.collection.document(str(user_id))
            doc_ref.set({
                "user_id": user_id,
                "topic_id": topic_id,
                "topic_name": topic_name,
            }, merge=True)
        except Exception as e:
            raise

    def get_topic_id(self, user_id: int) -> int | None:
        """
        Получает ID топика по ID пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            ID топика или None, если связь не найдена
        """
        try:
            doc_ref = self.collection.document(str(user_id))
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            topic_id = data.get("topic_id")
            
            return int(topic_id) if topic_id is not None else None
        except Exception:
            return None

    def get_user_id(self, topic_id: int) -> int | None:
        """
        Получает ID пользователя по ID топика (обратная связь).
        
        Args:
            topic_id: ID топика в Telegram Forum
            
        Returns:
            ID пользователя или None, если связь не найдена
        """
        try:
            # Используем запрос для поиска по topic_id
            query = self.collection.where("topic_id", "==", topic_id).limit(1)
            docs = list(query.stream())
            
            if not docs:
                return None
            
            doc = docs[0]
            data = doc.to_dict()
            user_id = data.get("user_id")
            
            return int(user_id) if user_id is not None else None
        except Exception as e:
            logger.error(
                "Ошибка при получении user_id для topic_id=%s: %s",
                topic_id,
                str(e),
            )
            return None
