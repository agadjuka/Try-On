"""Сервис для транскрибации аудио сообщений."""

import base64
import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_google_vertexai import ChatVertexAI

from app.config.llm_factory import create_llm

logger = logging.getLogger(__name__)

LOCATION = "global"
LLM = "gemini-2.5-flash"


class AudioTranscriptionService:
    """Сервис для транскрибации аудио через Gemini."""

    def __init__(self) -> None:
        """Инициализирует сервис транскрибации."""
        self.llm: ChatVertexAI = create_llm(model=LLM, location=LOCATION, temperature=0)

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """Транскрибирует аудио в текст.

        Args:
            audio_bytes: Аудио данные в формате bytes (OGG формат)

        Returns:
            Транскрибированный текст

        Raises:
            Exception: Если транскрибация не удалась
        """
        logger.info("Начало транскрибации аудио, размер: %d байт", len(audio_bytes))

        # Кодируем аудио в base64
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        # Создаем мультимодальное сообщение
        content = [
            {
                "type": "text",
                "text": "Transcribe the audio exactly as spoken. Return only the text.",
            },
            {
                "type": "media",
                "mime_type": "audio/ogg",
                "data": audio_base64,
            },
        ]

        try:
            # Создаем сообщение и вызываем LLM
            message = HumanMessage(content=content)
            response = await self.llm.ainvoke([message])

            # Извлекаем текст из ответа
            if hasattr(response, "content"):
                transcribed_text = response.content
            else:
                transcribed_text = str(response)

            # Очищаем текст от лишних символов
            transcribed_text = transcribed_text.strip()

            logger.info(
                "Транскрибация завершена, длина текста: %d символов",
                len(transcribed_text),
            )

            return transcribed_text

        except Exception as e:
            logger.error("Ошибка при транскрибации аудио: %s", str(e), exc_info=True)
            raise


# Singleton экземпляр сервиса
_transcription_service: AudioTranscriptionService | None = None


def get_transcription_service() -> AudioTranscriptionService:
    """Получает singleton экземпляр сервиса транскрибации.

    Returns:
        Экземпляр AudioTranscriptionService
    """
    global _transcription_service
    if _transcription_service is None:
        _transcription_service = AudioTranscriptionService()
    return _transcription_service

