"""Конфигурация checkpoint для LangGraph."""

import logging
import os
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


def get_checkpoint() -> Any:
    """
    Создает checkpoint для Firestore.
    
    Структура: checkpoints/{user_id} - один документ на пользователя.
    Переменные окружения: GOOGLE_CLOUD_PROJECT (обязательно), FIRESTORE_DATABASE (опционально).
    """
    try:
        from app.config.custom_firestore_checkpoint import CustomFirestoreCheckpoint
        
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        
        if not project_id:
            logger.warning("⚠️ GOOGLE_CLOUD_PROJECT не установлен. Используется MemorySaver")
            return MemorySaver()
        
        checkpoint = CustomFirestoreCheckpoint(
            project_id=project_id,
            database_id=os.getenv("FIRESTORE_DATABASE", "(default)"),
            collection_name="checkpoints"
        )
        logger.debug("✅ Используется CustomFirestoreCheckpoint (project=%s)", project_id)
        return checkpoint
        
    except Exception as e:
        logger.warning("⚠️ Ошибка при создании checkpoint: %s. Используется MemorySaver", str(e))
        return MemorySaver()


checkpoint_memory = get_checkpoint()

