"""Утилита для удаления checkpoint пользователя из Firestore."""

import logging
import os

from google.cloud import firestore

logger = logging.getLogger(__name__)


def delete_user_checkpoint(user_id: str) -> bool:
    """Удаляет checkpoint пользователя из Firestore.
    
    Args:
        user_id: ID пользователя Telegram
        
    Returns:
        True если удаление успешно, False в противном случае
    """
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            logger.warning("GOOGLE_CLOUD_PROJECT не установлен")
            return False
        
        database_id = os.getenv("FIRESTORE_DATABASE", "(default)")
        client = firestore.Client(project=project_id, database=database_id)
        collection = client.collection("checkpoints")
        
        doc_ref = collection.document(str(user_id))
        doc_ref.delete()
        
        logger.info("Checkpoint пользователя %s удален из Firestore", user_id)
        return True
        
    except Exception as e:
        logger.error("Ошибка при удалении checkpoint пользователя %s: %s", user_id, str(e))
        return False


