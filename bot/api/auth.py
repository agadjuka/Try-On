"""Bearer-авторизация для REST API.

Схема:
  - Клиент передаёт: Authorization: Bearer <raw_key>
  - Сервер хэширует raw_key через SHA-256 и ищет хэш в Firestore (коллекция api_keys).
  - Результат проверки кэшируется в памяти на 5 минут, чтобы не долбить Firestore каждым запросом.
  - Сырой ключ никогда не хранится — только хэш.
"""
import hashlib
import time
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from bot.api.task_repo import ApiTaskRepo

_bearer = HTTPBearer(auto_error=True)

# {key_hash: (is_valid, timestamp)}
_cache: dict[str, tuple[bool, float]] = {}
_CACHE_TTL = 300.0  # секунды

# Lazy singleton репозитория (создаётся при первом обращении)
_repo_instance: Optional[ApiTaskRepo] = None


def get_api_task_repo() -> ApiTaskRepo:
    """FastAPI dependency: возвращает singleton ApiTaskRepo."""
    global _repo_instance
    if _repo_instance is None:
        from bot.services.container import ServiceContainer

        settings = ServiceContainer.get().settings
        if settings is None:
            raise RuntimeError("ServiceContainer не инициализирован — сервисы ещё не запущены")
        _repo_instance = ApiTaskRepo(settings)
    return _repo_instance


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
    repo: ApiTaskRepo = Depends(get_api_task_repo),
) -> str:
    """Dependency: проверить Bearer-токен. Возвращает key_hash при успехе."""
    raw_key = credentials.credentials
    key_hash = _hash(raw_key)

    cached = _cache.get(key_hash)
    if cached is not None:
        is_valid, ts = cached
        if time.monotonic() - ts < _CACHE_TTL:
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or inactive API key",
                )
            return key_hash

    is_valid = await repo.is_key_active(key_hash)
    _cache[key_hash] = (is_valid, time.monotonic())

    if not is_valid:
        logger.warning(f"Отказ авторизации: ключ не найден (hash prefix: {key_hash[:8]})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    return key_hash
