#!/usr/bin/env python3
"""Простой скрипт для запуска Telegram бота."""
import subprocess
import sys


def main():
    """Запускает Telegram бота через uv."""
    try:
        subprocess.run(["uv", "run", "python", "start_telegram_bot.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при запуске бота: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nОстановка бота...")
        sys.exit(0)


if __name__ == "__main__":
    main()
