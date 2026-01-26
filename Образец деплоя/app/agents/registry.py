"""
Реестр агентов для управления списком доступных агентов.

Этот реестр используется эдитором для получения списка всех агентов.
При создании нового агента необходимо зарегистрировать его здесь.
"""

from typing import Dict, List, Optional
from pathlib import Path


class AgentRegistry:
    """Реестр агентов."""
    
    def __init__(self):
        """Инициализация реестра."""
        self._agents: Dict[str, Dict[str, str]] = {}
        self._load_agents()
    
    def _load_agents(self) -> None:
        """Загружает информацию об агентах из реестра."""
        # Регистрация всех агентов
        # Формат: ключ -> {имя файла, читаемое имя}
        
        self._agents = {
            "morning": {
                "file": "morning_stage.py",
                "name": "Утренний агент",
            },
            "evening": {
                "file": "evening_stage.py",
                "name": "Вечерний агент",
            },
        }
    
    def get_agent_info(self, key: str) -> Optional[Dict[str, str]]:
        """
        Получить информацию об агенте по ключу.
        
        Args:
            key: Ключ агента (например, "greeting")
            
        Returns:
            Словарь с информацией об агенте или None
        """
        return self._agents.get(key)
    
    def get_all_agents(self) -> List[Dict[str, str]]:
        """
        Получить список всех зарегистрированных агентов.
        
        Returns:
            Список словарей с информацией об агентах
        """
        return [
            {"key": key, **info}
            for key, info in self._agents.items()
        ]
    
    def get_agent_file(self, key: str) -> Optional[str]:
        """
        Получить имя файла агента по ключу.
        
        Args:
            key: Ключ агента
            
        Returns:
            Имя файла или None
        """
        info = self.get_agent_info(key)
        return info.get("file") if info else None


# Глобальный экземпляр реестра
_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """
    Получить глобальный экземпляр реестра.
    
    Returns:
        Экземпляр реестра агентов
    """
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry

