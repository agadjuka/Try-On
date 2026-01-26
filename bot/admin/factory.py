"""Фабрика для создания экземпляра сервиса админ-панели."""

from typing import Optional
from loguru import logger

from aiogram import Bot

from bot.admin.config import get_telegram_admin_group_id
from bot.admin.service import AdminPanelService
from bot.admin.topic_storage_factory import get_topic_storage

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
    
    logger.info("🔍 Получение сервиса админ-панели...")
    
    if _admin_service is None:
        logger.info("🔧 Создание нового экземпляра AdminPanelService...")
        admin_group_id = get_telegram_admin_group_id()
        if admin_group_id is None:
            logger.warning("⚠️ Админ-панель не настроена (TELEGRAM_ADMIN_GROUP_ID не установлен)")
            return None

        try:
            logger.info("📦 Получение хранилища топиков...")
            storage = get_topic_storage()
            logger.info(f"🤖 Создание AdminPanelService с admin_group_id={admin_group_id}...")
            _admin_service = AdminPanelService(
                bot=bot,
                storage=storage,
                admin_group_id=admin_group_id,
            )
            logger.success("✅ AdminPanelService успешно инициализирован")
        except Exception as e:
            logger.error(f"❌ Не удалось инициализировать AdminPanelService: {e}", exc_info=True)
            return None
    else:
        logger.debug("ℹ️ Используется существующий экземпляр AdminPanelService")

    return _admin_service
