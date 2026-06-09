"""Сервис для работы с объектным хранилищем (Oracle S3-compatible / GCS)."""

import asyncio
from typing import Optional

import boto3
from botocore.config import Config

from bot.core.config import Settings


class CloudStorageService:
    """Асинхронный фасад для Oracle Object Storage или Google Cloud Storage."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._gcs_client: Optional[object] = None
        self._s3_client = None

    def _primary_backend(self) -> str:
        return self.settings.storage_backend

    def _oracle_bucket(self) -> str:
        bucket = self.settings.oracle_bucket_name or self.settings.gcs_bucket_name
        if not bucket:
            raise ValueError("Для Oracle storage требуется ORACLE_BUCKET_NAME")
        return bucket

    def _get_gcs_client(self) -> object:
        if self._gcs_client is None:
            if not self.settings.google_cloud_project_id:
                raise ValueError("Для GCS storage требуется GOOGLE_CLOUD_PROJECT_ID")
            try:
                from google.auth.exceptions import DefaultCredentialsError
                from google.cloud import storage

                self._gcs_client = storage.Client(project=self.settings.google_cloud_project_id)
            except ImportError as e:
                raise ImportError(
                    "Для GCS storage установите google-cloud-storage и google-auth"
                ) from e
            except DefaultCredentialsError as e:
                raise DefaultCredentialsError(
                    "Не найдены учетные данные Google Cloud. "
                    "Установите GOOGLE_APPLICATION_CREDENTIALS или выполните ADC login."
                ) from e
        return self._gcs_client

    def _get_s3_client(self):
        if self._s3_client is None:
            if not self.settings.oracle_access_key_id or not self.settings.oracle_secret_access_key:
                raise ValueError("Для Oracle storage задать ORACLE_ACCESS_KEY_ID и ORACLE_SECRET_ACCESS_KEY")
            if not self.settings.oracle_s3_endpoint or not self.settings.oracle_s3_region:
                raise ValueError("Для Oracle storage задать ORACLE_S3_ENDPOINT и ORACLE_S3_REGION")
            self._s3_client = boto3.client(
                "s3",
                aws_access_key_id=self.settings.oracle_access_key_id,
                aws_secret_access_key=self.settings.oracle_secret_access_key,
                endpoint_url=self.settings.oracle_s3_endpoint,
                region_name=self.settings.oracle_s3_region,
                config=Config(
                    signature_version="s3v4",
                    request_checksum_calculation="when_required",
                    response_checksum_validation="when_required",
                    s3={
                        "addressing_style": "path",
                        "payload_signing_enabled": False,
                    },
                ),
            )
        return self._s3_client

    def _parse_uri(self, uri: str) -> tuple[str, str, str]:
        """Вернуть (scheme, bucket, key) для gs:// и s3:// URI."""
        if uri.startswith("gs://"):
            rest = uri[5:]
            scheme = "gs"
        elif uri.startswith("s3://"):
            rest = uri[5:]
            scheme = "s3"
        else:
            raise ValueError(f"Некорректный URI хранилища: {uri}")
        parts = rest.split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        return scheme, bucket, key

    async def upload_image(self, file_bytes: bytes, destination_path: str) -> str:
        return await self.upload_file(
            file_bytes=file_bytes,
            destination_path=destination_path,
            content_type="image/png",
        )

    async def upload_file(
        self, file_bytes: bytes, destination_path: str, content_type: str = "text/plain"
    ) -> str:
        backend = self._primary_backend()
        if backend == "oracle":
            client = self._get_s3_client()
            bucket = self._oracle_bucket()

            def _upload() -> str:
                client.put_object(
                    Bucket=bucket,
                    Key=destination_path,
                    Body=file_bytes,
                    ContentType=content_type,
                    ContentLength=len(file_bytes),
                )
                return f"s3://{bucket}/{destination_path}"

            try:
                return await asyncio.to_thread(_upload)
            except Exception as e:
                raise Exception(f"Ошибка загрузки файла в Oracle Object Storage: {str(e)}") from e

        client = self._get_gcs_client()
        if not self.settings.gcs_bucket_name:
            raise ValueError("Для GCS storage требуется GCS_BUCKET_NAME")
        bucket = client.bucket(self.settings.gcs_bucket_name)

        def _upload_gcs() -> str:
            blob = bucket.blob(destination_path)
            blob.upload_from_string(file_bytes, content_type=content_type)
            return f"gs://{self.settings.gcs_bucket_name}/{destination_path}"

        try:
            return await asyncio.to_thread(_upload_gcs)
        except Exception as e:
            raise Exception(f"Ошибка загрузки файла в GCS: {str(e)}") from e

    async def download_file(self, uri: str) -> bytes:
        scheme, bucket_name, key = self._parse_uri(uri)
        if scheme == "s3":
            client = self._get_s3_client()

            def _download_s3() -> bytes:
                response = client.get_object(Bucket=bucket_name, Key=key)
                return response["Body"].read()

            try:
                return await asyncio.to_thread(_download_s3)
            except Exception as e:
                raise Exception(f"Ошибка скачивания файла из Oracle Object Storage: {str(e)}") from e

        client = self._get_gcs_client()
        bucket = client.bucket(bucket_name)

        def _download_gcs() -> bytes:
            blob = bucket.blob(key)
            if not blob.exists():
                raise Exception(f"Файл не найден: {uri}")
            return blob.download_as_bytes()

        try:
            return await asyncio.to_thread(_download_gcs)
        except Exception as e:
            raise Exception(f"Ошибка скачивания файла из GCS: {str(e)}") from e

    async def delete_file(self, uri: str) -> None:
        scheme, bucket_name, key = self._parse_uri(uri)
        if scheme == "s3":
            client = self._get_s3_client()

            def _delete_s3() -> None:
                client.delete_object(Bucket=bucket_name, Key=key)

            try:
                await asyncio.to_thread(_delete_s3)
                return
            except Exception as e:
                raise Exception(f"Ошибка удаления файла из Oracle Object Storage: {str(e)}") from e

        client = self._get_gcs_client()
        bucket = client.bucket(bucket_name)

        def _delete_gcs() -> None:
            blob = bucket.blob(key)
            if blob.exists():
                blob.delete()

        try:
            await asyncio.to_thread(_delete_gcs)
        except Exception as e:
            raise Exception(f"Ошибка удаления файла из GCS: {str(e)}") from e