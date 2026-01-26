"""Middleware для обработки альбомов Telegram."""

import asyncio
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List

from aiogram import BaseMiddleware
from aiogram.types import Message
from loguru import logger


class AlbumMiddleware(BaseMiddleware):
    """Middleware для группировки сообщений из альбома в один список."""

    def __init__(self, delay: float = 1.5):
        """
        Инициализировать middleware.

        Args:
            delay: Задержка в секундах перед обработкой альбома (по умолчанию 1.5)
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
            logger.debug(f"Сообщение без media_group_id (не альбом): message_id={message.message_id}")
            return await handler(event, data)

        # Добавляем сообщение в альбом СРАЗУ, даже если обрабатывается
        # Это важно, чтобы не потерять сообщения, которые приходят во время обработки
        self.albums[media_group_id].append(message)
        current_count = len(self.albums[media_group_id])
        
        logger.info(
            f"📸 Фото добавлено в альбом {media_group_id}: "
            f"message_id={message.message_id}, "
            f"текущее количество = {current_count}"
        )

        # Если альбом уже обрабатывается, просто добавляем фото и выходим
        # Обработка уже идет, новое фото будет учтено в следующей итерации
        if self.processing.get(media_group_id, False):
            logger.debug(
                f"Альбом {media_group_id} уже обрабатывается, "
                f"фото {message.message_id} добавлено в очередь"
            )
            return

        # Если это первое сообщение альбома, запускаем таймер
        if current_count == 1:
            logger.info(f"🚀 Начало сбора альбома {media_group_id} (первое фото)")
            # Помечаем альбом как обрабатываемый
            self.processing[media_group_id] = True

            # Ждем задержку, чтобы собрать все сообщения
            # Используем несколько итераций с проверкой, чтобы убедиться, что все фото собраны
            max_iterations = 5  # Максимум 5 итераций проверки
            stable_count = 0
            last_count = len(self.albums[media_group_id])
            
            logger.info(f"⏳ Начало ожидания для альбома {media_group_id}, начальное количество: {last_count}")
            
            for iteration in range(max_iterations):
                await asyncio.sleep(self.delay / max_iterations)
                
                current_count = len(self.albums[media_group_id])
                logger.info(
                    f"🔄 Итерация {iteration + 1}/{max_iterations}: "
                    f"собрано {current_count} фото (media_group_id: {media_group_id})"
                )
                
                if current_count == last_count:
                    stable_count += 1
                    # Если количество не менялось 2 раза подряд, считаем что все собрано
                    if stable_count >= 2:
                        logger.info(f"✅ Количество стабилизировалось: {current_count} фото")
                        break
                else:
                    stable_count = 0
                    last_count = current_count
                    logger.info(f"📈 Количество изменилось: {last_count} → {current_count}")

            # Получаем все сообщения альбома
            album_messages = self.albums[media_group_id].copy()

            # Очищаем хранилище
            del self.albums[media_group_id]
            del self.processing[media_group_id]

            # Передаем список сообщений в хендлер через data
            data["album"] = album_messages

            final_count = len(album_messages)
            logger.info(
                f"✅ Альбом собран: {final_count} фото "
                f"(media_group_id: {media_group_id}, "
                f"message_ids: {[msg.message_id for msg in album_messages]})"
            )

            # Вызываем хендлер с первым сообщением, но в data будет album
            return await handler(event, data)

        # Для остальных сообщений альбома ничего не делаем
        # (они уже добавлены в список и будут обработаны первым сообщением)
        return
