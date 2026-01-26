"""Фабрика для создания LLM с автоматическим логированием."""

from langchain_google_vertexai import ChatVertexAI
from app.app_utils.llm_logging_callback import LLMLoggingCallback

LOCATION = "global"


def create_llm(
    model: str = "gemini-2.5-flash",
    location: str = LOCATION,
    temperature: float = 0,
    project: str | None = None,
) -> ChatVertexAI:
    """
    Создает LLM с автоматическим логированием (если включено через LOG_SAVE=on).
    
    Args:
        model: Название модели
        location: Локация для Vertex AI
        temperature: Температура модели
        project: ID проекта (опционально)
    
    Returns:
        ChatVertexAI с автоматическим логированием
    """
    return ChatVertexAI(
        model=model,
        location=location,
        project=project,
        temperature=temperature,
        callbacks=[LLMLoggingCallback()],
    )

