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
            logger.error("❌ GOOGLE_CLOUD_PROJECT не найден в переменных окружения")
            logger.debug(f"🔍 Доступные переменные с 'GOOGLE' или 'PROJECT': {[k for k in os.environ.keys() if 'GOOGLE' in k.upper() or 'PROJECT' in k.upper()]}")
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT должен быть установлен для использования FirestoreTopicStorage. "
                "Проверьте переменные окружения: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_PROJECT_ID"
            )
        
        logger.info(f"✅ GOOGLE_CLOUD_PROJECT найден: {project_id}")
        
        # Используем ту же логику, что и в основном проекте
        # Проверяем все возможные варианты имени переменной для database_id
        if database_id is None:
            database_id = (
                os.getenv("FIRESTORE_DATABASE_ID") or
                os.getenv("FIRESTORE_DATABASE") or
                os.getenv("firestore_database_id")
            )
            # Если не найдено, пытаемся получить из Settings
            if not database_id:
                try:
                    from bot.core.config import get_settings
                    settings = get_settings()
                    database_id = settings.firestore_database_id
                    logger.info(f"✅ FIRESTORE_DATABASE_ID получен из Settings: {database_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось получить database_id из Settings: {e}, используем '(default)'")
                    database_id = "(default)"
            else:
                logger.info(f"✅ FIRESTORE_DATABASE_ID найден в переменных окружения: {database_id}")
        else:
            logger.info(f"✅ FIRESTORE_DATABASE_ID передан напрямую: {database_id}")
        
        collection_name = collection_name or "adminpanel"
        
        self.client = firestore.Client(project=project_id, database=database_id)
        self.collection = self.client.collection(collection_name)
        
        logger.info(
            f"✅ Инициализирован FirestoreTopicStorage (project={project_id}, database={database_id}, collection={collection_name})"
        )

    def save_topic(self, user_id: int, topic_id: int, topic_name: str) -> None:
        """
        Сохраняет связь между пользователем и топиком.
        
        Args:
            user_id: ID пользователя Telegram
            topic_id: ID топика в Telegram Forum
            topic_name: Название топика
        """
        try:
            logger.info(f"💾 Сохранение связи в Firestore: user_id={user_id} -> topic_id={topic_id} ({topic_name})")
            doc_ref = self.collection.document(str(user_id))
            doc_ref.set({
                "user_id": user_id,
                "topic_id": topic_id,
                "topic_name": topic_name,
            }, merge=True)
            
            logger.success(
                f"✅ Связь сохранена в Firestore: user_id={user_id} -> topic_id={topic_id} ({topic_name})"
            )
        except Exception as e:
            logger.error(
                f"❌ Ошибка при сохранении связи user_id={user_id} -> topic_id={topic_id}: {e}",
                exc_info=True
            )
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
            logger.debug(f"🔍 Поиск topic_id для user_id={user_id} в Firestore...")
            doc_ref = self.collection.document(str(user_id))
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.info(f"ℹ️ Топик для user_id={user_id} не найден в Firestore")
                return None
            
            data = doc.to_dict()
            topic_id = data.get("topic_id")
            
            if topic_id is not None:
                result = int(topic_id)
                logger.success(f"✅ Найден topic_id={result} для user_id={user_id}")
                return result
            else:
                logger.warning(f"⚠️ Документ для user_id={user_id} существует, но topic_id отсутствует")
                return None
        except Exception as e:
            logger.error(
                f"❌ Ошибка при получении topic_id для user_id={user_id}: {e}",
                exc_info=True
            )
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
