"""Утилиты для работы с сообщениями."""

from langchain_core.messages import AIMessage, BaseMessage


def is_message_empty(msg: BaseMessage) -> bool:
    """Проверяет, является ли сообщение пустым (без контента)."""
    # Если у AIMessage есть tool_calls, сообщение не пустое, даже если content пустой
    if isinstance(msg, AIMessage):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            return False
    
    if not hasattr(msg, "content"):
        return True
    
    content = msg.content
    if content is None:
        return True
    
    # Если content - список (мультимодальный контент), проверяем, что он не пустой
    if isinstance(content, list):
        return len(content) == 0
    
    # Если content - строка, проверяем, что она не пустая после strip
    if isinstance(content, str):
        return not content.strip()
    
    # Для других типов считаем пустым, если это пустая строка
    return not str(content).strip()


def filter_empty_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Фильтрует пустые сообщения из списка."""
    return [msg for msg in messages if not is_message_empty(msg)]

