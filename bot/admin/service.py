"""Сервис для работы с админ-панелью на базе Telegram Forum Topics."""

import asyncio
from typing import Optional, List
from loguru import logger

from aiogram import Bot
from aiogram.types import User, BufferedInputFile, InputMediaPhoto

from bot.admin.topic_storage import BaseTopicStorage


class AdminPanelService:
    """Сервис для управления админ-панелью через Forum Topics."""

    # Таймаут для операций отправки в админ-панель (30 секунд)
    SEND_TIMEOUT = 30.0

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
        try:
            topic_id = self.storage.get_topic_id(user_id)
            if topic_id is not None:
                return topic_id
        except Exception:
            pass

        # Создаем новый топик
        topic_name = self._generate_topic_name(user)

        try:
            forum_topic = await self.bot.create_forum_topic(
                chat_id=self.admin_group_id,
                name=topic_name,
            )

            topic_id = forum_topic.message_thread_id
            logger.info(f"Топик создан: {topic_name}")

            # Сохраняем связь в хранилище (не критично, если не удастся)
            try:
                self.storage.save_topic(
                    user_id=user_id,
                    topic_id=topic_id,
                    topic_name=topic_name,
                )
            except Exception:
                pass

            # Отправляем первое сообщение с кликабельным ID клиента
            try:
                await self._send_initial_topic_message(user, topic_id)
            except Exception as e:
                logger.warning(f"Не удалось отправить начальное сообщение в топик: {e}")

            return topic_id

        except Exception as e:
            if "topic_id" in locals():
                return topic_id
            raise RuntimeError(f"Ошибка при создании топика: {e}") from e

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
            topic_id = await asyncio.wait_for(
                self.get_or_create_topic(user),
                timeout=self.SEND_TIMEOUT
            )
            
            photo_file = BufferedInputFile(
                file=photo_bytes,
                filename="model_photo.png",
            )
            
            await asyncio.wait_for(
                self.bot.send_photo(
                    chat_id=self.admin_group_id,
                    photo=photo_file,
                    caption=caption,
                    message_thread_id=topic_id,
                ),
                timeout=self.SEND_TIMEOUT
            )
            
            logger.info("Фото модели отправлено в админ-панель")
        except asyncio.TimeoutError:
            logger.error(f"Таймаут отправки фото модели в админ-панель (превышен лимит {self.SEND_TIMEOUT}с)")
        except Exception as e:
            logger.error(f"Ошибка отправки фото модели: {e}")

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
            topic_id = await asyncio.wait_for(
                self.get_or_create_topic(user),
                timeout=self.SEND_TIMEOUT
            )
            
            photo_file = BufferedInputFile(
                file=photo_bytes,
                filename="garment_photo.png",
            )
            
            await asyncio.wait_for(
                self.bot.send_photo(
                    chat_id=self.admin_group_id,
                    photo=photo_file,
                    caption=caption,
                    message_thread_id=topic_id,
                ),
                timeout=self.SEND_TIMEOUT
            )
            
            logger.info("Фото одежды отправлено в админ-панель")
        except asyncio.TimeoutError:
            logger.error(f"Таймаут отправки фото одежды в админ-панель (превышен лимит {self.SEND_TIMEOUT}с)")
        except Exception as e:
            logger.error(f"Ошибка отправки фото одежды: {e}")

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
            return

        try:
            # Получаем или создаем топик с таймаутом
            topic_id = await asyncio.wait_for(
                self.get_or_create_topic(user),
                timeout=self.SEND_TIMEOUT
            )
            
            if len(result_photos) == 1:
                photo_file = BufferedInputFile(
                    file=result_photos[0],
                    filename="generation_result.png",
                )
                
                # Отправляем фото с таймаутом
                await asyncio.wait_for(
                    self.bot.send_photo(
                        chat_id=self.admin_group_id,
                        photo=photo_file,
                        caption=caption,
                        message_thread_id=topic_id,
                    ),
                    timeout=self.SEND_TIMEOUT
                )
            else:
                media_group = []
                for idx, photo_bytes in enumerate(result_photos):
                    photo_file = BufferedInputFile(
                        file=photo_bytes,
                        filename=f"generation_result_{idx + 1}.png",
                    )
                    media_group.append(
                        InputMediaPhoto(
                            media=photo_file,
                            caption=caption if idx == 0 else None,
                        )
                    )
                
                # Отправляем медиа-группу с таймаутом
                await asyncio.wait_for(
                    self.bot.send_media_group(
                        chat_id=self.admin_group_id,
                        media=media_group,
                        message_thread_id=topic_id,
                    ),
                    timeout=self.SEND_TIMEOUT
                )
            
            logger.info(f"Результаты генерации отправлены в админ-панель ({len(result_photos)} фото)")
        except asyncio.TimeoutError:
            logger.error(f"Таймаут отправки результатов генерации в админ-панель (превышен лимит {self.SEND_TIMEOUT}с)")
        except Exception as e:
            logger.error(f"Ошибка отправки результатов генерации: {e}")

    async def _send_initial_topic_message(self, user: User, topic_id: int) -> None:
        """
        Отправляет первое сообщение в топик с кликабельным ID клиента.

        Args:
            user: Объект пользователя Telegram
            topic_id: ID топика
        """
        user_id = user.id
        
        # Формируем кликабельный ID клиента
        if user.username:
            client_link = f'<a href="tg://user?id={user_id}">@{user.username}</a>'
        else:
            client_link = f'<a href="tg://user?id={user_id}">ID: {user_id}</a>'
        
        message_text = f"Клиент: {client_link}"
        
        try:
            await asyncio.wait_for(
                self.bot.send_message(
                    chat_id=self.admin_group_id,
                    text=message_text,
                    message_thread_id=topic_id,
                    parse_mode="HTML",
                ),
                timeout=self.SEND_TIMEOUT
            )
            logger.info(f"Начальное сообщение отправлено в топик {topic_id} для пользователя {user_id}")
        except asyncio.TimeoutError:
            logger.error(f"Таймаут отправки начального сообщения в топик (превышен лимит {self.SEND_TIMEOUT}с)")
        except Exception as e:
            logger.error(f"Ошибка отправки начального сообщения в топик: {e}")
            raise

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
