"""Конфигурация приложения через pydantic-settings."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения."""

    # Optional legacy Google Cloud settings. Required only for GCS or Firestore;
    # Gemini try-on uses GEMINI_API_KEY instead.
    google_cloud_project_id: str = ""
    google_cloud_region: str = ""
    gcs_bucket_name: str = ""
    bot_token: str

    # Gemini API (Nano Banana) for Virtual Try-On image generation.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-image"
    gemini_try_on_prompt: str = (
        "The first photo is of a model, the second photo is of clothes. "
        "I need you to try the clothes on the model. Generate an image."
    )

    # Хранилище файлов: oracle (S3-compatible Object Storage) | gcs
    storage_backend: Literal["oracle", "gcs"] = "oracle"
    oracle_s3_endpoint: str = ""
    oracle_s3_region: str = ""
    oracle_access_key_id: str = ""
    oracle_secret_access_key: str = ""
    oracle_bucket_name: str = ""

    # firestore | sqlite — метаданные пользователей, API-ключи, adminpanel
    database_backend: Literal["firestore", "sqlite"] = "sqlite"
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
