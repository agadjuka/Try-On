"""Конфигурация для Virtual Try-On скрипта."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные окружения
script_dir = Path(__file__).parent
env_path = script_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Config:
    """Класс для хранения конфигурации."""
    
    # Пути к папкам
    BASE_DIR = script_dir
    INPUT_PERSON_DIR = BASE_DIR / "input" / "person"
    INPUT_PRODUCT_DIR = BASE_DIR / "input" / "product"
    OUTPUT_DIR = BASE_DIR / "output"
    
    # Google Cloud настройки
    PROJECT_ID: Optional[str] = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    REGION: Optional[str] = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    MODEL_ID: str = "virtual-try-on-001"
    
    # Параметры API
    BASE_STEPS: int = int(os.getenv("BASE_STEPS", "32"))
    SAMPLE_COUNT: int = int(os.getenv("SAMPLE_COUNT", "1"))
    ADD_WATERMARK: bool = os.getenv("ADD_WATERMARK", "true").lower() == "true"
    PERSON_GENERATION: str = os.getenv("PERSON_GENERATION", "allow_adult")
    SAFETY_SETTING: str = os.getenv("SAFETY_SETTING", "block_medium_and_above")
    
    # Настройки вывода
    OUTPUT_MIME_TYPE: str = os.getenv("OUTPUT_MIME_TYPE", "image/png")
    COMPRESSION_QUALITY: int = int(os.getenv("COMPRESSION_QUALITY", "75"))
    
    # Опциональные параметры
    STORAGE_URI: Optional[str] = os.getenv("STORAGE_URI")
    SEED: Optional[int] = int(os.getenv("SEED")) if os.getenv("SEED") else None
    
    @classmethod
    def validate(cls) -> None:
        """Проверяет корректность конфигурации."""
        if not cls.PROJECT_ID:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT_ID не установлен в переменных окружения"
            )
        
        if not cls.INPUT_PERSON_DIR.exists():
            cls.INPUT_PERSON_DIR.mkdir(parents=True, exist_ok=True)
        
        if not cls.INPUT_PRODUCT_DIR.exists():
            cls.INPUT_PRODUCT_DIR.mkdir(parents=True, exist_ok=True)
        
        if not cls.OUTPUT_DIR.exists():
            cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_api_url(cls) -> str:
        """Возвращает URL для API запроса."""
        return (
            f"https://{cls.REGION}-aiplatform.googleapis.com/v1/"
            f"projects/{cls.PROJECT_ID}/locations/{cls.REGION}/"
            f"publishers/google/models/{cls.MODEL_ID}:predict"
        )
