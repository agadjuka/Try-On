"""Репозиторий для работы с Firestore."""

from datetime import datetime
from typing import Optional

from google.cloud.firestore_v1 import AsyncClient
from google.auth.exceptions import DefaultCredentialsError
from loguru import logger

from bot.core.config import Settings
from bot.database.models import PersonImage, UserModel


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

    async def check_connection(self) -> bool:
        """
        Проверить подключение к Firestore.

        Returns:
            True если подключение успешно, False иначе
        """
        try:
            client = self._get_client()
            # Пытаемся прочитать коллекцию (даже если она пустая)
            collections = client.collections()
            # Преобразуем async generator в список для проверки
            _ = [collection async for collection in collections]
            logger.info("Подключение к Firestore успешно установлено")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к Firestore: {str(e)}")
            return False

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

    async def add_person_image(
        self,
        user_id: str,
        gcs_uri: str,
        image_id: Optional[str] = None,
    ) -> str:
        """
        Сохранить метаданные изображения человека в Firestore.

        Args:
            user_id: ID пользователя-владельца
            gcs_uri: URI изображения в GCS (gs://...)
            image_id: Кастомный ID изображения (если не указан, генерируется автоматически)

        Returns:
            ID изображения в Firestore
        """
        client = self._get_client()

        if image_id is None:
            # Генерируем ID на основе timestamp
            image_id = f"img_{int(datetime.utcnow().timestamp() * 1000)}"

        image_data = PersonImage(
            id=image_id,
            user_id=user_id,
            gcs_uri=gcs_uri,
            is_active=True,
            created_at=datetime.utcnow(),
        )

        doc_ref = client.collection("person_images").document(image_id)
        await doc_ref.set(image_data.model_dump())

        logger.info(f"Изображение {image_id} сохранено в Firestore")
        return image_id

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
