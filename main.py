"""Точка входа для Telegram бота в режиме webhook (Cloud Run)."""

import logging

from fastapi import BackgroundTasks, FastAPI, Request, status
from fastapi.responses import JSONResponse
from loguru import logger

from bot.core.config import get_settings
from bot.core.logger import setup_logger
from bot.webhook import process_update

# Настройка логирования
setup_logger()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Создаем FastAPI приложение
app = FastAPI(
    title="Virtual Try-On Bot",
    description="Webhook endpoint для Telegram бота виртуальной примерки",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения."""
    try:
        settings = get_settings()
        logger.info(f"Приложение запущено. Project ID: {settings.google_cloud_project_id}")
    except Exception as e:
        logger.error(f"Ошибка при инициализации: {e}")


@app.get("/")
async def root() -> dict[str, str]:
    """Проверка работоспособности сервиса."""
    return {"status": "ok", "service": "virtual-try-on-bot"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint для Cloud Run."""
    return {"status": "healthy"}


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request, background_tasks: BackgroundTasks
) -> JSONResponse:
    """Эндпоинт для получения обновлений от Telegram.
    
    Telegram отправляет POST-запросы с объектом Update в JSON.
    Эндпоинт немедленно возвращает 200 OK, а обработка запускается в фоне.
    
    Args:
        request: HTTP запрос от Telegram
        background_tasks: Фоновые задачи FastAPI
        
    Returns:
        JSONResponse с кодом 200 OK
    """
    try:
        # Получаем данные обновления из запроса
        update_data = await request.json()
        
        # Проверяем наличие токена бота
        try:
            settings = get_settings()
            if not settings.bot_token or not settings.bot_token.strip():
                logger.error("BOT_TOKEN не установлен в переменных окружения")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"error": "Bot token not configured"},
                )
        except Exception as e:
            logger.error(f"Ошибка загрузки настроек: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Configuration error"},
            )
        
        # Логируем получение обновления
        update_id = update_data.get("update_id", "unknown")
        logger.info(f"Получено обновление от Telegram: update_id={update_id}")
        
        # Добавляем обработку в фоновые задачи
        # Это позволяет немедленно вернуть ответ Telegram, не дожидаясь обработки
        background_tasks.add_task(process_update, update_data)
        
        # Немедленно возвращаем успешный ответ
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ok"},
        )
        
    except Exception as e:
        # Логируем ошибку, но все равно возвращаем 200 OK
        # Это важно, чтобы Telegram не повторял запрос
        logger.error(f"Ошибка при получении webhook запроса: {e}")
        logger.exception(e)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "error", "message": str(e)},
        )
