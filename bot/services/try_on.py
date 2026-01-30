"""Сервис для работы с Vertex AI Virtual Try-On API."""

import asyncio
import base64
import json
from typing import Dict, Any, Optional

import requests
from google.auth import default
from google.auth.transport.requests import Request
from loguru import logger
from aiogram import Bot
from aiogram.types import User

from bot.core.config import Settings


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
        # Храним не сам токен, а креденшелы — токен будем получать каждый раз,
        # чтобы он не протухал при долгой работе контейнера
        self._credentials = None

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
        Получить актуальный access token через Application Default Credentials.
        Токен НЕ кэшируется в виде строки, каждый раз берём его из креденшелов,
        которые при необходимости сами обновляются.

        Returns:
            Access token для авторизации

        Raises:
            RuntimeError: Если не удалось получить токен
        """
        try:
            # Инициализируем креденшелы один раз
            if self._credentials is None:
                self._credentials, _ = default()

            # При необходимости обновляем (если истёк или ещё не получен)
            if not self._credentials.valid:
                self._credentials.refresh(Request())

            token = self._credentials.token
            if not token:
                raise RuntimeError("Пустой access token из креденшелов")

            logger.debug("Access token получен из Application Default Credentials")
            return token

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
        garment_bytes: bytes,
        base_steps: int = 32,
        sample_count: int = 1,
        add_watermark: bool = False,
        person_generation: str = "allow_all",
        safety_setting: str = "block_medium_and_above",
        output_mime_type: str = "image/png",
        compression_quality: int = 0,
        storage_uri: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Создать тело запроса для API.
        Модель передается через GCS URI, одежда - через base64.

        Args:
            person_gcs_uri: URI изображения модели в GCS (gs://bucket/path)
            garment_bytes: Байты изображения одежды
            base_steps: Качество генерации (по умолчанию: 32)
            sample_count: Количество изображений на пару (по умолчанию: 1)
            add_watermark: Добавлять водяной знак (по умолчанию: True)
            person_generation: Разрешение генерации людей (по умолчанию: allow_all)
            safety_setting: Уровень фильтрации безопасности (по умолчанию: block_medium_and_above)
            output_mime_type: Формат вывода (по умолчанию: image/png)
            compression_quality: Качество сжатия для JPEG (по умолчанию: 75)
            storage_uri: Путь в Cloud Storage для сохранения (опционально)
            seed: Случайное зерно для генерации (только если add_watermark=False)

        Returns:
            Словарь с телом запроса
        """
        # Кодируем фото одежды в base64
        garment_base64 = base64.b64encode(garment_bytes).decode('utf-8')
        
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
                                "bytesBase64Encoded": garment_base64
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
        garment_bytes: bytes,
        base_steps: int = 32,
        sample_count: int = 1,
        add_watermark: bool = False,
        user: Optional[User] = None,
        bot: Optional[Bot] = None,
    ) -> bytes:
        """
        Генерировать изображение примерки асинхронно.
        Модель передается через GCS URI, одежда - через base64.
        Результат возвращается в виде байтов без сохранения в облако.

        Args:
            person_gcs_uri: URI изображения модели в GCS (gs://bucket/path)
            garment_bytes: Байты изображения одежды
            base_steps: Качество генерации (по умолчанию: 32)
            sample_count: Количество изображений на пару (по умолчанию: 1)
            add_watermark: Добавлять водяной знак (по умолчанию: True)
            user: Пользователь (для отправки ошибок в админ-панель, опционально)
            bot: Экземпляр бота (для отправки ошибок в админ-панель, опционально)

        Returns:
            Байты результата примерки

        Raises:
            ValueError: Если ответ API не содержит predictions
            RuntimeError: При ошибке запроса к API или обработки ответа
        """
        logger.info("=" * 60)
        logger.info("НАЧАЛО ГЕНЕРАЦИИ TRY-ON (одежда через base64)")
        logger.info("=" * 60)
        
        access_token = self._get_access_token()
        request_body = self._build_request_body(
            person_gcs_uri=person_gcs_uri,
            garment_bytes=garment_bytes,
            base_steps=base_steps,
            sample_count=sample_count,
            add_watermark=add_watermark,
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        api_url = self._get_api_url()
        logger.info(f"Отправка запроса к Vertex AI API: {api_url}")
        logger.info(f"Person GCS URI: {person_gcs_uri}")
        logger.info(f"Garment: передано через base64 ({len(garment_bytes)} байт)")

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
                raw_response = json.dumps(result, indent=2, ensure_ascii=False)
                logger.error(f"{error_msg}. Ответ: {raw_response}")
                
                # Отправляем ошибку в админ-панель
                if user and bot:
                    try:
                        from bot.admin.error_reporter import get_error_reporter
                        error_reporter = get_error_reporter(bot)
                        if error_reporter:
                            error_reporter.send_error_async(
                                user=user,
                                error=ValueError(error_msg),
                                context="Try-On Generation",
                                raw_response=raw_response,
                            )
                    except Exception as report_error:
                        logger.error(f"Ошибка при отправке ошибки в админ-панель: {report_error}")
                
                raise ValueError(error_msg)

            predictions = result["predictions"]
            if not predictions:
                error_msg = "Ответ API содержит пустой список predictions"
                raw_response = json.dumps(result, indent=2, ensure_ascii=False)
                logger.error(f"{error_msg}. Ответ: {raw_response}")
                
                # Отправляем ошибку в админ-панель
                if user and bot:
                    try:
                        from bot.admin.error_reporter import get_error_reporter
                        error_reporter = get_error_reporter(bot)
                        if error_reporter:
                            error_reporter.send_error_async(
                                user=user,
                                error=ValueError(error_msg),
                                context="Try-On Generation",
                                raw_response=raw_response,
                            )
                    except Exception as report_error:
                        logger.error(f"Ошибка при отправке ошибки в админ-панель: {report_error}")
                
                raise ValueError(error_msg)

            logger.info(f"Получено {len(predictions)} результатов")

            # Берем первый результат
            first_prediction = predictions[0]

            if "bytesBase64Encoded" not in first_prediction:
                error_msg = "Ответ не содержит 'bytesBase64Encoded'"
                raw_response = json.dumps(first_prediction, indent=2, ensure_ascii=False)
                logger.error(f"{error_msg}. Ответ: {raw_response}")
                
                # Отправляем ошибку в админ-панель
                if user and bot:
                    try:
                        from bot.admin.error_reporter import get_error_reporter
                        error_reporter = get_error_reporter(bot)
                        if error_reporter:
                            error_reporter.send_error_async(
                                user=user,
                                error=ValueError(error_msg),
                                context="Try-On Generation",
                                raw_response=raw_response,
                            )
                    except Exception as report_error:
                        logger.error(f"Ошибка при отправке ошибки в админ-панель: {report_error}")
                
                raise ValueError(error_msg)

            # Декодируем base64 в байты
            image_base64 = first_prediction["bytesBase64Encoded"]
            image_bytes = base64.b64decode(image_base64)

            logger.success(f"Результат успешно получен ({len(image_bytes)} байт)")
            return image_bytes

        except requests.exceptions.RequestException as e:
            error_detail = "Неизвестная ошибка"
            raw_response = None
            
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    raw_response = json.dumps(error_detail, indent=2, ensure_ascii=False)
                    logger.error(f"Детали ошибки: {raw_response}")
                except:
                    error_detail = e.response.text
                    raw_response = error_detail
                    logger.error(f"Текст ответа: {raw_response}")

            logger.error(f"Ошибка при запросе к API: {e}")
            
            # Отправляем ошибку в админ-панель, если есть user и bot
            if user and bot:
                try:
                    from bot.admin.error_reporter import get_error_reporter
                    error_reporter = get_error_reporter(bot)
                    if error_reporter:
                        error_reporter.send_error_async(
                            user=user,
                            error=e,
                            context="Try-On Generation",
                            raw_response=raw_response,
                        )
                except Exception as report_error:
                    logger.error(f"Ошибка при отправке ошибки в админ-панель: {report_error}")
            
            raise RuntimeError(
                f"Ошибка API: {str(e)}. "
                f"Детали: {error_detail}"
            ) from e

        except Exception as e:
            logger.error(f"Неожиданная ошибка при генерации: {e}")
            
            # Отправляем ошибку в админ-панель, если есть user и bot
            if user and bot:
                try:
                    from bot.admin.error_reporter import get_error_reporter
                    error_reporter = get_error_reporter(bot)
                    if error_reporter:
                        error_reporter.send_error_async(
                            user=user,
                            error=e,
                            context="Try-On Generation",
                        )
                except Exception as report_error:
                    logger.error(f"Ошибка при отправке ошибки в админ-панель: {report_error}")
            
            raise RuntimeError(f"Неожиданная ошибка при генерации: {str(e)}") from e
