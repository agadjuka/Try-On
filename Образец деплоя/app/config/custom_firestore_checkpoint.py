"""Кастомный Firestore checkpoint saver с правильной структурой хранения.

Структура: checkpoints/{user_id}
Каждый пользователь имеет один документ с последним checkpoint'ом.
При сохранении нового checkpoint старый автоматически заменяется.
"""

from __future__ import annotations

import logging
from typing import Any, Iterator

from google.cloud import firestore
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)

logger = logging.getLogger(__name__)


class CustomFirestoreCheckpoint(BaseCheckpointSaver):
    """
    Кастомный checkpoint saver для Firestore.
    
    Структура хранения:
    - checkpoints/{user_id} - документ с последним checkpoint'ом для пользователя
    
    Каждый пользователь (thread_id) имеет только один последний checkpoint.
    При сохранении нового checkpoint старый автоматически заменяется.
    """

    def __init__(
        self,
        project_id: str,
        database_id: str = "(default)",
        collection_name: str = "checkpoints",
    ):
        """Инициализирует кастомный Firestore checkpoint.
        
        Args:
            project_id: ID проекта GCP
            database_id: ID базы данных Firestore (по умолчанию "(default)")
            collection_name: Имя коллекции для checkpoint'ов (по умолчанию "checkpoints")
        """
        super().__init__()
        self.client = firestore.Client(project=project_id, database=database_id)
        self.collection = self.client.collection(collection_name)

    def _get_user_id_from_thread_id(self, thread_id: str) -> str:
        """Извлекает user_id из thread_id (убирает суффикс _router:uuid)."""
        return thread_id.split("_")[0] if "_" in thread_id else thread_id

    def put(
        self,
        config: dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, Any],
    ) -> dict[str, Any]:
        """Сохраняет checkpoint для пользователя, заменяя предыдущий."""
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            raise ValueError("thread_id не указан в config")
        
        user_id = self._get_user_id_from_thread_id(thread_id)
        checkpoint_type, serialized_checkpoint = self.serde.dumps_typed(checkpoint)
        metadata_type, serialized_metadata = self.serde.dumps_typed(metadata)
        
        self.collection.document(user_id).set({
            "checkpoint": serialized_checkpoint,
            "checkpoint_type": checkpoint_type,
            "metadata": serialized_metadata,
            "metadata_type": metadata_type,
            "thread_id": thread_id,
            "user_id": user_id,
            "checkpoint_id": checkpoint.get("id", "current"),
            "timestamp": firestore.SERVER_TIMESTAMP,
        })
        
        result_config = config.copy()
        if "configurable" not in result_config:
            result_config["configurable"] = {}
        
        checkpoint_ns = result_config.get("configurable", {}).get("checkpoint_ns", "")
        result_config["configurable"].update({
            "checkpoint_id": checkpoint.get("id", "current"),
            "checkpoint_ns": checkpoint_ns,
            "thread_id": thread_id,
        })
        
        return result_config

    def _get_doc(self, config: dict[str, Any]) -> dict[str, Any] | None:
        """Получает документ checkpoint'а для пользователя."""
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return None
        
        doc = self.collection.document(self._get_user_id_from_thread_id(thread_id)).get()
        return doc.to_dict() if doc.exists else None

    def get(self, config: dict[str, Any]) -> Checkpoint | None:
        """Получает последний checkpoint для пользователя."""
        data = self._get_doc(config)
        if not data or "checkpoint" not in data:
            return None
        
        checkpoint_type = data.get("checkpoint_type", "checkpoint")
        return self.serde.loads_typed((checkpoint_type, data["checkpoint"]))

    def list(
        self,
        config: dict[str, Any],
        *,
        filter: dict[str, Any] | None = None,
        before: str | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointMetadata]:
        """Возвращает metadata последнего checkpoint'а для пользователя."""
        data = self._get_doc(config)
        if not data or "metadata" not in data:
            return
        
        metadata_type = data.get("metadata_type", "checkpoint_metadata")
        metadata_dict = self.serde.loads_typed((metadata_type, data["metadata"]))
        yield CheckpointMetadata(checkpoint_id="current", **metadata_dict)

    def put_writes(
        self,
        config: dict[str, Any],
        writes: list[tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Сохраняет записи (writes) для checkpoint'а."""
        pass

    def get_tuple(self, config: dict[str, Any]) -> CheckpointTuple | None:
        """Получает checkpoint и metadata в формате CheckpointTuple."""
        checkpoint = self.get(config)
        if not checkpoint:
            return None
        
        data = self._get_doc(config)
        if not data or "metadata" not in data:
            return None
        
        metadata_type = data.get("metadata_type", "checkpoint_metadata")
        metadata_dict = self.serde.loads_typed((metadata_type, data["metadata"]))
        metadata = CheckpointMetadata(checkpoint_id="current", **metadata_dict)
        
        return CheckpointTuple(
            config=config,
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=None,
            pending_writes=None,
        )

    def delete(self, config: dict[str, Any], checkpoint_id: str) -> None:
        """Удаляет checkpoint для пользователя."""
        thread_id = config.get("configurable", {}).get("thread_id")
        if thread_id:
            self.collection.document(self._get_user_id_from_thread_id(thread_id)).delete()

