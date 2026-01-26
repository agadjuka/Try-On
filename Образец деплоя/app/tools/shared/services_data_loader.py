"""
Сервис для чтения данных об услугах
Поддерживает чтение из Google Cloud Storage
"""
import os
import json
from typing import Dict
from functools import lru_cache
from google.cloud import storage


class ServicesDataLoader:
    """Загрузчик данных об услугах из Google Cloud Storage"""
    
    def __init__(self):
        """Инициализация загрузчика"""
        pass
    
    @lru_cache(maxsize=1)
    def load_data(self) -> Dict:
        """
        Загрузка данных об услугах из Google Cloud Storage
        
        Returns:
            Словарь с данными об услугах
            
        Raises:
            ValueError: если не указаны переменные окружения
            Exception: если файл не найден или ошибка парсинга JSON
        """
        bucket_name = os.getenv('GCS_BUCKET_NAME')
        file_name = os.getenv('SERVICES_JSON_FILENAME', 'services.json')
        
        if not bucket_name:
            raise ValueError("Переменная окружения GCS_BUCKET_NAME не установлена")
        
        # Создаем клиент GCS (использует ADC для аутентификации)
        client = storage.Client()
        
        # Получаем бакет
        bucket = client.bucket(bucket_name)
        
        # Получаем объект файла (blob)
        blob = bucket.blob(file_name)
        
        # Проверяем существование файла
        if not blob.exists():
            raise FileNotFoundError(f"Файл {file_name} не найден в бакете {bucket_name}")
        
        # Скачиваем содержимое файла как строку
        json_data = blob.download_as_text(encoding="utf-8")
        
        # Парсим JSON
        return json.loads(json_data)
    
    def reload(self):
        """Принудительная перезагрузка данных (очистка кэша)"""
        self.load_data.cache_clear()


# Глобальный экземпляр загрузчика
_data_loader = ServicesDataLoader()

