"""Сервис для работы с Google Cloud Storage."""

import asyncio
from typing import Optional

from google.cloud import storage
from google.auth.exceptions import DefaultCredentialsError

from bot.core.config import Settings


class CloudStorageService:
    """Сервис для асинхронной работы с Google Cloud Storage через ADC."""

    def __init__(self, settings: Settings):
        """
        Инициализировать сервис.

        Args:
            settings: Настройки приложения с параметрами GCS
        """
        self.settings = settings
        self._client: Optional[storage.Client] = None

    def _get_client(self) -> storage.Client:
        """
        Получить синхронный клиент GCS через Application Default Credentials.

        Returns:
            Клиент Google Cloud Storage

        Raises:
            DefaultCredentialsError: Если не найдены учетные данные ADC
        """
        if self._client is None:
            try:
                self._client = storage.Client(
                    project=self.settings.google_cloud_project_id
                )
            except DefaultCredentialsError as e:
                raise DefaultCredentialsError(
                    "Не найдены учетные данные Google Cloud. "
                    "Выполните: gcloud auth application-default login"
                ) from e
        return self._client

    async def upload_image(
        self, file_bytes: bytes, destination_path: str
    ) -> str:
        """
        Загрузить изображение в GCS бакет асинхронно.

        Args:
            file_bytes: Байты файла для загрузки
            destination_path: Путь назначения в бакете (например, 'images/user123/photo.jpg')

        Returns:
            URI файла в формате gs://bucket-name/path

        Raises:
            Exception: При ошибке загрузки
        """
        client = self._get_client()
        bucket = client.bucket(self.settings.gcs_bucket_name)

        def _upload() -> str:
            """Синхронная функция загрузки."""
            blob = bucket.blob(destination_path)
            blob.upload_from_string(file_bytes, content_type="image/jpeg")
            return f"gs://{self.settings.gcs_bucket_name}/{destination_path}"

        try:
            gs_uri = await asyncio.to_thread(_upload)
            return gs_uri
        except Exception as e:
            raise Exception(f"Ошибка загрузки файла в GCS: {str(e)}") from e

    async def upload_file(
        self, file_bytes: bytes, destination_path: str, content_type: str = "text/plain"
    ) -> str:
        """
        Загрузить произвольный файл в GCS бакет асинхронно.

        Args:
            file_bytes: Байты файла для загрузки
            destination_path: Путь назначения в бакете
            content_type: MIME-тип файла

        Returns:
            URI файла в формате gs://bucket-name/path
        """
        client = self._get_client()
        bucket = client.bucket(self.settings.gcs_bucket_name)

        def _upload() -> str:
            """Синхронная функция загрузки."""
            blob = bucket.blob(destination_path)
            blob.upload_from_string(file_bytes, content_type=content_type)
            return f"gs://{self.settings.gcs_bucket_name}/{destination_path}"

        try:
            gs_uri = await asyncio.to_thread(_upload)
            return gs_uri
        except Exception as e:
            raise Exception(f"Ошибка загрузки файла в GCS: {str(e)}") from e
