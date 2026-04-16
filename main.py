"""Опциональный HTTP-сервер: REST API для внешних клиентов.

Основной контур Telegram-бота в продакшене — `run_bot.py` (long polling).
Запуск API: `uvicorn main:app --host 0.0.0.0 --port 8080`
"""

from fastapi import FastAPI
from loguru import logger

from bot.api.router import router as api_router
from bot.core.config import get_settings
from bot.core.logger import setup_logger
from bot.services.api_bootstrap import init_service_container_for_api

setup_logger()

app = FastAPI(
    title="Virtual Try-On API",
    description="REST API виртуальной примерки (опционально; бот — long polling)",
    version="1.0.0",
)

app.include_router(api_router)


@app.on_event("startup")
async def startup_event() -> None:
    try:
        settings = get_settings()
        logger.info("=" * 60)
        logger.info("Запуск FastAPI (REST API)")
        logger.info(f"Project ID: {settings.google_cloud_project_id}")
        logger.info(f"Region: {settings.google_cloud_region}")
        logger.info("=" * 60)
        await init_service_container_for_api()
        logger.info("Приложение готово к приёму HTTP-запросов")
    except Exception as e:
        logger.error(f"Ошибка при инициализации: {e}")
        logger.exception(e)


@app.get("/")
async def root() -> dict[str, str]:
    """Проверка работоспособности сервиса."""
    return {"status": "ok", "service": "virtual-try-on-api"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check."""
    return {"status": "healthy"}
