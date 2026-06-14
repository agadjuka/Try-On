"""Сервис генерации Virtual Try-On через Gemini или OpenAI Images API."""

import asyncio
import base64
import json
from io import BytesIO
from typing import Dict, Any, Optional

import requests
from loguru import logger

from aiogram import Bot
from aiogram.types import User

from bot.core.config import Settings


class VertexTryOnService:
    """Асинхронный сервис для генерации примерки через выбранный image API.

    Название класса оставлено прежним, чтобы не менять существующие
    обработчики и контейнеры, которые уже зависят от этого типа.
    """

    def __init__(self, settings: Settings):
        """
        Инициализировать сервис.

        Args:
            settings: Настройки приложения с параметрами image provider
        """
        self.settings = settings
        self.provider = settings.try_on_provider
        self.api_key = settings.gemini_api_key
        self.openai_api_key = settings.openai_api_key
        self.model_id = settings.gemini_model
        self.openai_model_id = settings.openai_image_model
        self.prompt = settings.gemini_try_on_prompt

    def _get_gemini_api_url(self) -> str:
        """
        Получить URL для API запроса.

        Returns:
            URL эндпоинта Gemini API
        """
        return f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent"

    @staticmethod
    def _get_openai_api_url() -> str:
        """Получить URL OpenAI Images Edit API."""
        return "https://api.openai.com/v1/images/edits"

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

    @staticmethod
    def _openai_file_part(filename: str, image_bytes: bytes) -> tuple[str, BytesIO, str]:
        """Сформировать file tuple для requests multipart."""
        mime_type = VertexTryOnService._detect_mime_type(image_bytes)
        return (
            filename,
            BytesIO(image_bytes),
            mime_type,
        )

    @staticmethod
    def _extension_for_mime_type(image_bytes: bytes) -> str:
        mime_type = VertexTryOnService._detect_mime_type(image_bytes)
        if mime_type == "image/png":
            return "png"
        if mime_type == "image/webp":
            return "webp"
        return "jpg"

    def _build_openai_request(
        self,
        person_image_bytes: Optional[bytes],
        garment_bytes: bytes,
    ) -> tuple[Dict[str, str], list[tuple[str, tuple[str, BytesIO, str]]]]:
        """Создать multipart data/files для OpenAI Images Edit API."""
        if not self.openai_api_key:
            raise ValueError("Не задан OPENAI_API_KEY")

        if person_image_bytes is None:
            raise ValueError("Для OpenAI Images Edit API нужно передать person_image_bytes")

        data = {
            "model": self.openai_model_id,
            "prompt": (
                f"{self.prompt} Preserve the aspect ratio and framing of the first "
                "photo whenever possible. Do not add padding or white borders."
            ),
            "n": "1",
            "quality": self.settings.openai_image_quality,
            "size": self.settings.openai_image_size,
            "output_format": self.settings.openai_image_output_format,
        }
        model_ext = self._extension_for_mime_type(person_image_bytes)
        garment_ext = self._extension_for_mime_type(garment_bytes)
        # Важно для try-on: первый reference image - модель, второй - одежда.
        files = [
            ("image[]", self._openai_file_part(f"model.{model_ext}", person_image_bytes)),
            ("image[]", self._openai_file_part(f"garment.{garment_ext}", garment_bytes)),
        ]
        return data, files

    @staticmethod
    def _log_openai_usage(result: Dict[str, Any]) -> None:
        """Залогировать usage из OpenAI Images API."""
        usage = result.get("usage")
        if not isinstance(usage, dict):
            logger.warning("OpenAI Images API не вернул usage с токенами")
            return

        input_details = usage.get("input_tokens_details") or {}
        output_details = usage.get("output_tokens_details") or {}
        logger.info(
            "OpenAI image usage: "
            f"input={usage.get('input_tokens')}, "
            f"output={usage.get('output_tokens')}, "
            f"total={usage.get('total_tokens')}, "
            f"input_text={input_details.get('text_tokens')}, "
            f"input_image={input_details.get('image_tokens')}, "
            f"output_text={output_details.get('text_tokens')}, "
            f"output_image={output_details.get('image_tokens')}"
        )
        logger.info(
            "OpenAI image usage raw: "
            f"{json.dumps(usage, ensure_ascii=False)}"
        )

    @staticmethod
    def _extract_openai_image_base64(result: Dict[str, Any]) -> Optional[str]:
        data = result.get("data") or []
        if not data or not isinstance(data[0], dict):
            return None
        return data[0].get("b64_json")

    @staticmethod
    def _get_usage_count(usage_metadata: Dict[str, Any], camel_key: str, snake_key: str) -> Any:
        """Вернуть счетчик usageMetadata с учетом camelCase/snake_case."""
        return usage_metadata.get(camel_key, usage_metadata.get(snake_key))

    @classmethod
    def _log_usage_metadata(cls, result: Dict[str, Any]) -> None:
        """Залогировать токены, которые Gemini вернул в usageMetadata."""
        usage_metadata = result.get("usageMetadata") or result.get("usage_metadata")
        if not isinstance(usage_metadata, dict):
            logger.warning("Gemini API не вернул usageMetadata с токенами")
            return

        prompt_tokens = cls._get_usage_count(
            usage_metadata, "promptTokenCount", "prompt_token_count"
        )
        output_tokens = cls._get_usage_count(
            usage_metadata, "candidatesTokenCount", "candidates_token_count"
        )
        thoughts_tokens = cls._get_usage_count(
            usage_metadata, "thoughtsTokenCount", "thoughts_token_count"
        )
        cached_tokens = cls._get_usage_count(
            usage_metadata, "cachedContentTokenCount", "cached_content_token_count"
        )
        total_tokens = cls._get_usage_count(
            usage_metadata, "totalTokenCount", "total_token_count"
        )

        logger.info(
            "Gemini token usage: "
            f"input={prompt_tokens}, output={output_tokens}, "
            f"thoughts={thoughts_tokens}, cached={cached_tokens}, total={total_tokens}"
        )

        token_details = {
            "promptTokensDetails": usage_metadata.get("promptTokensDetails")
            or usage_metadata.get("prompt_tokens_details"),
            "candidatesTokensDetails": usage_metadata.get("candidatesTokensDetails")
            or usage_metadata.get("candidates_tokens_details"),
        }
        if any(token_details.values()):
            logger.info(
                "Gemini token usage details: "
                f"{json.dumps(token_details, ensure_ascii=False)}"
            )

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

    async def _generate_openai_try_on(
        self,
        garment_bytes: bytes,
        person_image_uri: Optional[str] = None,
        person_image_bytes: Optional[bytes] = None,
        user: Optional[User] = None,
        bot: Optional[Bot] = None,
    ) -> bytes:
        """Генерировать примерку через OpenAI Images Edit API."""
        logger.info("=" * 60)
        logger.info("НАЧАЛО ГЕНЕРАЦИИ TRY-ON (OpenAI Images Edit API)")
        logger.info("=" * 60)

        data, files = self._build_openai_request(
            person_image_bytes=person_image_bytes,
            garment_bytes=garment_bytes,
        )
        headers = {"Authorization": f"Bearer {self.openai_api_key}"}

        api_url = self._get_openai_api_url()
        logger.info(f"Отправка запроса к OpenAI Images API: {api_url}")
        logger.info(f"OpenAI image model: {self.openai_model_id}")
        logger.info(
            "OpenAI image settings: "
            f"quality={self.settings.openai_image_quality}, "
            f"size={self.settings.openai_image_size}, "
            f"format={self.settings.openai_image_output_format}"
        )
        if person_image_uri:
            logger.info(f"Person image URI: {person_image_uri}")
        logger.info(f"Person image: передано как image[0] ({len(person_image_bytes or b'')} байт)")
        logger.info(f"Garment: передано как image[1] ({len(garment_bytes)} байт)")

        def _make_request() -> dict:
            response = requests.post(
                api_url,
                headers=headers,
                data=data,
                files=files,
                timeout=300,
            )
            response.raise_for_status()
            return response.json()

        try:
            result = await asyncio.to_thread(_make_request)
            self._log_openai_usage(result)

            image_base64 = self._extract_openai_image_base64(result)
            if not image_base64:
                error_msg = "Ответ OpenAI Images API не содержит data[0].b64_json"
                raw_response = self._format_response_for_log(result)
                logger.error(f"{error_msg}. Ответ: {raw_response}")
                error = ValueError(error_msg)
                self._report_error_async(user, bot, error, "Try-On Generation", raw_response)
                raise error

            image_bytes = base64.b64decode(image_base64)
            logger.success(f"Результат OpenAI успешно получен ({len(image_bytes)} байт)")
            return image_bytes

        except requests.exceptions.RequestException as e:
            error_detail = "Неизвестная ошибка"
            raw_response = None

            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    raw_response = json.dumps(error_detail, indent=2, ensure_ascii=False)
                    logger.error(f"Детали ошибки OpenAI: {raw_response}")
                except Exception:
                    error_detail = e.response.text
                    raw_response = error_detail
                    logger.error(f"Текст ответа OpenAI: {raw_response}")

            logger.error(f"Ошибка при запросе к OpenAI Images API: {e}")
            self._report_error_async(user, bot, e, "Try-On Generation", raw_response)
            raise RuntimeError(
                f"Ошибка OpenAI API: {str(e)}. "
                f"Детали: {error_detail}"
            ) from e

        except Exception as e:
            logger.error(f"Неожиданная ошибка при OpenAI генерации: {e}")
            self._report_error_async(user, bot, e, "Try-On Generation")
            raise RuntimeError(f"Неожиданная ошибка при OpenAI генерации: {str(e)}") from e

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
        if self.provider == "openai":
            return await self._generate_openai_try_on(
                garment_bytes=garment_bytes,
                person_image_uri=person_image_uri,
                person_image_bytes=person_image_bytes,
                user=user,
                bot=bot,
            )

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

        api_url = self._get_gemini_api_url()
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
            self._log_usage_metadata(result)

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
