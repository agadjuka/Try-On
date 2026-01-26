"""Callback для логирования реальных запросов и ответов LLM."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)

# Путь к папке logs относительно корня проекта
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"


def is_logging_enabled() -> bool:
    """Проверяет, включено ли логирование через переменную окружения LOG_SAVE."""
    log_save = os.getenv("LOG_SAVE", "off").lower().strip()
    return log_save == "on"


def ensure_logs_dir() -> Path:
    """Создает папку logs, если её нет."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR


class LLMLoggingCallback(BaseCallbackHandler):
    """Callback для логирования необработанных запросов и ответов LLM."""
    
    def __init__(self):
        super().__init__()
        self.request_messages = None
        self.response = None
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    
    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        """Вызывается при начале запроса к LLM."""
        # prompts содержит реальные промпты которые отправляются в LLM
        self.request_messages = prompts
        self._log_request(prompts)
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Вызывается при завершении запроса к LLM."""
        # response содержит реальный ответ от LLM
        self.response = response
        self._log_response(response)
    
    def _log_request(self, prompts: list[str]) -> None:
        """Логирует необработанный запрос - только текст промпта без заголовков."""
        if not is_logging_enabled():
            return
        
        try:
            logs_dir = ensure_logs_dir()
            filename = f"llm_request_{self.timestamp}.txt"
            filepath = logs_dir / filename
            
            # Записываем только необработанный текст промпта - что реально отправляется в LLM
            with open(filepath, "w", encoding="utf-8") as f:
                # Объединяем все промпты в один текст
                full_prompt = "\n".join(prompts)
                f.write(full_prompt)
            
        except Exception as e:
            logger.error(f"Ошибка при логировании запроса: {str(e)}", exc_info=True)
    
    def _log_response(self, response: LLMResult) -> None:
        """Логирует необработанный ответ - только текст ответа."""
        if not is_logging_enabled():
            return
        
        try:
            logs_dir = ensure_logs_dir()
            filename = f"llm_response_{self.timestamp}.txt"
            filepath = logs_dir / filename
            
            # Извлекаем текст ответа
            response_text = ""
            if response.generations:
                for generation_list in response.generations:
                    for generation in generation_list:
                        if hasattr(generation, "text"):
                            response_text += generation.text
                        elif hasattr(generation, "message") and hasattr(generation.message, "content"):
                            content = generation.message.content
                            if isinstance(content, str):
                                response_text += content
                            elif isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict) and "text" in item:
                                        response_text += item["text"]
                                    else:
                                        response_text += str(item)
            
            # Записываем только необработанный текст ответа
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(response_text)
            
        except Exception as e:
            logger.error(f"Ошибка при логировании ответа: {str(e)}", exc_info=True)
