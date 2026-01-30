"""Pydantic модели для работы с Firestore."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserModel(BaseModel):
    """Модель пользователя Telegram."""

    id: str = Field(..., description="Уникальный ID в Firestore")
    telegram_id: int = Field(..., description="ID пользователя в Telegram")
    username: Optional[str] = Field(None, description="Username в Telegram")
    language: Optional[str] = Field(None, description="Язык интерфейса ('ru' или 'en')")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Дата создания")

    class Config:
        """Конфигурация модели."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class PersonImage(BaseModel):
    """Модель изображения человека для примерки."""

    id: str = Field(..., description="Уникальный ID в Firestore")
    user_id: str = Field(..., description="ID пользователя-владельца")
    gcs_uri: str = Field(..., description="URI изображения в GCS (gs://...)")
    is_active: bool = Field(default=True, description="Активно ли изображение")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Дата создания")

    class Config:
        """Конфигурация модели."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class TryOnResult(BaseModel):
    """Модель финального результата примерки."""

    id: str = Field(..., description="Уникальный ID в Firestore")
    user_id: str = Field(..., description="ID пользователя-владельца")
    gcs_uri: str = Field(..., description="URI изображения результата в GCS (gs://...)")
    model_gcs_uri: Optional[str] = Field(None, description="URI модели, использованной для примерки")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Дата создания")

    class Config:
        """Конфигурация модели."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }