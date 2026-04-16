"""Конфигурация приложения через pydantic-settings."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения."""

    google_cloud_project_id: str
    google_cloud_region: str
    gcs_bucket_name: str
    bot_token: str

    # firestore | sqlite — метаданные пользователей, API-ключи, adminpanel
    database_backend: Literal["firestore", "sqlite"] = "firestore"
    sqlite_path: str = "./data/vyon.db"
    
    # Название базы данных Firestore (только при database_backend=firestore)
    firestore_database_id: str = "(default)"
    
    # Настройки админ-панели для конкретного пользователя (261617302)
    admin_panel_forwarding_enabled: bool = True  # on/off пересылка в админ-панель для пользователя 261617302

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


def get_settings() -> Settings:
    """Получить экземпляр настроек."""
    return Settings()
