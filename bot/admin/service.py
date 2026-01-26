"""Сервис для работы с админ-панелью на базе Telegram Forum Topics."""

import logging
from typing import Optional, List

from aiogram import Bot
from aiogram.types import User, BufferedInputFile, InputMediaPhoto

from bot.admin.topic_storage import BaseTopicStorage

logger = logging.getLogger(__name__)


class AdminPanelService:
    """Сервис для управления админ-панелью через Forum Topics."""

    def __init__(
        self,
        bot: Bot,
        storage: BaseTopicStorage,
        admin_group_id: int,
    ) -> None:
        """
        Инициализирует сервис админ-панели.

        Args:
            bot: Экземпляр Telegram бота
            storage: Хранилище для связей user_id и topic_id
            admin_group_id: ID группы Telegram для админ-панели
        """
        self.bot = bot
        self.storage = storage
        self.admin_group_id = admin_group_id

    async def get_or_create_topic(self, user: User) -> int:
        """
        Получает или создает топик для пользователя.

        Args:
            user: Объект пользователя Telegram

        Returns:
            ID топика (message_thread_id)

        Raises:
            RuntimeError: Если не удалось создать топик и он не существует в хранилище
        """
        user_id = user.id

        # Проверяем, есть ли топик в хранилище
        topic_id = self.storage.get_topic_id(user_id)
        if topic_id is not None:
            logger.debug(
                "Найден существующий топик для user_id=%s: topic_id=%s",
                user_id,
                topic_id,
            )
            return topic_id

        # Создаем новый топик
        topic_name = self._generate_topic_name(user)
        logger.info(
            "Создание нового топика для user_id=%s: %s",
            user_id,
            topic_name,
        )

        try:
            # Создаем топик в админской группе
            forum_topic = await self.bot.create_forum_topic(
                chat_id=self.admin_group_id,
                name=topic_name,
            )

            topic_id = forum_topic.message_thread_id

            # Сохраняем связь в хранилище
            self.storage.save_topic(
                user_id=user_id,
                topic_id=topic_id,
                topic_name=topic_name,
            )

            logger.info(
                "Создан новый топик для user_id=%s: topic_id=%s, name=%s",
                user_id,
                topic_id,
                topic_name,
            )

            return topic_id

        except Exception as e:
            error_msg = (
                f"Ошибка при создании топика для user_id={user_id}: {str(e)}. "
                "Убедитесь, что бот является администратором группы и имеет права на создание топиков."
            )
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

    async def send_model_photo(
        self,
        user: User,
        photo_bytes: bytes,
        caption: str = "Добавлено новое фото модели",
    ) -> None:
        """
        Отправляет фото модели в админ-панель.

        Args:
            user: Объект пользователя Telegram
            photo_bytes: Байты изображения
            caption: Подпись к фото
        """
        try:
            topic_id = await self.get_or_create_topic(user)
            
            photo_file = BufferedInputFile(
                file=photo_bytes,
                filename="model_photo.jpg",
            )
            
            await self.bot.send_photo(
                chat_id=self.admin_group_id,
                photo=photo_file,
                caption=caption,
                message_thread_id=topic_id,
            )
            
            logger.debug(
                "Фото модели отправлено в админ-панель для user_id=%s (topic_id=%s)",
                user.id,
                topic_id,
            )
        except Exception as e:
            logger.error(
                "Ошибка при отправке фото модели в админ-панель для user_id=%s: %s",
                user.id,
                str(e),
                exc_info=True,
            )

    async def send_garment_photo(
        self,
        user: User,
        photo_bytes: bytes,
        caption: str = "Добавлено новое фото одежды",
    ) -> None:
        """
        Отправляет фото одежды в админ-панель.

        Args:
            user: Объект пользователя Telegram
            photo_bytes: Байты изображения
            caption: Подпись к фото
        """
        try:
            topic_id = await self.get_or_create_topic(user)
            
            photo_file = BufferedInputFile(
                file=photo_bytes,
                filename="garment_photo.jpg",
            )
            
            await self.bot.send_photo(
                chat_id=self.admin_group_id,
                photo=photo_file,
                caption=caption,
                message_thread_id=topic_id,
            )
            
            logger.debug(
                "Фото одежды отправлено в админ-панель для user_id=%s (topic_id=%s)",
                user.id,
                topic_id,
            )
        except Exception as e:
            logger.error(
                "Ошибка при отправке фото одежды в админ-панель для user_id=%s: %s",
                user.id,
                str(e),
                exc_info=True,
            )

    async def send_generation_results(
        self,
        user: User,
        result_photos: List[bytes],
        caption: str = "Проведена генерация",
    ) -> None:
        """
        Отправляет результаты генерации в админ-панель.

        Args:
            user: Объект пользователя Telegram
            result_photos: Список байтов результатов генерации
            caption: Подпись к фото (будет добавлена только к первому фото)
        """
        if not result_photos:
            logger.warning("Попытка отправить пустой список результатов генерации")
            return

        try:
            topic_id = await self.get_or_create_topic(user)
            
            if len(result_photos) == 1:
                # Одно фото - отправляем отдельно
                photo_file = BufferedInputFile(
                    file=result_photos[0],
                    filename="generation_result.jpg",
                )
                
                await self.bot.send_photo(
                    chat_id=self.admin_group_id,
                    photo=photo_file,
                    caption=caption,
                    message_thread_id=topic_id,
                )
            else:
                # Несколько фото - отправляем альбомом
                media_group = []
                for idx, photo_bytes in enumerate(result_photos):
                    photo_file = BufferedInputFile(
                        file=photo_bytes,
                        filename=f"generation_result_{idx + 1}.jpg",
                    )
                    # Подпись только к первому фото
                    media_group.append(
                        InputMediaPhoto(
                            media=photo_file,
                            caption=caption if idx == 0 else None,
                        )
                    )
                
                await self.bot.send_media_group(
                    chat_id=self.admin_group_id,
                    media=media_group,
                    message_thread_id=topic_id,
                )
            
            logger.debug(
                "Результаты генерации отправлены в админ-панель для user_id=%s (topic_id=%s, фото: %d)",
                user.id,
                topic_id,
                len(result_photos),
            )
        except Exception as e:
            logger.error(
                "Ошибка при отправке результатов генерации в админ-панель для user_id=%s: %s",
                user.id,
                str(e),
                exc_info=True,
            )

    def _generate_topic_name(self, user: User) -> str:
        """
        Генерирует название топика для пользователя.

        Args:
            user: Объект пользователя Telegram

        Returns:
            Название топика
        """
        # Используем полное имя, если есть, иначе username, иначе ID
        if user.full_name:
            return user.full_name
        elif user.username:
            return f"@{user.username}"
        else:
            return f"User {user.id}"
