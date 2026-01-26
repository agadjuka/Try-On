#!/usr/bin/env python3
"""Простой скрипт для деплоя приложения в Google Cloud Run."""
import subprocess
import sys
import os
import re


CONTAINER_NAME = ""


def get_container_name():
    """Получает название контейнера, запрашивая у пользователя если нужно."""
    global CONTAINER_NAME
    
    if not CONTAINER_NAME:
        container_name = input("Введите название контейнера: ").strip()
        if not container_name:
            print("Ошибка: название контейнера не может быть пустым.", file=sys.stderr)
            sys.exit(1)
        
        # Сохраняем название в файл
        script_path = os.path.abspath(__file__)
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Заменяем любое значение на введенное
        content = re.sub(
            r'CONTAINER_NAME = "[^"]*"',
            f'CONTAINER_NAME = "{container_name}"',
            content
        )
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return container_name
    
    return CONTAINER_NAME


def main():
    """Запускает деплой в Google Cloud Run."""
    container_name = get_container_name()
    
    command = (
        f"gcloud run deploy {container_name} "
        "--source . "
        "--region BYON "
        "--allow-unauthenticated "
        "--memory 1Gi"
    )
    
    try:
        subprocess.run(command, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при деплое: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nДеплой прерван пользователем.")
        sys.exit(0)


if __name__ == "__main__":
    main()
