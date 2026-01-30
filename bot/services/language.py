"""Сервис для работы с языком пользователя с кешированием."""

from typing import Optional
from loguru import logger

from bot.database.repo import FirestoreRepo

# Кеш языка пользователей: {telegram_id: language}
_language_cache: dict[int, str] = {}


async def get_user_language(
    repo: FirestoreRepo,
    telegram_id: int,
    user_id: Optional[str] = None,
) -> str:
    """
    Получить язык пользователя с кешированием.

    Args:
        repo: Репозиторий для работы с БД
        telegram_id: ID пользователя в Telegram
        user_id: ID пользователя в Firestore (опционально, если не указан, используется telegram_id)

    Returns:
        Язык пользователя ('ru' по умолчанию, если не установлен)
    """
    # Проверяем кеш
    if telegram_id in _language_cache:
        return _language_cache[telegram_id]
    
    # Получаем из БД
    db_user_id = user_id or str(telegram_id)
    language = await repo.get_user_language(db_user_id)
    
    # Если язык не установлен, возвращаем 'ru' по умолчанию
    if language is None:
        language = "ru"
    
    # Сохраняем в кеш
    _language_cache[telegram_id] = language
    
    return language


async def set_user_language(
    repo: FirestoreRepo,
    telegram_id: int,
    language: str,
    user_id: Optional[str] = None,
) -> None:
    """
    Установить язык пользователя и обновить кеш.

    Args:
        repo: Репозиторий для работы с БД
        telegram_id: ID пользователя в Telegram
        language: Язык ('ru' или 'en')
        user_id: ID пользователя в Firestore (опционально, если не указан, используется telegram_id)
    """
    db_user_id = user_id or str(telegram_id)
    await repo.set_user_language(db_user_id, language)
    
    # Обновляем кеш
    _language_cache[telegram_id] = language
    
    logger.info(f"Язык пользователя {telegram_id} установлен: {language}")


def clear_language_cache(telegram_id: Optional[int] = None) -> None:
    """
    Очистить кеш языка пользователя.

    Args:
        telegram_id: ID пользователя в Telegram (если не указан, очищается весь кеш)
    """
    if telegram_id is None:
        _language_cache.clear()
        logger.info("Кеш языка полностью очищен")
    else:
        _language_cache.pop(telegram_id, None)
        logger.info(f"Кеш языка для пользователя {telegram_id} очищен")
