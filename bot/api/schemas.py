"""Pydantic-схемы запросов и ответов REST API."""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TryOnSubmitResponse(BaseModel):
    """Ответ при создании задачи примерки."""

    task_id: str = Field(..., description="Уникальный ID задачи для опроса статуса")
    status: TaskStatus
    created_at: datetime


class TryOnStatusResponse(BaseModel):
    """Ответ при опросе статуса задачи."""

    task_id: str
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    results: list[str] = Field(
        default_factory=list,
        description="URL для скачивания готовых фото (заполняется когда status=completed)",
    )
    error: Optional[str] = Field(None, description="Текст ошибки (заполняется когда status=failed)")
