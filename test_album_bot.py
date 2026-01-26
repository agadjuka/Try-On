"""Тестовый бот для проверки обработки альбомов."""

import asyncio
from typing import List, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from loguru import logger

from bot.core.config import get_settings
from bot.core.logger import setup_logger
from bot.middlewares.album import AlbumMiddleware


async def handle_photo(
    message: Message,
    album: Optional[List[Message]] = None,
) -> None:
    """
    Обработчик фото для тестирования альбомов.

    Args:
        message: Сообщение с фото
        album: Список сообщений из альбома (если есть)
    """
    if album:
        # Это альбом
        photo_count = len(album)
        logger.info(f"📸 АЛЬБОМ: получено {photo_count} фото")
        logger.info(f"   Media group ID: {album[0].media_group_id}")
        logger.info(f"   Message IDs: {[msg.message_id for msg in album]}")
        
        await message.answer(
            f"✅ Альбом обработан!\n\n"
            f"📸 Получено фото: {photo_count}\n"
            f"🆔 Media Group ID: {album[0].media_group_id}\n"
            f"📋 Message IDs: {', '.join(str(msg.message_id) for msg in album)}"
        )
    else:
        # Одно фото
        logger.info("📸 ОДНО ФОТО: получено 1 фото")
        logger.info(f"   Message ID: {message.message_id}")
        logger.info(f"   Media group ID: {message.media_group_id}")
        
        await message.answer(
            f"✅ Одно фото обработано!\n\n"
            f"📸 Получено фото: 1\n"
            f"🆔 Message ID: {message.message_id}\n"
            f"📋 Media Group ID: {message.media_group_id or 'нет (не альбом)'}"
        )


async def start_command(message: Message) -> None:
    """Обработчик команды /start."""
    await message.answer(
        "🧪 Тестовый бот для проверки альбомов\n\n"
        "Отправьте одно фото или несколько фото альбомом.\n"
        "Бот покажет, сколько фото получено."
    )


async def main() -> None:
    """Основная функция запуска тестового бота."""
    setup_logger()
    logger.info("Запуск тестового бота для проверки альбомов...")

    # Загружаем настройки
    try:
        settings = get_settings()
    except Exception as e:
        logger.error(f"Ошибка загрузки настроек: {e}")
        return

    if not settings.bot_token:
        logger.error("BOT_TOKEN не найден в .env")
        return

    # Создаем бота и диспетчер
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем middleware для альбомов
    album_middleware = AlbumMiddleware(delay=1.5)
    dp.message.middleware(album_middleware)

    # Регистрируем хендлеры
    dp.message.register(start_command, Command("start"))
    dp.message.register(handle_photo, F.photo)

    try:
        logger.info("Проверка подключения к Telegram API...")
        me = await bot.get_me()
        logger.success(f"Тестовый бот подключен: @{me.username} ({me.first_name})")
        logger.info("Бот готов к тестированию. Отправьте фото для проверки.")
        
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        logger.exception(e)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
