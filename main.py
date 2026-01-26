"""Основной файл для запуска Telegram бота."""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from bot.core.config import get_settings
from bot.core.logger import setup_logger
from bot.database.repo import FirestoreRepo
from bot.handlers.router import setup_handlers
from bot.services.storage import CloudStorageService


async def main() -> None:
    """Основная функция запуска бота."""
    setup_logger()
    logger.info("Запуск Telegram бота...")

    # Загружаем настройки
    try:
        settings = get_settings()
    except Exception as e:
        logger.error(
            f"Ошибка загрузки настроек: {e}\n"
            "Убедитесь, что файл .env существует и содержит все необходимые переменные:\n"
            "- BOT_TOKEN\n"
            "- GOOGLE_CLOUD_PROJECT_ID\n"
            "- GOOGLE_CLOUD_REGION\n"
            "- GCS_BUCKET_NAME"
        )
        return

    # Проверяем наличие токена
    if not settings.bot_token or not settings.bot_token.strip():
        logger.error(
            "BOT_TOKEN не найден или пустой в файле .env\n"
            "Получите токен у @BotFather в Telegram и добавьте в .env файл:\n"
            "BOT_TOKEN=ваш_токен_бота"
        )
        return

    logger.info(f"Конфигурация загружена. Project ID: {settings.google_cloud_project_id}")

    # Инициализируем сервисы
    repo = FirestoreRepo(settings)
    storage_service = CloudStorageService(settings)

    # Создаем бота и диспетчер
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Настраиваем хендлеры
    setup_handlers(
        router=dp,
        bot=bot,
        repo=repo,
        storage_service=storage_service,
    )

    try:
        logger.info("Проверка подключения к Telegram API...")
        # Проверяем подключение перед запуском polling
        me = await bot.get_me()
        logger.success(f"Бот успешно подключен: @{me.username} ({me.first_name})")
        
        logger.info("Бот запущен и готов к работе")
        await dp.start_polling(bot)
    except TelegramUnauthorizedError:
        logger.error(
            "Ошибка авторизации: неверный токен бота\n"
            "Проверьте BOT_TOKEN в файле .env:\n"
            "1. Получите новый токен у @BotFather в Telegram\n"
            "2. Убедитесь, что токен скопирован полностью без пробелов\n"
            "3. Формат в .env: BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        )
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        logger.exception(e)
    finally:
        await bot.session.close()
        await repo.close()


if __name__ == "__main__":
    asyncio.run(main())
