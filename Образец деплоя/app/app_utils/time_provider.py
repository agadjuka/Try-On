"""Утилиты для получения текущего времени в часовом поясе Москвы."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def get_moscow_time_tag() -> str:
    """Формирует строку-вставку с текущим временем в Москве."""
    current_time = datetime.now(tz=MOSCOW_TZ)
    formatted = current_time.strftime("%d.%m.%Y %H:%M:%S")
    return f"[Текущее время {formatted}]"

