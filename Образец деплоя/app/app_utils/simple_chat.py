"""Простые модели для REST API чата."""

from pydantic import BaseModel, Field


class SimpleChatRequest(BaseModel):
    """Простой запрос для чата - только текст сообщения."""

    message: str = Field(..., description="Текст сообщения для отправки агенту")


class SimpleChatResponse(BaseModel):
    """Простой ответ от чата - только текст ответа."""

    response: str = Field(..., description="Текст ответа от агента")



