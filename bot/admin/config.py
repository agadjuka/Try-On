"""Конфигурация для админ-панели на базе Telegram Forum Topics."""

import os
from loguru import logger
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()


def get_telegram_admin_group_id() -> int | None:
    """
    Получает ID группы Telegram для админ-панели.
    
    Returns:
        ID группы или None, если не установлен
    """
    logger.info("🔍 Проверка переменной окружения TELEGRAM_ADMIN_GROUP_ID...")
    
    # Проверяем все возможные варианты имени переменной
    group_id_str = (
        os.getenv("TELEGRAM_ADMIN_GROUP_ID") or 
        os.getenv("telegram_admin_group_id") or
        os.getenv("TELEGRAM_ADMIN_GROUP_ID".lower())
    )
    
    if not group_id_str:
        logger.warning("⚠️ TELEGRAM_ADMIN_GROUP_ID не установлен - админ-панель отключена")
        logger.debug(f"🔍 Проверка всех переменных окружения, содержащих 'ADMIN': {[k for k in os.environ.keys() if 'ADMIN' in k.upper()]}")
        return None
    
    # Убираем пробелы и переносы строк
    group_id_str = group_id_str.strip()
    
    try:
        group_id = int(group_id_str)
        logger.success(f"✅ TELEGRAM_ADMIN_GROUP_ID найден: {group_id}")
        return group_id
    except ValueError:
        logger.error(
            f"❌ TELEGRAM_ADMIN_GROUP_ID должен быть числом, получено: '{group_id_str}' (тип: {type(group_id_str).__name__})"
        )
        return None
