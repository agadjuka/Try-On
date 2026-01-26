"""Репозиторий для работы с Firestore."""

import warnings
from datetime import datetime
from typing import Optional

from google.cloud.firestore_v1 import AsyncClient
from google.auth.exceptions import DefaultCredentialsError
from loguru import logger

from bot.core.config import Settings
from bot.database.models import PersonImage, UserModel

# Подавляем предупреждение о синхронном Retry с асинхронными вызовами
# AsyncClient не поддерживает retry в конструкторе, используется дефолтный retry
warnings.filterwarnings(
    "ignore",
    message=".*synchronous google.api_core.retry.Retry with asynchronous calls.*",
    category=UserWarning
)


class FirestoreRepo:
    """Репозиторий для асинхронной работы с Firestore через ADC."""

    def __init__(self, settings: Settings):
        """
        Инициализировать репозиторий.

        Args:
            settings: Настройки приложения с параметрами Google Cloud
        """
        self.settings = settings
        self._client: Optional[AsyncClient] = None

    def _get_client(self) -> AsyncClient:
        """
        Получить асинхронный клиент Firestore через Application Default Credentials.

        Returns:
            Асинхронный клиент Firestore

        Raises:
            DefaultCredentialsError: Если не найдены учетные данные ADC
        """
        if self._client is None:
            try:
                self._client = AsyncClient(
                    project=self.settings.google_cloud_project_id,
                    database=self.settings.firestore_database_id
                )
            except DefaultCredentialsError as e:
                raise DefaultCredentialsError(
                    "Не найдены учетные данные Google Cloud. "
                    "Выполните: gcloud auth application-default login"
                ) from e
        return self._client

    async def add_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Добавить или обновить пользователя в Firestore.

        Args:
            telegram_id: ID пользователя в Telegram
            username: Username пользователя (опционально)
            user_id: Кастомный ID пользователя (если не указан, используется telegram_id как строка)

        Returns:
            ID пользователя в Firestore
        """
        client = self._get_client()
        doc_id = user_id or str(telegram_id)

        user_data = UserModel(
            id=doc_id,
            telegram_id=telegram_id,
            username=username,
            created_at=datetime.utcnow(),
        )

        doc_ref = client.collection("users").document(doc_id)
        await doc_ref.set(user_data.model_dump(), merge=True)

        logger.info(f"Пользователь {doc_id} добавлен/обновлен в Firestore")
        return doc_id

    async def add_model(
        self,
        user_id: str,
        gcs_uri: str,
        model_id: Optional[str] = None,
    ) -> str:
        """
        Добавить модель пользователя в подколлекцию users/{user_id}/models.

        Args:
            user_id: ID пользователя
            gcs_uri: URI изображения модели в GCS (gs://...)
            model_id: Кастомный ID модели (если не указан, генерируется автоматически)

        Returns:
            ID модели в Firestore
        """
        client = self._get_client()

        if model_id is None:
            # Генерируем ID на основе timestamp
            model_id = f"model_{int(datetime.utcnow().timestamp() * 1000)}"

        model_data = PersonImage(
            id=model_id,
            user_id=user_id,
            gcs_uri=gcs_uri,
            is_active=False,  # Не используется, оставлено для совместимости с БД
            created_at=datetime.utcnow(),
        )

        # Сохраняем в подколлекцию users/{user_id}/models
        doc_ref = client.collection("users").document(user_id).collection("models").document(model_id)
        await doc_ref.set(model_data.model_dump())

        logger.info(f"Модель {model_id} добавлена для пользователя {user_id}")
        return model_id

    async def get_user_models(self, user_id: str) -> list[PersonImage]:
        """
        Получить все модели пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список моделей пользователя
        """
        client = self._get_client()
        models_ref = client.collection("users").document(user_id).collection("models")
        
        models = []
        async for doc in models_ref.stream():
            data = doc.to_dict()
            if data:
                # ID документа из Firestore должен быть явно установлен
                data["id"] = doc.id
                models.append(PersonImage(**data))
        
        # Сортируем по дате создания (новые первыми)
        models.sort(key=lambda x: x.created_at, reverse=True)
        
        logger.info(f"Найдено {len(models)} моделей для пользователя {user_id}")
        return models

    async def delete_model(self, user_id: str, model_id: str) -> None:
        """
        Удалить модель пользователя.

        Args:
            user_id: ID пользователя
            model_id: ID модели для удаления
        """
        client = self._get_client()
        doc_ref = client.collection("users").document(user_id).collection("models").document(model_id)
        await doc_ref.delete()
        
        logger.info(f"Модель {model_id} удалена для пользователя {user_id}")

    async def close(self) -> None:
        """Закрыть соединение с Firestore."""
        if self._client is not None:
            await self._client.close()
            self._client = None
            logger.info("Соединение с Firestore закрыто")
