"""Middleware для обработки альбомов Telegram."""

import asyncio
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List

from aiogram import BaseMiddleware
from aiogram.types import Message
from loguru import logger


class AlbumMiddleware(BaseMiddleware):
    """Middleware для группировки сообщений из альбома в один список."""

    def __init__(self, delay: float = 0.8):
        """
        Инициализировать middleware.

        Args:
            delay: Задержка в секундах перед обработкой альбома (по умолчанию 0.8)
        """
        self.delay = delay
        # Хранилище для сообщений из альбомов
        # Ключ: media_group_id, Значение: список сообщений
        self.albums: Dict[str, List[Message]] = defaultdict(list)
        # Флаги обработки для каждого альбома
        self.processing: Dict[str, bool] = {}

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        """
        Обработать событие.

        Args:
            handler: Следующий обработчик в цепочке
            event: Событие от Telegram (Message для message handlers)
            data: Данные для передачи в хендлер

        Returns:
            Результат обработки
        """
        # Проверяем, что это сообщение с фото
        # В aiogram 3 для message handlers event уже является Message
        if not isinstance(event, Message) or not event.photo:
            return await handler(event, data)

        message = event
        media_group_id = message.media_group_id

        # Если это не альбом (нет media_group_id), передаем как обычно
        if not media_group_id:
            return await handler(event, data)

        # Если альбом уже обрабатывается, пропускаем
        if self.processing.get(media_group_id, False):
            return

        # Добавляем сообщение в альбом
        self.albums[media_group_id].append(message)

        # Если это первое сообщение альбома, запускаем таймер
        if len(self.albums[media_group_id]) == 1:
            # Помечаем альбом как обрабатываемый
            self.processing[media_group_id] = True

            # Ждем задержку, чтобы собрать все сообщения
            await asyncio.sleep(self.delay)

            # Получаем все сообщения альбома
            album_messages = self.albums[media_group_id].copy()

            # Очищаем хранилище
            del self.albums[media_group_id]
            del self.processing[media_group_id]

            # Передаем список сообщений в хендлер через data
            data["album"] = album_messages

            logger.info(
                f"Альбом собран: {len(album_messages)} фото "
                f"(media_group_id: {media_group_id})"
            )

            # Вызываем хендлер с первым сообщением, но в data будет album
            return await handler(event, data)

        # Для остальных сообщений альбома ничего не делаем
        # (они уже добавлены в список и будут обработаны первым сообщением)
        return
