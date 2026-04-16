"""Singleton-контейнер глобальных сервисов приложения."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from aiogram import Bot
    from bot.core.config import Settings
    from bot.database.repo_factory import UserRepository
    from bot.services.storage import CloudStorageService
    from bot.services.try_on import VertexTryOnService


class ServiceContainer:
    """Хранит ссылки на уже инициализированные сервисы.

    Заполняется при старте REST API (`init_service_container_for_api`), после чего
    любой модуль может получить сервис без повторной инициализации.
    """

    _instance: Optional[ServiceContainer] = None

    def __init__(self) -> None:
        self.settings: Optional[Settings] = None
        self.bot: Optional[Bot] = None
        self.try_on_service: Optional[VertexTryOnService] = None
        self.storage_service: Optional[CloudStorageService] = None
        self.repo: Optional["UserRepository"] = None

    @classmethod
    def get(cls) -> ServiceContainer:
        """Вернуть единственный экземпляр контейнера."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
