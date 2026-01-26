"""Точка входа для запуска Telegram бота."""

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from app.telegram.bot import TelegramBot

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Главная функция для запуска бота."""
    # Переходим в папку скрипта
    script_dir = Path(__file__).parent.parent.parent
    os.chdir(script_dir)

    # Загружаем переменные из .env файла
    env_path = script_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Загружены переменные из {env_path}")
    else:
        logger.warning(f"Файл .env не найден в {script_dir}")

    # Устанавливаем PYTHONPATH
    os.environ["PYTHONPATH"] = str(script_dir)

    # Получаем токен из переменной окружения
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error(
            "Токен Telegram бота не найден. "
            "Установите переменную окружения TELEGRAM_BOT_TOKEN"
        )
        sys.exit(1)

    # Создаем и запускаем бота
    bot = TelegramBot(token=token)
    try:
        await bot.start_polling()
        # Ожидаем бесконечно, пока бот работает
        stop_event = asyncio.Event()
        await stop_event.wait()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())

