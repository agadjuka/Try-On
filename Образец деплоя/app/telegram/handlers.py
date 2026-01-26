"""Обработчики сообщений для Telegram бота."""

import logging
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from app.telegram.audio_transcription import get_transcription_service
from app.telegram.service import AgentService

logger = logging.getLogger(__name__)


class MessageHandlers:
    """Класс для обработки сообщений Telegram."""

    def __init__(self, agent_service: AgentService) -> None:
        """Инициализирует обработчики.

        Args:
            agent_service: Сервис для взаимодействия с агентом
        """
        self.agent_service = agent_service

    async def _download_voice_to_memory(self, bot: Any, file_id: str) -> bytes:
        """Скачивает голосовое сообщение в память.

        Args:
            bot: Экземпляр Telegram бота
            file_id: ID файла голосового сообщения

        Returns:
            Аудио данные в формате bytes

        Raises:
            Exception: Если не удалось скачать файл
        """
        logger.info("Скачивание голосового сообщения, file_id: %s", file_id)
        try:
            file = await bot.get_file(file_id)
            audio_bytearray = await file.download_as_bytearray()
            audio_bytes = bytes(audio_bytearray)
            logger.info("Голосовое сообщение скачано, размер: %d байт", len(audio_bytes))
            return audio_bytes
        except Exception as e:
            logger.error("Ошибка при скачивании голосового сообщения: %s", str(e), exc_info=True)
            raise

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обрабатывает текстовое или голосовое сообщение от пользователя.

        Args:
            update: Обновление от Telegram
            context: Контекст бота
        """
        if not update.message:
            return

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        message_text: str | None = None

        # Определяем тип сообщения
        if update.message.text:
            message_text = update.message.text
            logger.info("Получено текстовое сообщение от пользователя %s в чате %s", user_id, chat_id)
        elif update.message.voice:
            # Обрабатываем голосовое сообщение
            logger.info("Получено голосовое сообщение от пользователя %s в чате %s", user_id, chat_id)

            # Отправляем индикатор записи голоса
            await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")

            try:
                # Скачиваем аудио в память
                file_id = update.message.voice.file_id
                audio_bytes = await self._download_voice_to_memory(context.bot, file_id)

                # Транскрибируем аудио
                transcription_service = get_transcription_service()
                message_text = await transcription_service.transcribe_audio(audio_bytes)

                if not message_text or not message_text.strip():
                    logger.warning("Транскрибация вернула пустой текст")
                    await update.message.reply_text(
                        "Не удалось распознать речь в аудиосообщении. Попробуйте отправить текстовое сообщение."
                    )
                    return

                logger.info("Транскрибация завершена: %s", message_text[:100])

            except Exception as e:
                logger.error("Ошибка при обработке голосового сообщения: %s", str(e), exc_info=True)
                await update.message.reply_text(
                    "Произошла ошибка при обработке аудиосообщения. Попробуйте отправить текстовое сообщение."
                )
                return
        else:
            # Неизвестный тип сообщения
            return

        if not message_text:
            return

        # Отправляем индикатор печати
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        try:
            # Обрабатываем сообщение через агента
            response = await self.agent_service.process_message(
                user_message=message_text,
                user_id=str(user_id),
                bot=context.bot,
                chat_id=chat_id,
                session_id=str(chat_id),
            )

            # Отправляем ответ пользователю только если response не None
            # (если был вызван CallManager, сообщения уже отправлены)
            if response is not None:
                await update.message.reply_text(response)

        except Exception as e:
            logger.error("Ошибка при обработке сообщения: %s", str(e), exc_info=True)
            error_message = "Произошла ошибка при обработке вашего сообщения. Попробуйте позже."
            await update.message.reply_text(error_message)

    async def handle_error(self, update: Update | None, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обрабатывает ошибки бота.

        Args:
            update: Обновление от Telegram (может быть None)
            context: Контекст бота
        """
        logger.error("Ошибка в обработчике: %s", context.error, exc_info=True)

        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "Произошла ошибка при обработке вашего сообщения. Попробуйте позже."
                )
            except Exception as e:
                logger.error("Не удалось отправить сообщение об ошибке: %s", str(e))

