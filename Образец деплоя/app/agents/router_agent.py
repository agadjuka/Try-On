"""Роутер агент для распределения запросов между специализированными агентами."""

from langgraph.graph import END, StateGraph

from app.agents.message_router import RouterState, router_node
from app.config.checkpoint_config import checkpoint_memory


def create_router_agent() -> StateGraph:
    """Создает граф роутера агента с checkpoint для сохранения состояния."""
    workflow = StateGraph(RouterState)

    # Добавляем узел роутера
    workflow.add_node("router", router_node)

    # Устанавливаем точку входа
    workflow.set_entry_point("router")

    # Роутер всегда завершает работу после обработки
    workflow.add_edge("router", END)

    # Компилируем граф с checkpoint для сохранения состояния между вызовами
    return workflow.compile(checkpointer=checkpoint_memory)


# Создаем router_agent при импорте модуля
try:
    router_agent = create_router_agent()
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Ошибка при создании router_agent: {str(e)}", exc_info=True)
    raise

