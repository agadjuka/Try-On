"""Скрипт для локального запуска Telegram бота в режиме polling."""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from bot.core.config import get_settings
from bot.core.logger import setup_logger
from bot.database.repo_factory import create_user_repo
from bot.handlers.router import setup_handlers
from bot.services.storage import CloudStorageService
from bot.services.try_on import VertexTryOnService


async def main() -> None:
    """Основная функция запуска бота в режиме polling."""
    setup_logger()
    logger.info("Запуск Telegram бота в режиме polling...")

    # Загружаем настройки
    try:
        settings = get_settings()
    except Exception as e:
        logger.error(
            f"Ошибка загрузки настроек: {e}\n"
            "Убедитесь, что файл .env существует и содержит все необходимые переменные:\n"
            "- BOT_TOKEN\n"
            "- GEMINI_API_KEY\n"
            "- ORACLE_S3_ENDPOINT / ORACLE_S3_REGION\n"
            "- ORACLE_ACCESS_KEY_ID / ORACLE_SECRET_ACCESS_KEY\n"
            "- ORACLE_BUCKET_NAME"
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

    logger.info(
        f"Конфигурация загружена. Storage: {settings.storage_backend}, "
        f"Try-on provider: {settings.try_on_provider}"
    )
    if settings.try_on_provider == "gemini":
        logger.info(f"Try-on model: {settings.gemini_model}")
    else:
        logger.info(
            "Try-on model: "
            f"{settings.openai_image_model} "
            f"(quality={settings.openai_image_quality}, size={settings.openai_image_size})"
        )
    if settings.google_cloud_project_id and settings.google_cloud_region:
        logger.info(
            "Google Cloud config enabled: "
            f"project={settings.google_cloud_project_id}, region={settings.google_cloud_region}"
        )
    else:
        logger.info("Google Cloud config не задан; GCS/Firestore недоступны")
    logger.info(
        f"БД: {settings.database_backend}"
        + (
            f" ({settings.sqlite_path})"
            if settings.database_backend == "sqlite"
            else ""
        )
    )

    # Инициализируем сервисы
    repo = create_user_repo(settings)
    storage_service = CloudStorageService(settings)
    try_on_service = VertexTryOnService(settings)

    # Создаем бота и диспетчер
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Настраиваем хендлеры
    setup_handlers(
        router=dp,
        bot=bot,
        repo=repo,
        storage_service=storage_service,
        try_on_service=try_on_service,
    )

    try:
        logger.info("Проверка подключения к Telegram API...")
        me = await bot.get_me()
        logger.success(f"Бот успешно подключен: @{me.username} ({me.first_name})")

        # После миграции с webhook снимаем webhook и очищаем очередь апдейтов
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook отключён (режим long polling)")

        logger.info("Бот запущен в режиме polling и готов к работе")
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
