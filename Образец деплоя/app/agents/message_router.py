"""Модуль маршрутизации сообщений для определения намерений пользователя."""

import logging
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph.message import add_messages

from app.agents.router_stage import ROUTER_STAGE_INSTRUCTION, llm_flash
from app.agents.morning_stage import morning_agent
from app.agents.evening_stage import evening_agent
from app.tools.call_manager import call_manager_tool
from app.app_utils.tool_callback import ToolCallCallback
from app.app_utils.call_manager_handler import set_call_manager_content_if_empty
from app.app_utils.message_utils import is_message_empty, filter_empty_messages

logger = logging.getLogger(__name__)


def add_messages_filtered(left: list[BaseMessage], right: list[BaseMessage]) -> list[BaseMessage]:
    """
    Кастомный reducer для добавления сообщений с фильтрацией пустых.
    
    Фильтрует пустые сообщения перед добавлением в историю,
    чтобы они не попадали в checkpoint и не вызывали ошибки в API.
    Также устанавливает reason для пустых AIMessage с CallManager tool_calls.
    """
    # Обрабатываем CallManager: устанавливаем reason для пустых AIMessage с tool_calls
    for msg in right:
        if isinstance(msg, AIMessage):
            set_call_manager_content_if_empty(msg)
    
    # Фильтруем пустые сообщения из новых сообщений
    filtered_right = filter_empty_messages(right)
    
    # Если после фильтрации остались пустые сообщения, логируем
    if len(filtered_right) < len(right):
        skipped_count = len(right) - len(filtered_right)
        logger.debug(f"Пропущено {skipped_count} пустых сообщений при добавлении в историю")
    
    # Используем стандартный add_messages для объединения
    return add_messages(left, filtered_right)


class RouterState(TypedDict):
    """Состояние для роутера агента."""

    messages: Annotated[list[BaseMessage], add_messages_filtered]


def route_message(state: RouterState) -> tuple[str, AIMessage | None]:
    """
    Определяет намерение пользователя и возвращает маршрут на основе последних сообщений.
    
    Returns:
        tuple: (маршрут, AIMessage с tool_calls если был вызов CallManager, иначе None)
    """
    # Получаем последние 5 сообщений (исключаем ToolMessage и пустые сообщения)
    recent_messages = []
    for msg in reversed(state["messages"]):
        # Пропускаем ToolMessage, они не нужны для контекста роутера
        if isinstance(msg, ToolMessage):
            continue
        
        # Пропускаем пустые сообщения - они вызывают ошибку в Google Vertex AI API
        if is_message_empty(msg):
            logger.debug("Пропущено пустое сообщение: %s", type(msg).__name__)
            continue
        
        # Для AIMessage создаем чистую копию без tool_calls, чтобы роутер не видел информацию об инструментах
        if isinstance(msg, AIMessage):
            # Создаем новое сообщение только с content, без tool_calls
            clean_msg = AIMessage(content=msg.content)
            recent_messages.insert(0, clean_msg)
        else:
            # Для HumanMessage и других типов добавляем как есть
            recent_messages.insert(0, msg)
        
        if len(recent_messages) >= 5:
            break
    
    # Если нет сообщений, возвращаем morning
    if not recent_messages:
        return ("morning", None)
    
    # Создаем промпт для роутера с контекстом последних сообщений
    router_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ROUTER_STAGE_INSTRUCTION),
            MessagesPlaceholder("recent_messages"),
        ]
    )

    # Создаем цепочку из промпта и модели с инструментами
    # Добавляем CallManager к роутеру
    llm_with_tools = llm_flash.bind_tools([call_manager_tool])
    chain = router_prompt | llm_with_tools

    # Вызываем цепочку с последними сообщениями
    # Логирование уже настроено в llm_flash через create_llm
    response = chain.invoke({"recent_messages": recent_messages})
    
    # Проверяем, был ли вызван CallManager
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
            if tool_name == "call_manager_tool":
                # Роутер вызвал CallManager - возвращаем маркер и response с tool_calls
                args = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", {})
                reason = args.get("reason", "-") if isinstance(args, dict) else "-"
                logger.info("🔧 Router → call_manager_tool | reason: %s", reason)
                return ("__CALL_MANAGER__", response)
    
    # Извлекаем результат и приводим к нижнему регистру
    raw_response = response.content if hasattr(response, "content") else str(response)
    result = raw_response.lower().strip() if raw_response else ""

    # Проверяем, что результат валидный
    valid_routes = ["morning", "evening"]
    if result not in valid_routes:
        logger.warning("⚠️ Невалидный маршрут: '%s' → morning", result)
        return ("morning", None)

    logger.info("🔄 Router → %s", result)
    return (result, None)


def _handle_call_manager_route(router_response: AIMessage) -> RouterState:
    """
    Обрабатывает маршрут __CALL_MANAGER__.
    
    Args:
        router_response: AIMessage с tool_calls для CallManager
        
    Returns:
        RouterState с обработанными сообщениями
    """
    # Извлекаем reason из tool_calls и устанавливаем как content, если пустой
    set_call_manager_content_if_empty(router_response)
    
    # Создаем ToolMessage для каждого tool_calls (требование LangGraph)
    tool_messages = []
    if hasattr(router_response, "tool_calls") and router_response.tool_calls:
        for tool_call in router_response.tool_calls:
            tool_call_id = tool_call.get("id") if isinstance(tool_call, dict) else getattr(tool_call, "id", "")
            tool_messages.append(ToolMessage(content="Менеджер вызван", tool_call_id=tool_call_id))
    
    return {"messages": [router_response] + tool_messages}


def _process_agent_response(agent, messages: list[BaseMessage]) -> RouterState:
    """
    Вызывает агента и обрабатывает его ответ.
    
    Args:
        agent: Агент для вызова
        messages: Список сообщений для передачи агенту
        
    Returns:
        RouterState с ответом агента
    """
    try:
        # Передаем отфильтрованные сообщения без пустых
        # Добавляем callback для логирования вызовов инструментов в момент их выполнения
        from langchain_core.runnables import RunnableConfig
        config = RunnableConfig(callbacks=[ToolCallCallback()])
        result = agent.invoke({"messages": messages}, config=config)
        response_messages = result.get("messages", [])
        
        # Обрабатываем CallManager: устанавливаем reason для пустых AIMessage с tool_calls
        for msg in response_messages:
            if isinstance(msg, AIMessage):
                set_call_manager_content_if_empty(msg)
        
        return {"messages": response_messages}
    except Exception as e:
        logger.error("❌ Router ошибка: %s", str(e))
        error_msg = f"Ошибка при обработке запроса: {str(e)}. Убедитесь, что вы авторизованы в Google Cloud (выполните 'gcloud auth application-default login')."
        return {
            "messages": [
                AIMessage(content=error_msg)
            ]
        }


def router_node(state: RouterState) -> RouterState:
    """Узел роутера, который определяет, какому агенту отправить запрос."""
    messages = state.get("messages", [])
    
    # 1. Фильтрация сообщений
    messages = filter_empty_messages(messages)
    
    if not messages:
        return state

    # 2. Определение маршрута
    route, router_response = route_message(state)
    
    # 3. Если CallManager → _handle_call_manager_route
    if route == "__CALL_MANAGER__" and router_response is not None:
        if isinstance(router_response, AIMessage):
            return _handle_call_manager_route(router_response)
    
    # 4. Иначе → выбор агента → _process_agent_response
    agents = {
        "morning": morning_agent,
        "evening": evening_agent,
    }
    
    agent = agents.get(route, morning_agent)
    return _process_agent_response(agent, messages)

