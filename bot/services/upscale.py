"""Сервис для апскейла изображений через Imagen API."""

import base64
import asyncio
from typing import Optional

import aiohttp
from google.auth import default
from google.auth.transport.requests import Request
from loguru import logger

from bot.core.config import Settings


class UpscaleService:
    """Сервис для апскейла изображений через Google Imagen API."""

    def __init__(self, settings: Settings):
        """
        Инициализировать сервис.

        Args:
            settings: Настройки приложения
        """
        self.settings = settings
        self._credentials = None

    def _get_credentials(self):
        """Получить учетные данные Google Cloud."""
        if self._credentials is None:
            self._credentials, _ = default()
        if not self._credentials.valid:
            self._credentials.refresh(Request())
        return self._credentials

    async def _get_access_token(self) -> str:
        """
        Получить access token для Google Cloud API асинхронно.

        Returns:
            Access token
        """
        def _get_token() -> str:
            """Синхронная функция получения токена."""
            credentials = self._get_credentials()
            return credentials.token

        try:
            token = await asyncio.to_thread(_get_token)
            return token
        except Exception as e:
            raise Exception(f"Ошибка получения токена доступа: {str(e)}") from e

    async def upscale_image(
        self,
        image_bytes: bytes,
        upscale_factor: str = "x2",
    ) -> bytes:
        """
        Апскейл изображения через Imagen API.

        Args:
            image_bytes: Байты изображения для апскейла
            upscale_factor: Фактор увеличения ("x2", "x4", "x8")

        Returns:
            Байты апскейленного изображения

        Raises:
            Exception: При ошибке апскейла
        """
        # Кодируем изображение в base64
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        # Получаем токен
        token = await self._get_access_token()

        # Формируем URL
        region = self.settings.google_cloud_region
        project_id = self.settings.google_cloud_project_id
        
        url = (
            f"https://{region}-aiplatform.googleapis.com/v1/"
            f"projects/{project_id}/locations/{region}/"
            f"publishers/google/models/imagen-4.0-upscale-preview:predict"
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

        payload = {
            "instances": [
                {
                    "prompt": "Upscale the image",
                    "image": {
                        "bytesBase64Encoded": image_base64,
                    },
                }
            ],
            "parameters": {
                "mode": "upscale",
                "outputOptions": {
                    "mimeType": "image/png",
                },
                "upscaleConfig": {
                    "upscaleFactor": upscale_factor,
                },
            },
        }

        try:
            # Отправляем запрос асинхронно
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    result = await response.json()

            # Проверяем результат
            if "predictions" not in result or not result["predictions"]:
                raise Exception("Не получен результат от API")

            # Декодируем результат
            output_base64 = result["predictions"][0]["bytesBase64Encoded"]
            output_bytes = base64.b64decode(output_base64)

            logger.info(f"Изображение успешно апскейлено (фактор: {upscale_factor})")
            return output_bytes

        except aiohttp.ClientError as e:
            raise Exception(f"Ошибка HTTP запроса к Imagen API: {str(e)}") from e
        except Exception as e:
            raise Exception(f"Ошибка при апскейле изображения: {str(e)}") from e
