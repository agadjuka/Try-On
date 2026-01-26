"""Утилиты для обработки CallManager tool_calls."""

from typing import Optional

from langchain_core.messages import AIMessage


def extract_call_manager_reason(message: AIMessage) -> Optional[str]:
    """
    Извлекает reason из tool_calls сообщения, если был вызван call_manager_tool.
    
    Args:
        message: AIMessage с возможными tool_calls
        
    Returns:
        reason из args или None, если CallManager не был вызван
    """
    if not isinstance(message, AIMessage):
        return None
    
    if not hasattr(message, "tool_calls") or not message.tool_calls:
        return None
    
    for tool_call in message.tool_calls:
        tool_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
        if tool_name == "call_manager_tool":
            args = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", {})
            reason = args.get("reason", "-") if isinstance(args, dict) else "-"
            return reason
    
    return None


def set_call_manager_content_if_empty(message: AIMessage) -> None:
    """
    Устанавливает content из reason, если content пустой и был вызван CallManager.
    
    Args:
        message: AIMessage для обработки (изменяется in-place)
    """
    if not isinstance(message, AIMessage):
        return
    
    # Проверяем, что content пустой (отсутствует или пустая строка)
    if message.content and isinstance(message.content, str) and message.content.strip():
        return
    
    # Извлекаем reason из tool_calls
    reason = extract_call_manager_reason(message)
    if reason:
        message.content = reason


def check_call_manager_in_messages(messages: list) -> Optional[dict]:
    """
    Проверяет наличие CallManager в списке сообщений.
    
    Args:
        messages: Список сообщений для проверки
        
    Returns:
        dict с ключом "reason" если CallManager найден, иначе None
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
                if tool_name == "call_manager_tool":
                    args = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", {})
                    reason = args.get("reason", "Причина не указана") if isinstance(args, dict) else "Причина не указана"
                    return {"reason": reason}
    return None

