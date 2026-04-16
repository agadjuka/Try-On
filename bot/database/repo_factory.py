"""Фабрика репозиториев: Firestore или SQLite по DATABASE_BACKEND."""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

from bot.core.config import Settings

if TYPE_CHECKING:
    from bot.api.task_repo import ApiTaskRepo
    from bot.database.repo import FirestoreRepo
    from bot.database.sqlite_repo import SqliteRepo
    from bot.database.sqlite_task_repo import SqliteApiTaskRepo

UserRepository = Union["FirestoreRepo", "SqliteRepo"]
ApiTaskRepository = Union["ApiTaskRepo", "SqliteApiTaskRepo"]


def create_user_repo(settings: Settings) -> UserRepository:
    if settings.database_backend == "sqlite":
        from bot.database.sqlite_repo import SqliteRepo

        return SqliteRepo(settings)
    from bot.database.repo import FirestoreRepo

    return FirestoreRepo(settings)


def create_api_task_repo(settings: Settings) -> ApiTaskRepository:
    if settings.database_backend == "sqlite":
        from bot.database.sqlite_task_repo import SqliteApiTaskRepo

        return SqliteApiTaskRepo(settings)
    from bot.api.task_repo import ApiTaskRepo

    return ApiTaskRepo(settings)
