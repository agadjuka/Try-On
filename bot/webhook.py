"""Модуль для обработки обновлений от Telegram в режиме webhook."""

import logging
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from loguru import logger

from bot.core.config import get_settings
from bot.database.repo import FirestoreRepo
from bot.handlers.router import setup_handlers
from bot.services.storage import CloudStorageService
from bot.services.try_on import VertexTryOnService

# Глобальные объекты для переиспользования в webhook режиме
_webhook_bot: Bot | None = None
_webhook_dispatcher: Dispatcher | None = None
_webhook_repo: FirestoreRepo | None = None
_webhook_storage_service: CloudStorageService | None = None
_webhook_try_on_service: VertexTryOnService | None = None
_initialized: bool = False


async def init_webhook_services() -> None:
    """Инициализирует все сервисы при старте приложения.
    
    Вызывается из startup_event FastAPI для предварительной инициализации,
    чтобы избежать cold start задержек при первом запросе.
    """
    global _webhook_bot, _webhook_dispatcher, _initialized
    global _webhook_repo, _webhook_storage_service, _webhook_try_on_service
    
    if _initialized:
        return
    
    logger.info("Инициализация сервисов при старте приложения...")
    
    # Загружаем настройки
    settings = get_settings()
    
    # Создаем бота и диспетчер
    _webhook_bot = Bot(token=settings.bot_token)
    _webhook_dispatcher = Dispatcher(storage=MemoryStorage())
    
    # Инициализируем сервисы
    _webhook_repo = FirestoreRepo(settings)
    _webhook_storage_service = CloudStorageService(settings)
    _webhook_try_on_service = VertexTryOnService(settings)
    
    # Настраиваем хендлеры
    setup_handlers(
        router=_webhook_dispatcher,
        bot=_webhook_bot,
        repo=_webhook_repo,
        storage_service=_webhook_storage_service,
        try_on_service=_webhook_try_on_service,
    )
    
    _initialized = True
    logger.info("Сервисы успешно инициализированы при старте")


async def get_webhook_dispatcher() -> tuple[Bot, Dispatcher]:
    """Получает или создает глобальные объекты Bot и Dispatcher для webhook режима.
    
    Returns:
        Кортеж (Bot, Dispatcher) для обработки обновлений
    """
    global _webhook_bot, _webhook_dispatcher
    
    # Если объекты еще не инициализированы, инициализируем
    if not _initialized:
        await init_webhook_services()
    
    return _webhook_bot, _webhook_dispatcher


async def process_update(update_data: dict[str, Any]) -> None:
    """Обрабатывает обновление от Telegram в формате JSON.
    
    Args:
        update_data: Обновление от Telegram в формате словаря (JSON)
    """
    try:
        # Получаем Bot и Dispatcher
        bot, dispatcher = await get_webhook_dispatcher()
        
        # Преобразуем словарь в Update объект
        update = Update(**update_data)
        
        # Обрабатываем обновление через Dispatcher
        await dispatcher.feed_update(bot, update)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке обновления: {e}")
        logger.exception(e)
