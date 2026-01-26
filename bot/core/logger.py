"""Настройка логирования через loguru только для терминала."""

import sys
from loguru import logger


def setup_logger() -> None:
    """Настроить логгер для приложения (только терминал, без файлов)."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True,
    )
