"""Точка входа для Telegram бота в режиме webhook (Cloud Run)."""

import logging
import os

from fastapi import BackgroundTasks, FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.telegram.bot import process_update

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Создаем FastAPI приложение
app = FastAPI(
    title="Telegram Bot Webhook",
    description="Webhook endpoint для Telegram бота",
    version="1.0.0",
)


@app.get("/")
async def root() -> dict[str, str]:
    """Проверка работоспособности сервиса."""
    return {"status": "ok", "service": "telegram-bot-webhook"}


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
        
        # Получаем токен бота из переменных окружения
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Bot token not configured"},
            )
        
        # Логируем получение обновления
        update_id = update_data.get("update_id", "unknown")
        logger.info("Получено обновление от Telegram: update_id=%s", update_id)
        
        # Добавляем обработку в фоновые задачи
        # Это позволяет немедленно вернуть ответ Telegram, не дожидаясь обработки
        background_tasks.add_task(process_update, update_data, bot_token)
        
        # Немедленно возвращаем успешный ответ
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ok"},
        )
        
    except Exception as e:
        # Логируем ошибку, но все равно возвращаем 200 OK
        # Это важно, чтобы Telegram не повторял запрос
        logger.error("Ошибка при получении webhook запроса: %s", str(e), exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "error", "message": str(e)},
        )

