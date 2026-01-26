"""Сервис для работы с памятью - переключение между Firestore и локальным хранилищем."""

import logging
import os
import pickle
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

logger = logging.getLogger(__name__)


class LocalMemoryBank:
    """Локальное хранилище сообщений в файловой системе."""

    def __init__(self, base_dir: str = ".memory_bank"):
        """Инициализирует локальное хранилище.
        
        Args:
            base_dir: Базовая директория для хранения файлов
        """
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_file_path(self, user_id: str) -> str:
        """Получает путь к файлу для пользователя."""
        return os.path.join(self.base_dir, f"{user_id}.pkl")

    def get_messages(self, user_id: str) -> list[BaseMessage]:
        """Загружает историю сообщений для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список сообщений
        """
        file_path = self._get_file_path(user_id)
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, "rb") as f:
                messages = pickle.load(f)
            return messages
        except Exception as e:
            logger.error("Ошибка при загрузке сообщений из локального хранилища: %s", str(e))
            return []

    def save_messages(self, user_id: str, messages: list[BaseMessage]) -> None:
        """Сохраняет историю сообщений для пользователя.
        
        Args:
            user_id: ID пользователя
            messages: Список сообщений для сохранения
        """
        file_path = self._get_file_path(user_id)
        try:
            with open(file_path, "wb") as f:
                pickle.dump(messages, f)
        except Exception as e:
            logger.error("Ошибка при сохранении сообщений в локальное хранилище: %s", str(e))

    def clear_messages(self, user_id: str) -> None:
        """Очищает историю сообщений для пользователя.
        
        Args:
            user_id: ID пользователя
        """
        file_path = self._get_file_path(user_id)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error("Ошибка при удалении файла сообщений: %s", str(e))


# Глобальный экземпляр локального хранилища
_local_memory_bank: LocalMemoryBank | None = None


def get_memory_service() -> LocalMemoryBank:
    """Получает или создает экземпляр локального хранилища."""
    global _local_memory_bank
    if _local_memory_bank is None:
        base_dir = os.getenv("MEMORY_BANK_DIR", ".memory_bank")
        _local_memory_bank = LocalMemoryBank(base_dir=base_dir)
    return _local_memory_bank


def get_memory_type() -> str:
    """Определяет тип памяти из переменной окружения.
    
    Returns:
        "firestore" или "local"
    """
    memory_type = os.getenv("MEMORY_TYPE", "firestore").lower()
    if memory_type not in ("firestore", "local"):
        logger.warning("Неизвестный тип памяти: %s. Используется firestore", memory_type)
        return "firestore"
    return memory_type


def is_local_memory() -> bool:
    """Проверяет, используется ли локальная память."""
    return get_memory_type() == "local"


