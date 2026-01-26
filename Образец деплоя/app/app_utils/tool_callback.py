"""Callback для логирования вызовов инструментов в момент их выполнения."""
import logging
from typing import Any, Dict

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)


class ToolCallCallback(BaseCallbackHandler):
    """Callback для логирования вызовов инструментов."""
    
    def __init__(self):
        super().__init__()
        self._current_tool_name = None
    
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: str,
        parent_run_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Вызывается при старте выполнения инструмента."""
        # Извлекаем имя инструмента из serialized
        tool_name = "unknown"
        if "name" in serialized:
            tool_name = serialized["name"]
        elif "id" in serialized:
            tool_id = serialized["id"]
            if isinstance(tool_id, list) and tool_id:
                tool_name = tool_id[-1]
            else:
                tool_name = str(tool_id)
        
        # Парсим input_str если это JSON
        try:
            import json
            args = json.loads(input_str) if input_str else {}
        except:
            args = input_str
        
        args_str = str(args)[:150] + "..." if len(str(args)) > 150 else str(args)
        logger.info("🔧 Tool вызван: %s | args: %s", tool_name, args_str)
        # Сохраняем имя инструмента для on_tool_end
        self._current_tool_name = tool_name
    
    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: str,
        parent_run_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Вызывается при завершении выполнения инструмента."""
        tool_name = getattr(self, "_current_tool_name", "unknown")
        
        # Обрабатываем разные типы output
        if output is None:
            output_str = "None"
        elif hasattr(output, "content"):
            # Если это ToolMessage или другой объект с content
            content = getattr(output, "content", None)
            output_str = str(content) if content is not None else str(output)
        elif isinstance(output, str):
            output_str = output
        else:
            # Для других типов просто преобразуем в строку
            output_str = str(output)
        
        # Компактный вывод результата
        output_preview = output_str[:150] + "..." if len(output_str) > 150 else output_str
        logger.info("✅ Tool ответ: %s | result: %s", tool_name, output_preview)
    
    def on_tool_error(
        self,
        error: Exception,
        *,
        run_id: str,
        parent_run_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Вызывается при ошибке выполнения инструмента."""
        tool_name = kwargs.get("name", "unknown")
        logger.error("❌ Tool ошибка: %s | error: %s", tool_name, str(error))

