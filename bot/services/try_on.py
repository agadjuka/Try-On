"""Сервис генерации Virtual Try-On через Gemini API."""

import asyncio
import base64
import json
from typing import Dict, Any, Optional

import requests
from loguru import logger

from aiogram import Bot
from aiogram.types import User

from bot.core.config import Settings


class VertexTryOnService:
    """Асинхронный сервис для генерации примерки через Gemini image API.

    Название класса оставлено прежним, чтобы не менять существующие
    обработчики и контейнеры, которые уже зависят от этого типа.
    """

    def __init__(self, settings: Settings):
        """
        Инициализировать сервис.

        Args:
            settings: Настройки приложения с параметрами Gemini
        """
        self.settings = settings
        self.api_key = settings.gemini_api_key
        self.model_id = settings.gemini_model
        self.prompt = settings.gemini_try_on_prompt

    def _get_api_url(self) -> str:
        """
        Получить URL для API запроса.

        Returns:
            URL эндпоинта Gemini API
        """
        return f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent"

    @staticmethod
    def _detect_mime_type(image_bytes: bytes) -> str:
        """Определить MIME type изображения по сигнатуре байтов."""
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if image_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
            return "image/webp"
        return "image/jpeg"

    @staticmethod
    def _image_part(image_bytes: bytes) -> Dict[str, Any]:
        """Сформировать inline_data part для Gemini REST API."""
        return {
            "inline_data": {
                "mime_type": VertexTryOnService._detect_mime_type(image_bytes),
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            }
        }

    def _build_request_body(
        self,
        person_image_uri: Optional[str],
        person_image_bytes: Optional[bytes],
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
        Модель и одежда передаются в Gemini через inline_data в одном запросе.

        Args:
            person_image_uri: URI изображения модели (оставлен для совместимости)
            person_image_bytes: Байты изображения модели
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
        if not self.api_key:
            raise ValueError("Не задан GEMINI_API_KEY")

        if person_image_bytes is None:
            raise ValueError(
                "Для Gemini API нужно передать person_image_bytes. "
                f"URI модели недоступен напрямую: {person_image_uri or 'не указан'}"
            )

        request_body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": self.prompt},
                        # Важно для try-on: сначала фото модели, затем фото одежды.
                        self._image_part(person_image_bytes),
                        self._image_part(garment_bytes),
                    ],
                }
            ],
            "generation_config": {
                "response_modalities": ["IMAGE"],
            },
        }

        return request_body

    @staticmethod
    def _extract_inline_data(part: Dict[str, Any]) -> Optional[str]:
        """Достать base64 изображения из part с учетом snake_case/camelCase."""
        inline_data = part.get("inline_data") or part.get("inlineData")
        if not inline_data:
            return None
        return inline_data.get("data")

    @staticmethod
    def _extract_text(part: Dict[str, Any]) -> Optional[str]:
        text = part.get("text")
        return text if isinstance(text, str) and text.strip() else None

    @staticmethod
    def _get_response_parts(result: Dict[str, Any]) -> list[Dict[str, Any]]:
        """Вернуть parts первого кандидата из ответа Gemini."""
        candidates = result.get("candidates") or []
        if not candidates:
            return []

        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []
        return [part for part in parts if isinstance(part, dict)]

    @staticmethod
    def _format_response_for_log(result: Dict[str, Any]) -> str:
        return json.dumps(result, indent=2, ensure_ascii=False)

    def _report_error_async(
        self,
        user: Optional[User],
        bot: Optional[Bot],
        error: Exception,
        context: str,
        raw_response: Optional[str] = None,
    ) -> None:
        """Отправить ошибку в админ-панель, если доступны user и bot."""
        if not user or not bot:
            return

        try:
            from bot.admin.error_reporter import get_error_reporter

            error_reporter = get_error_reporter(bot)
            if error_reporter:
                error_reporter.send_error_async(
                    user=user,
                    error=error,
                    context=context,
                    raw_response=raw_response,
                )
        except Exception as report_error:
            logger.error(f"Ошибка при отправке ошибки в админ-панель: {report_error}")

    async def generate_try_on(
        self,
        garment_bytes: bytes,
        person_image_uri: Optional[str] = None,
        person_image_bytes: Optional[bytes] = None,
        base_steps: int = 32,
        sample_count: int = 1,
        add_watermark: bool = False,
        user: Optional[User] = None,
        bot: Optional[Bot] = None,
    ) -> bytes:
        """
        Генерировать изображение примерки асинхронно.
        Модель и одежда отправляются в Gemini одним запросом через inline_data.
        Результат возвращается в виде байтов без сохранения в облако.

        Args:
            person_image_uri: URI изображения модели (для логирования/совместимости)
            person_image_bytes: Байты изображения модели
            garment_bytes: Байты изображения одежды
            base_steps: Качество генерации (по умолчанию: 32)
            sample_count: Количество изображений на пару (по умолчанию: 1)
            add_watermark: Добавлять водяной знак (по умолчанию: True)
            user: Пользователь (для отправки ошибок в админ-панель, опционально)
            bot: Экземпляр бота (для отправки ошибок в админ-панель, опционально)

        Returns:
            Байты результата примерки

        Raises:
            ValueError: Если ответ API не содержит изображение
            RuntimeError: При ошибке запроса к API или обработки ответа
        """
        logger.info("=" * 60)
        logger.info("НАЧАЛО ГЕНЕРАЦИИ TRY-ON (Gemini API)")
        logger.info("=" * 60)

        request_body = self._build_request_body(
            person_image_uri=person_image_uri,
            person_image_bytes=person_image_bytes,
            garment_bytes=garment_bytes,
            base_steps=base_steps,
            sample_count=sample_count,
            add_watermark=add_watermark,
        )

        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json; charset=utf-8"
        }

        api_url = self._get_api_url()
        logger.info(f"Отправка запроса к Gemini API: {api_url}")
        if person_image_uri:
            logger.info(f"Person image URI: {person_image_uri}")
        logger.info(f"Person image: передано через inline_data ({len(person_image_bytes or b'')} байт)")
        logger.info(f"Garment: передано через inline_data ({len(garment_bytes)} байт)")

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

            parts = self._get_response_parts(result)
            if not parts:
                error_msg = "Ответ Gemini API не содержит candidates[0].content.parts"
                raw_response = self._format_response_for_log(result)
                logger.error(f"{error_msg}. Ответ: {raw_response}")
                error = ValueError(error_msg)
                self._report_error_async(user, bot, error, "Try-On Generation", raw_response)
                raise error

            texts = [text for part in parts if (text := self._extract_text(part))]
            for text in texts:
                logger.info(f"Gemini text response: {text}")

            image_base64 = next(
                (
                    inline_data
                    for part in parts
                    if (inline_data := self._extract_inline_data(part))
                ),
                None,
            )
            if not image_base64:
                error_msg = "Ответ Gemini API не содержит inline_data с изображением"
                raw_response = self._format_response_for_log(result)
                logger.error(f"{error_msg}. Ответ: {raw_response}")
                error = ValueError(error_msg)
                self._report_error_async(user, bot, error, "Try-On Generation", raw_response)
                raise error

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
            self._report_error_async(user, bot, e, "Try-On Generation", raw_response)
            
            raise RuntimeError(
                f"Ошибка API: {str(e)}. "
                f"Детали: {error_detail}"
            ) from e

        except Exception as e:
            logger.error(f"Неожиданная ошибка при генерации: {e}")
            self._report_error_async(user, bot, e, "Try-On Generation")
            
            raise RuntimeError(f"Неожиданная ошибка при генерации: {str(e)}") from e
