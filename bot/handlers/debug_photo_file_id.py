"""Временный хендлер для вывода file_id фото в терминал."""

from aiogram.types import Message
from loguru import logger


async def log_photo_file_id(message: Message) -> None:
    """
    Вывести file_id отправленного фото в терминал.

    Используется как временный отладочный функционал для локального polling.
    """
    if not message.photo:
        return

    file_id = message.photo[-1].file_id
    logger.info(
        "DEBUG PHOTO file_id: {} | user_id: {} | chat_id: {}",
        file_id,
        message.from_user.id if message.from_user else "unknown",
        message.chat.id if message.chat else "unknown",
    )
