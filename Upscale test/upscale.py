"""Простой скрипт для апскейла изображения через Imagen API."""

import base64
import json
import os
from pathlib import Path

import requests
from google.auth import default
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# Загрузка переменных из .env файла в корне проекта
load_dotenv(Path(__file__).parent.parent / ".env")


def get_access_token() -> str:
    """Получить access token для Google Cloud API."""
    credentials, _ = default()
    if not credentials.valid:
        credentials.refresh(Request())
    return credentials.token


def upscale_image():
    """Апскейл изображения in.jpg до 2X и сохранение как out.jpg."""
    # Путь к файлам
    script_dir = Path(__file__).parent
    input_file = script_dir / "in.jpg"
    output_file = script_dir / "out.jpg"
    
    # Проверка наличия входного файла
    if not input_file.exists():
        print(f"Ошибка: файл {input_file} не найден")
        return
    
    # Получение переменных окружения
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    region = "us-central1"  # Хардкод региона для Imagen upscale
    
    if not project_id:
        print("Ошибка: установите переменную окружения GOOGLE_CLOUD_PROJECT_ID")
        return
    
    # Чтение изображения и кодирование в base64
    print("Чтение изображения...")
    with open(input_file, "rb") as f:
        image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    
    # Получение токена
    print("Получение токена доступа...")
    token = get_access_token()
    
    # Формирование запроса
    url = (
        f"https://{region}-aiplatform.googleapis.com/v1/"
        f"projects/{project_id}/locations/{region}/"
        f"publishers/google/models/imagen-4.0-upscale-preview:predict"
    )
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    payload = {
        "instances": [
            {
                "prompt": "Upscale the image",
                "image": {
                    "bytesBase64Encoded": image_base64
                }
            }
        ],
        "parameters": {
            "mode": "upscale",
            "outputOptions": {
                "mimeType": "image/png"
            },
            "upscaleConfig": {
                "upscaleFactor": "x2"
            }
        }
    }
    
    # Отправка запроса
    print("Отправка запроса на апскейл...")
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    # Получение результата
    result = response.json()
    if "predictions" not in result or not result["predictions"]:
        print("Ошибка: не получен результат от API")
        return
    
    # Декодирование и сохранение изображения
    print("Сохранение результата...")
    output_base64 = result["predictions"][0]["bytesBase64Encoded"]
    output_bytes = base64.b64decode(output_base64)
    
    with open(output_file, "wb") as f:
        f.write(output_bytes)
    
    print(f"Готово! Результат сохранен в {output_file}")


if __name__ == "__main__":
    upscale_image()
