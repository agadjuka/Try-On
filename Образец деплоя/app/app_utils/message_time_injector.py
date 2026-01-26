"""Вставка контекста времени в сообщения, отправляемые агенту."""

from __future__ import annotations

from typing import Iterable, Sequence

from langchain_core.messages import HumanMessage

from app.app_utils.time_provider import get_moscow_time_tag


def ensure_time_context(messages: Sequence | Iterable) -> list:
    """Возвращает новый список сообщений с вставкой времени в первое HumanMessage.

    Args:
        messages: Последовательность сообщений для агента.

    Returns:
        Новый список, где первое HumanMessage содержит время в начале текста.
    """
    messages_list = list(messages)
    time_tag = get_moscow_time_tag()
    
    # Ищем первое HumanMessage и добавляем время в его начало
    for i, msg in enumerate(messages_list):
        if isinstance(msg, HumanMessage):
            # Создаем новое сообщение с временем в начале
            original_content = msg.content
            if isinstance(original_content, str):
                new_content = f"{time_tag}\n{original_content}"
            else:
                # Если content не строка (например, список для мультимодального контента)
                new_content = original_content
            
            # Создаем новое HumanMessage с обновленным контентом
            messages_list[i] = HumanMessage(content=new_content)
            break
    
    return messages_list

