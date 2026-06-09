"""Модуль для работы с админ-панелью."""

from bot.admin.topic_storage import BaseTopicStorage
from bot.admin.topic_storage_factory import get_topic_storage
from bot.admin.factory import get_admin_service
from bot.admin.service import AdminPanelService

__all__ = [
    "BaseTopicStorage",
    "get_topic_storage",
    "get_admin_service",
    "AdminPanelService",
]
