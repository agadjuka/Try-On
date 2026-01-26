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
    group_id_str = (
        os.getenv("TELEGRAM_ADMIN_GROUP_ID") or 
        os.getenv("telegram_admin_group_id") or
        os.getenv("TELEGRAM_ADMIN_GROUP_ID".lower())
    )
    
    if not group_id_str:
        return None
    
    group_id_str = group_id_str.strip()
    
    try:
        return int(group_id_str)
    except ValueError:
        return None
