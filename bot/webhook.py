"""Модуль для обработки обновлений от Telegram в режиме webhook."""

from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from loguru import logger

from bot.core.config import get_settings
from bot.database.repo import FirestoreRepo
from bot.handlers.router import setup_handlers
from bot.services.container import ServiceContainer
from bot.services.storage import CloudStorageService
from bot.services.try_on import VertexTryOnService
from bot.services.upscale import UpscaleService

# Глобальные объекты для переиспользования в webhook режиме
_webhook_bot: Bot | None = None
_webhook_dispatcher: Dispatcher | None = None
_webhook_repo: FirestoreRepo | None = None
_webhook_storage_service: CloudStorageService | None = None
_webhook_try_on_service: VertexTryOnService | None = None
_webhook_upscale_service: UpscaleService | None = None
_initialized: bool = False


async def init_webhook_services() -> None:
    """Инициализирует все сервисы при старте приложения.
    
    Вызывается из startup_event FastAPI для предварительной инициализации,
    чтобы избежать cold start задержек при первом запросе.
    """
    global _webhook_bot, _webhook_dispatcher, _initialized
    global _webhook_repo, _webhook_storage_service, _webhook_try_on_service, _webhook_upscale_service
    
    if _initialized:
        logger.info("ℹ️ Сервисы уже инициализированы")
        return
    
    logger.info("🔧 Инициализация сервисов...")
    
    # Загружаем настройки
    settings = get_settings()
    logger.info("✅ Настройки загружены")
    
    # Создаем бота и диспетчер
    logger.info("🤖 Создание бота и диспетчера...")
    _webhook_bot = Bot(token=settings.bot_token)
    _webhook_dispatcher = Dispatcher(storage=MemoryStorage())
    
    # Инициализируем сервисы
    logger.info("💾 Инициализация Firestore репозитория...")
    _webhook_repo = FirestoreRepo(settings)
    
    logger.info("☁️ Инициализация Cloud Storage сервиса...")
    _webhook_storage_service = CloudStorageService(settings)
    
    logger.info("🎨 Инициализация Try-On сервиса...")
    _webhook_try_on_service = VertexTryOnService(settings)
    
    logger.info("🔍 Инициализация Upscale сервиса...")
    _webhook_upscale_service = UpscaleService(settings)
    
    # Настраиваем хендлеры
    logger.info("📋 Настройка хендлеров...")
    setup_handlers(
        router=_webhook_dispatcher,
        bot=_webhook_bot,
        repo=_webhook_repo,
        storage_service=_webhook_storage_service,
        try_on_service=_webhook_try_on_service,
        upscale_service=_webhook_upscale_service,
    )
    
    # Наполняем ServiceContainer — он используется REST API модулем
    container = ServiceContainer.get()
    container.settings = settings
    container.bot = _webhook_bot
    container.try_on_service = _webhook_try_on_service
    container.storage_service = _webhook_storage_service
    container.repo = _webhook_repo

    _initialized = True
    logger.info("✅ Все сервисы успешно инициализированы")


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
    update_id = update_data.get("update_id", "unknown")
    try:
        logger.info(f"🔄 Начало обработки обновления: update_id={update_id}")
        
        # Получаем Bot и Dispatcher
        bot, dispatcher = await get_webhook_dispatcher()
        
        # Преобразуем словарь в Update объект
        update = Update(**update_data)
        
        # Обрабатываем обновление через Dispatcher
        await dispatcher.feed_update(bot, update)
        
        logger.info(f"✅ Обновление успешно обработано: update_id={update_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке обновления {update_id}: {e}")
        logger.exception(e)
