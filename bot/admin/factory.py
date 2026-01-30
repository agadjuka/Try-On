"""Фабрика для создания экземпляра сервиса админ-панели."""

from typing import Optional
from loguru import logger

from aiogram import Bot

from bot.admin.config import get_telegram_admin_group_id
from bot.admin.service import AdminPanelService
from bot.admin.topic_storage_factory import get_topic_storage
from bot.core.config import get_settings

# Глобальный экземпляр сервиса
_admin_service: Optional[AdminPanelService] = None


def get_admin_service(bot: Bot) -> Optional[AdminPanelService]:
    """
    Получает или создает экземпляр AdminPanelService.
    
    Args:
        bot: Экземпляр Telegram бота
        
    Returns:
        Экземпляр AdminPanelService или None, если админ-панель не настроена
    """
    global _admin_service
    
    if _admin_service is None:
        admin_group_id = get_telegram_admin_group_id()
        if admin_group_id is None:
            return None

        try:
            settings = get_settings()
            storage = get_topic_storage()
            _admin_service = AdminPanelService(
                bot=bot,
                storage=storage,
                admin_group_id=admin_group_id,
                forwarding_enabled=settings.admin_panel_forwarding_enabled,
            )
        except Exception as e:
            logger.error(f"Ошибка инициализации AdminPanelService: {e}")
            return None

    return _admin_service
