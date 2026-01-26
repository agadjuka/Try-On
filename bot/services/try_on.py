"""Сервис для работы с Vertex AI Virtual Try-On API."""

import asyncio
import base64
import json
from typing import Dict, Any, Optional

import requests
from google.auth import default
from google.auth.transport.requests import Request
from loguru import logger

from bot.core.config import Settings
from bot.services.storage import CloudStorageService


class VertexTryOnService:
    """Асинхронный сервис для генерации примерки через Vertex AI."""

    def __init__(self, settings: Settings):
        """
        Инициализировать сервис.

        Args:
            settings: Настройки приложения с параметрами Google Cloud
        """
        self.settings = settings
        self.project_id = settings.google_cloud_project_id
        self.region = settings.google_cloud_region
        self.model_id = "virtual-try-on-001"
        self._access_token: Optional[str] = None

    def _get_api_url(self) -> str:
        """
        Получить URL для API запроса.

        Returns:
            URL эндпоинта Vertex AI
        """
        return (
            f"https://{self.region}-aiplatform.googleapis.com/v1/"
            f"projects/{self.project_id}/locations/{self.region}/"
            f"publishers/google/models/{self.model_id}:predict"
        )

    def _get_access_token(self) -> str:
        """
        Получить access token через Application Default Credentials.
        Точно так же, как в старой версии (api_client.py).

        Returns:
            Access token для авторизации

        Raises:
            RuntimeError: Если не удалось получить токен
        """
        if self._access_token:
            return self._access_token

        try:
            credentials, _ = default()

            if not credentials.valid:
                credentials.refresh(Request())

            self._access_token = credentials.token
            logger.debug("Access token получен через Application Default Credentials")
            return self._access_token

        except Exception as e:
            logger.error(f"Ошибка при получении access token: {e}")
            raise RuntimeError(
                "Не удалось получить access token. "
                "Убедитесь, что вы авторизованы через 'gcloud auth application-default login' "
                "или установите переменную окружения GOOGLE_APPLICATION_CREDENTIALS"
            ) from e

    def _build_request_body(
        self,
        person_gcs_uri: str,
        garment_gcs_uri: str,
        base_steps: int = 32,
        sample_count: int = 1,
        add_watermark: bool = True,
        person_generation: str = "allow_adult",
        safety_setting: str = "block_medium_and_above",
        output_mime_type: str = "image/png",
        compression_quality: int = 75,
        storage_uri: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Создать тело запроса для API с использованием GCS URI.

        Args:
            person_gcs_uri: URI изображения модели в GCS (gs://bucket/path)
            garment_gcs_uri: URI изображения одежды в GCS (gs://bucket/path)
            base_steps: Качество генерации (по умолчанию: 32)
            sample_count: Количество изображений на пару (по умолчанию: 1)
            add_watermark: Добавлять водяной знак (по умолчанию: True)
            person_generation: Разрешение генерации людей (по умолчанию: allow_adult)
            safety_setting: Уровень фильтрации безопасности (по умолчанию: block_medium_and_above)
            output_mime_type: Формат вывода (по умолчанию: image/png)
            compression_quality: Качество сжатия для JPEG (по умолчанию: 75)
            storage_uri: Путь в Cloud Storage для сохранения (опционально)
            seed: Случайное зерно для генерации (только если add_watermark=False)

        Returns:
            Словарь с телом запроса
        """
        request_body = {
            "instances": [
                {
                    "personImage": {
                        "image": {
                            "gcsUri": person_gcs_uri
                        }
                    },
                    "productImages": [
                        {
                            "image": {
                                "gcsUri": garment_gcs_uri
                            }
                        }
                    ]
                }
            ],
            "parameters": {
                "baseSteps": base_steps,
                "sampleCount": sample_count,
                "addWatermark": add_watermark,
                "personGeneration": person_generation,
                "safetySetting": safety_setting,
                "outputOptions": {
                    "mimeType": output_mime_type
                }
            }
        }

        # Добавляем compressionQuality только для JPEG
        if output_mime_type == "image/jpeg":
            request_body["parameters"]["outputOptions"]["compressionQuality"] = compression_quality

        # Добавляем опциональные параметры
        if storage_uri:
            request_body["parameters"]["storageUri"] = storage_uri

        if seed and not add_watermark:
            request_body["parameters"]["seed"] = seed

        return request_body

    async def generate_try_on(
        self,
        person_gcs_uri: str,
        garment_gcs_uri: str,
        storage_service: CloudStorageService,
        base_steps: int = 32,
        sample_count: int = 1,
        add_watermark: bool = True,
    ) -> str:
        """
        Генерировать изображение примерки асинхронно (используя GCS URI).

        Args:
            person_gcs_uri: URI изображения модели в GCS (gs://bucket/path)
            garment_gcs_uri: URI изображения одежды в GCS (gs://bucket/path)
            storage_service: Сервис для загрузки результата в GCS
            base_steps: Качество генерации (по умолчанию: 32)
            sample_count: Количество изображений на пару (по умолчанию: 1)
            add_watermark: Добавлять водяной знак (по умолчанию: True)

        Returns:
            Публичная ссылка на результат в GCS (gs://bucket/path)

        Raises:
            ValueError: Если ответ API не содержит predictions
            RuntimeError: При ошибке запроса к API или обработки ответа
        """
        logger.info("=" * 60)
        logger.info("НАЧАЛО ГЕНЕРАЦИИ TRY-ON с GCS URI")
        logger.info("=" * 60)
        
        access_token = self._get_access_token()
        request_body = self._build_request_body(
            person_gcs_uri=person_gcs_uri,
            garment_gcs_uri=garment_gcs_uri,
            base_steps=base_steps,
            sample_count=sample_count,
            add_watermark=add_watermark,
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        api_url = self._get_api_url()
        logger.info(f"Отправка ОДНОГО запроса к Vertex AI API: {api_url}")
        logger.info(f"Person GCS URI: {person_gcs_uri}")
        logger.info(f"Garment GCS URI: {garment_gcs_uri}")

        # Используем синхронный requests через asyncio.to_thread, как в старой версии
        def _make_request() -> dict:
            """Синхронная функция для выполнения запроса."""
            response = requests.post(
                api_url,
                headers=headers,
                json=request_body,
                timeout=300  # 5 минут таймаут
            )
            response.raise_for_status()
            return response.json()

        try:
            # Выполняем запрос в отдельном потоке
            result = await asyncio.to_thread(_make_request)

            if "predictions" not in result:
                error_msg = "Ответ API не содержит 'predictions'"
                logger.error(f"{error_msg}. Ответ: {json.dumps(result, indent=2)}")
                raise ValueError(error_msg)

            predictions = result["predictions"]
            if not predictions:
                error_msg = "Ответ API содержит пустой список predictions"
                logger.error(f"{error_msg}. Ответ: {json.dumps(result, indent=2)}")
                raise ValueError(error_msg)

            logger.info(f"Получено {len(predictions)} результатов")

            # Берем первый результат
            first_prediction = predictions[0]

            if "bytesBase64Encoded" not in first_prediction:
                error_msg = "Ответ не содержит 'bytesBase64Encoded'"
                logger.error(f"{error_msg}. Ответ: {json.dumps(first_prediction, indent=2)}")
                raise ValueError(error_msg)

            # Декодируем base64 в байты
            image_base64 = first_prediction["bytesBase64Encoded"]
            image_bytes = base64.b64decode(image_base64)

            # Определяем расширение файла на основе mimeType
            mime_type = first_prediction.get("mimeType", "image/png")
            extension = "png" if mime_type == "image/png" else "jpg"

            # Генерируем уникальное имя файла
            import uuid
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            destination_path = f"try_on_results/{timestamp}_{unique_id}.{extension}"

            # Загружаем результат в GCS
            logger.info(f"Загрузка результата в GCS: {destination_path}")
            gs_uri = await storage_service.upload_file(
                file_bytes=image_bytes,
                destination_path=destination_path,
                content_type=mime_type,
            )

            logger.success(f"Результат успешно загружен: {gs_uri}")
            return gs_uri

        except requests.exceptions.RequestException as e:
            error_detail = "Неизвестная ошибка"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Детали ошибки: {json.dumps(error_detail, indent=2)}")
                except:
                    error_detail = e.response.text
                    logger.error(f"Текст ответа: {error_detail}")

            logger.error(f"Ошибка при запросе к API: {e}")
            raise RuntimeError(
                f"Ошибка API: {str(e)}. "
                f"Детали: {error_detail}"
            ) from e

        except Exception as e:
            logger.error(f"Неожиданная ошибка при генерации: {e}")
            raise RuntimeError(f"Неожиданная ошибка при генерации: {str(e)}") from e
