"""Утилита для форматирования промптов в нужном формате."""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def create_formatted_prompt(
    system_instruction: str,
    messages: list[BaseMessage],
) -> ChatPromptTemplate:
    """
    Создает промпт в формате:
    1. Системная инструкция
    2. Последнее сообщение клиента (если есть)
    3. Пустая строка
    4. "История переписки:"
    5. История переписки (без последнего сообщения)
    
    Args:
        system_instruction: Системная инструкция
        messages: Список сообщений
        
    Returns:
        ChatPromptTemplate с правильно отформатированным промптом
    """
    if not messages:
        # Если нет сообщений, возвращаем только системную инструкцию
        return ChatPromptTemplate.from_messages([("system", system_instruction)])
    
    # Разделяем на последнее сообщение и историю
    last_message = messages[-1]
    history_messages = messages[:-1] if len(messages) > 1 else []
    
    # Определяем тип последнего сообщения
    if isinstance(last_message, AIMessage):
        last_message_role = "assistant"
    elif isinstance(last_message, HumanMessage):
        last_message_role = "human"
    else:
        # Если последнее сообщение не Human или AI, добавляем его в историю
        history_messages = messages
        last_message = None
        last_message_role = None
    
    # Создаем структуру промпта
    prompt_messages = [("system", system_instruction)]
    
    # Добавляем последнее сообщение клиента с явной подписью (только если это HumanMessage)
    if last_message and isinstance(last_message, HumanMessage):
        last_message_content = getattr(last_message, "content", "")
        if last_message_content:
            # Добавляем подпись "Последнее сообщение клиента:" через системное сообщение
            prompt_messages.append(("system", "Последнее сообщение клиента:"))
            prompt_messages.append(("human", last_message_content))
    
    # Добавляем разделитель и заголовок истории после последнего сообщения
    if history_messages:
        # Добавляем пустую строку и заголовок "История переписки:" как отдельное системное сообщение
        prompt_messages.append(("system", "\n\nИстория переписки:"))
        prompt_messages.append(MessagesPlaceholder("history_messages"))
    
    return ChatPromptTemplate.from_messages(prompt_messages)

