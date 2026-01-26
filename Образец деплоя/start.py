#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для запуска backend и frontend с выводом всех логов в консоль.
"""

import os
import subprocess
import sys
import time
import threading
from pathlib import Path

# Цвета для вывода
class Colors:
    BACKEND = "\033[36m"  # Cyan
    FRONTEND = "\033[35m"  # Magenta
    INFO = "\033[32m"  # Green
    RESET = "\033[0m"  # Reset


def print_colored(text: str, color: str = Colors.RESET) -> None:
    """Выводит текст с цветом."""
    print(f"{color}{text}{Colors.RESET}")


def run_backend() -> None:
    """Запускает backend и выводит его логи."""
    script_dir = Path(__file__).parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(script_dir)
    
    print_colored("=" * 80, Colors.BACKEND)
    print_colored("BACKEND (FastAPI) - http://localhost:8000", Colors.BACKEND)
    print_colored("=" * 80, Colors.BACKEND)
    
    process = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.fast_api_app:app", "--host", "localhost", "--port", "8000", "--reload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        env=env,
        cwd=str(script_dir)
    )
    
    for line in process.stdout:
        print_colored(f"[BACKEND] {line.rstrip()}", Colors.BACKEND)


def run_frontend() -> None:
    """Запускает frontend и выводит его логи."""
    script_dir = Path(__file__).parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(script_dir)
    
    # Небольшая задержка, чтобы backend успел запуститься
    time.sleep(3)
    
    print_colored("=" * 80, Colors.FRONTEND)
    print_colored("FRONTEND (Streamlit) - http://localhost:8501", Colors.FRONTEND)
    print_colored("=" * 80, Colors.FRONTEND)
    
    process = subprocess.Popen(
        [
            "uv", "run", "streamlit", "run", "frontend/streamlit_app.py",
            "--browser.serverAddress=localhost",
            "--server.enableCORS=false",
            "--server.enableXsrfProtection=false"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        env=env,
        cwd=str(script_dir)
    )
    
    for line in process.stdout:
        print_colored(f"[FRONTEND] {line.rstrip()}", Colors.FRONTEND)


def main() -> None:
    """Главная функция."""
    # Переходим в папку скрипта
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print_colored("=" * 80, Colors.INFO)
    print_colored("Запуск Backend и Frontend", Colors.INFO)
    print_colored("=" * 80, Colors.INFO)
    print()
    
    # Проверяем зависимости
    print_colored("[1/4] Проверка зависимостей...", Colors.INFO)
    result = subprocess.run(
        ["uv", "sync", "--extra", "streamlit"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print_colored("Ошибка при установке зависимостей!", Colors.RESET)
        print(result.stderr)
        sys.exit(1)
    
    # Устанавливаем проект в режиме разработки
    print_colored("[2/4] Установка проекта в режиме разработки...", Colors.INFO)
    result = subprocess.run(
        ["uv", "pip", "install", "-e", "."],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print_colored("Предупреждение: не удалось установить проект в режиме разработки", Colors.RESET)
        print(result.stderr)
    
    # Устанавливаем PYTHONPATH
    os.environ["PYTHONPATH"] = str(script_dir)
    
    print_colored("[3/4] Запуск Backend...", Colors.INFO)
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    
    print_colored("[4/4] Запуск Frontend...", Colors.INFO)
    frontend_thread = threading.Thread(target=run_frontend, daemon=True)
    frontend_thread.start()
    
    print()
    print_colored("=" * 80, Colors.INFO)
    print_colored("Backend: http://localhost:8000", Colors.INFO)
    print_colored("Frontend: http://localhost:8501", Colors.INFO)
    print_colored("=" * 80, Colors.INFO)
    print()
    print_colored("Логи обоих процессов выводятся ниже. Нажмите Ctrl+C для остановки.", Colors.INFO)
    print()
    
    # Ждем завершения потоков
    try:
        backend_thread.join()
        frontend_thread.join()
    except KeyboardInterrupt:
        print_colored("\nОстановка процессов...", Colors.INFO)
        sys.exit(0)


if __name__ == "__main__":
    main()

