"""Сервис для работы с админ-панелью на базе Telegram Forum Topics."""

from typing import Optional, List
from loguru import logger

from aiogram import Bot
from aiogram.types import User, BufferedInputFile, InputMediaPhoto

from bot.admin.topic_storage import BaseTopicStorage


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
        logger.info(f"🔍 Получение или создание топика для user_id={user_id}...")

        # Проверяем, есть ли топик в хранилище (не критично, если не удастся - просто создадим новый)
        logger.info(f"📋 Проверка существующего топика для user_id={user_id} в хранилище...")
        try:
            topic_id = self.storage.get_topic_id(user_id)
            if topic_id is not None:
                logger.success(
                    f"✅ Найден существующий топик для user_id={user_id}: topic_id={topic_id}"
                )
                return topic_id
        except Exception as storage_error:
            # Ошибка чтения из Firestore не критична - просто создадим новый топик
            logger.warning(
                f"⚠️ Не удалось проверить существующий топик в Firestore для user_id={user_id}: {storage_error}. "
                "Продолжаем создание нового топика."
            )

        # Создаем новый топик
        topic_name = self._generate_topic_name(user)
        logger.info(
            f"🆕 Создание нового топика для user_id={user_id}: '{topic_name}' в группе {self.admin_group_id}"
        )

        try:
            # Создаем топик в админской группе
            logger.info(f"📤 Отправка запроса на создание топика в Telegram API...")
            forum_topic = await self.bot.create_forum_topic(
                chat_id=self.admin_group_id,
                name=topic_name,
            )

            topic_id = forum_topic.message_thread_id
            logger.success(f"✅ Топик успешно создан в Telegram: topic_id={topic_id}")

            # Сохраняем связь в хранилище (не критично, если не удастся - топик уже создан)
            logger.info(f"💾 Сохранение связи user_id={user_id} -> topic_id={topic_id} в хранилище...")
            try:
                self.storage.save_topic(
                    user_id=user_id,
                    topic_id=topic_id,
                    topic_name=topic_name,
                )
                logger.success(
                    f"✅ Топик полностью создан и сохранен: user_id={user_id}, topic_id={topic_id}, name='{topic_name}'"
                )
            except Exception as storage_error:
                # Ошибка сохранения в Firestore не критична - топик уже создан в Telegram
                logger.warning(
                    f"⚠️ Топик создан в Telegram (topic_id={topic_id}), но не удалось сохранить в Firestore: {storage_error}. "
                    "Топик будет работать, но при следующем запуске будет создан новый топик."
                )

            return topic_id

        except Exception as e:
            # Проверяем, не связана ли ошибка с созданием топика в Telegram
            if "topic_id" in locals() and "forum_topic" in locals():
                # Топик создан, но что-то пошло не так - возвращаем topic_id
                logger.warning(
                    f"⚠️ Топик создан в Telegram (topic_id={topic_id}), но возникла ошибка: {e}. "
                    "Возвращаем topic_id несмотря на ошибку."
                )
                return topic_id
            
            error_msg = (
                f"Ошибка при создании топика для user_id={user_id}: {str(e)}. "
                "Убедитесь, что бот является администратором группы и имеет права на создание топиков."
            )
            logger.error(f"❌ {error_msg}", exc_info=True)
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
            logger.info(f"📸 Отправка фото модели для user_id={user.id} в админ-панель...")
            topic_id = await self.get_or_create_topic(user)
            logger.info(f"✅ Топик получен: topic_id={topic_id}, размер фото: {len(photo_bytes)} байт")
            
            photo_file = BufferedInputFile(
                file=photo_bytes,
                filename="model_photo.jpg",
            )
            
            logger.info(f"📤 Отправка фото в группу {self.admin_group_id}, топик {topic_id}...")
            await self.bot.send_photo(
                chat_id=self.admin_group_id,
                photo=photo_file,
                caption=caption,
                message_thread_id=topic_id,
            )
            
            logger.success(
                f"✅ Фото модели успешно отправлено в админ-панель для user_id={user.id} (topic_id={topic_id})"
            )
        except Exception as e:
            logger.error(
                f"❌ Ошибка при отправке фото модели в админ-панель для user_id={user.id}: {e}",
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
            logger.info(f"👕 Отправка фото одежды для user_id={user.id} в админ-панель...")
            topic_id = await self.get_or_create_topic(user)
            logger.info(f"✅ Топик получен: topic_id={topic_id}, размер фото: {len(photo_bytes)} байт")
            
            photo_file = BufferedInputFile(
                file=photo_bytes,
                filename="garment_photo.jpg",
            )
            
            logger.info(f"📤 Отправка фото в группу {self.admin_group_id}, топик {topic_id} с подписью: '{caption}'...")
            await self.bot.send_photo(
                chat_id=self.admin_group_id,
                photo=photo_file,
                caption=caption,
                message_thread_id=topic_id,
            )
            
            logger.success(
                f"✅ Фото одежды успешно отправлено в админ-панель для user_id={user.id} (topic_id={topic_id})"
            )
        except Exception as e:
            logger.error(
                f"❌ Ошибка при отправке фото одежды в админ-панель для user_id={user.id}: {e}",
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
            logger.warning("⚠️ Попытка отправить пустой список результатов генерации")
            return

        try:
            logger.info(f"🎨 Отправка результатов генерации для user_id={user.id} в админ-панель ({len(result_photos)} фото)...")
            topic_id = await self.get_or_create_topic(user)
            logger.info(f"✅ Топик получен: topic_id={topic_id}")
            
            if len(result_photos) == 1:
                # Одно фото - отправляем отдельно
                logger.info(f"📤 Отправка одного фото результата ({len(result_photos[0])} байт)...")
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
                logger.success(f"✅ Одно фото результата отправлено")
            else:
                # Несколько фото - отправляем альбомом
                logger.info(f"📤 Подготовка альбома из {len(result_photos)} фото...")
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
                
                logger.info(f"📤 Отправка альбома в группу {self.admin_group_id}, топик {topic_id}...")
                await self.bot.send_media_group(
                    chat_id=self.admin_group_id,
                    media=media_group,
                    message_thread_id=topic_id,
                )
                logger.success(f"✅ Альбом из {len(result_photos)} фото отправлен")
            
            logger.success(
                f"✅ Результаты генерации успешно отправлены в админ-панель для user_id={user.id} (topic_id={topic_id}, фото: {len(result_photos)})"
            )
        except Exception as e:
            logger.error(
                f"❌ Ошибка при отправке результатов генерации в админ-панель для user_id={user.id}: {e}",
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
