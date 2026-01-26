"""
Реестр инструментов для управления списком доступных инструментов.

Этот реестр используется эдитором для получения списка всех инструментов.
При создании нового инструмента необходимо зарегистрировать его здесь.
"""

from typing import Dict, List, Optional
from langchain_core.tools import BaseTool


class ToolsRegistry:
    """Реестр инструментов."""
    
    def __init__(self):
        """Инициализация реестра."""
        self._tools: Dict[str, BaseTool] = {}
        self._load_tools()
    
    def _load_tools(self) -> None:
        """Загружает все инструменты из модулей."""
        try:
            from app.tools.get_services import get_services_tool
            from app.tools.call_manager import call_manager_tool
            
            # Регистрируем все инструменты по их именам
            tools_list = [
                get_services_tool,
                call_manager_tool,
            ]
            
            for tool in tools_list:
                self._tools[tool.name] = tool
                
        except ImportError as e:
            # Если инструменты еще не импортированы, реестр будет пустым
            # Это нормально при первой инициализации
            pass
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Получить инструмент по имени.
        
        Args:
            name: Имя инструмента
            
        Returns:
            Инструмент или None
        """
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """
        Получить список всех зарегистрированных инструментов.
        
        Returns:
            Список всех инструментов
        """
        return list(self._tools.values())


# Глобальный экземпляр реестра
_registry: Optional[ToolsRegistry] = None


def get_registry() -> ToolsRegistry:
    """
    Получить глобальный экземпляр реестра.
    
    Returns:
        Экземпляр реестра инструментов
    """
    global _registry
    if _registry is None:
        _registry = ToolsRegistry()
    return _registry

