"""Модуль для работы с Google Cloud Vertex AI API."""

import json
import logging
from typing import Dict, Any, List, Optional
import requests
from google.auth import default
from google.auth.transport.requests import Request

from config import Config

logger = logging.getLogger(__name__)


class APIClient:
    """Клиент для работы с Virtual Try-On API."""
    
    def __init__(self):
        """Инициализация клиента."""
        self.api_url = Config.get_api_url()
        self._access_token: Optional[str] = None
    
    def _get_access_token(self) -> str:
        """
        Получает access token через Application Default Credentials.
        Автоматически использует gcloud credentials если они настроены.
        
        Returns:
            Access token для авторизации
        """
        if self._access_token:
            return self._access_token
        
        try:
            # Используем Application Default Credentials
            # Это автоматически найдет credentials из gcloud auth application-default login
            # или из переменной окружения GOOGLE_APPLICATION_CREDENTIALS
            credentials, project = default()
            
            # Обновляем credentials если нужно
            if not credentials.valid:
                credentials.refresh(Request())
            
            self._access_token = credentials.token
            logger.debug("Access token получен через Application Default Credentials")
            return self._access_token
            
        except Exception as e:
            logger.error(f"Ошибка при получении access token: {e}")
            raise RuntimeError(
                "Не удалось получить access token. "
                "Убедитесь, что вы авторизованы через 'gcloud auth application-default login' "
                "или установите переменную окружения GOOGLE_APPLICATION_CREDENTIALS"
            )
    
    def _build_request_body(
        self,
        person_image_base64: str,
        product_image_base64: str
    ) -> Dict[str, Any]:
        """
        Создает тело запроса для API.
        
        Args:
            person_image_base64: Base64-encoded изображение модели
            product_image_base64: Base64-encoded изображение одежды
            
        Returns:
            Словарь с телом запроса
        """
        request_body = {
            "instances": [
                {
                    "personImage": {
                        "image": {
                            "bytesBase64Encoded": person_image_base64
                        }
                    },
                    "productImages": [
                        {
                            "image": {
                                "bytesBase64Encoded": product_image_base64
                            }
                        }
                    ]
                }
            ],
            "parameters": {
                "baseSteps": Config.BASE_STEPS,
                "sampleCount": Config.SAMPLE_COUNT,
                "addWatermark": Config.ADD_WATERMARK,
                "personGeneration": Config.PERSON_GENERATION,
                "safetySetting": Config.SAFETY_SETTING,
                "outputOptions": {
                    "mimeType": Config.OUTPUT_MIME_TYPE
                }
            }
        }
        
        # Добавляем compressionQuality только для JPEG
        if Config.OUTPUT_MIME_TYPE == "image/jpeg":
            request_body["parameters"]["outputOptions"]["compressionQuality"] = Config.COMPRESSION_QUALITY
        
        # Добавляем опциональные параметры
        if Config.STORAGE_URI:
            request_body["parameters"]["storageUri"] = Config.STORAGE_URI
        
        if Config.SEED and not Config.ADD_WATERMARK:
            request_body["parameters"]["seed"] = Config.SEED
        
        return request_body
    
    def generate_try_on(
        self,
        person_image_base64: str,
        product_image_base64: str
    ) -> List[Dict[str, Any]]:
        """
        Генерирует изображение примерки.
        
        Args:
            person_image_base64: Base64-encoded изображение модели
            product_image_base64: Base64-encoded изображение одежды
            
        Returns:
            Список словарей с результатами (mimeType, bytesBase64Encoded)
        """
        access_token = self._get_access_token()
        request_body = self._build_request_body(
            person_image_base64,
            product_image_base64
        )
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        logger.info("Отправка запроса к API...")
        logger.debug(f"URL: {self.api_url}")
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=request_body,
                timeout=300  # 5 минут таймаут
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "predictions" not in result:
                raise ValueError("Ответ API не содержит 'predictions'")
            
            predictions = result["predictions"]
            logger.info(f"Получено {len(predictions)} результатов")
            
            return predictions
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при запросе к API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Детали ошибки: {json.dumps(error_detail, indent=2)}")
                except:
                    logger.error(f"Текст ответа: {e.response.text}")
            raise
