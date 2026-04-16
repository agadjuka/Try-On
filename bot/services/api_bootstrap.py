"""Инициализация ServiceContainer для REST API (без Telegram webhook / polling)."""

from aiogram import Bot
from loguru import logger

from bot.core.config import get_settings
from bot.database.repo import FirestoreRepo
from bot.services.container import ServiceContainer
from bot.services.storage import CloudStorageService
from bot.services.try_on import VertexTryOnService


async def init_service_container_for_api() -> None:
    """Заполняет ServiceContainer для FastAPI `/api/v1`.

    Bot создаётся для опциональных уведомлений в админ-панель из фоновых задач API.
    """
    settings = get_settings()
    logger.info("Инициализация сервисов для REST API...")

    repo = FirestoreRepo(settings)
    storage_service = CloudStorageService(settings)
    try_on_service = VertexTryOnService(settings)
    bot = Bot(token=settings.bot_token)

    container = ServiceContainer.get()
    container.settings = settings
    container.bot = bot
    container.repo = repo
    container.storage_service = storage_service
    container.try_on_service = try_on_service

    logger.info("ServiceContainer для REST API готов")
