"""Обработчик команды /start."""

from aiogram import Bot
from aiogram.types import Message
from loguru import logger

from bot.database.repo_factory import UserRepository
from bot.keyboards.user_kb import (
    get_main_menu_keyboard,
    get_language_selection_keyboard,
    get_privacy_consent_keyboard,
)
from bot.locales.texts import get_text
from bot.services.language import get_user_language
from bot.admin.factory import get_admin_service


async def start_command(
    message: Message,
    bot: Bot,
    repo: UserRepository,
) -> None:
    """
    Обработчик команды /start.

    Args:
        message: Сообщение от пользователя
        bot: Экземпляр бота
        repo: Репозиторий для работы с БД
    """
    user = message.from_user
    
    try:
        # Проверяем/создаем пользователя в БД
        user_id = await repo.add_user(
            telegram_id=user.id,
            username=user.username,
        )
        logger.info(f"Пользователь {user_id} обработан в /start")
        
        # Проверяем, есть ли язык у пользователя в БД (прямая проверка, не через кеш)
        language = await repo.get_user_language(user_id)
        
        if language is None:
            # Язык не выбран - показываем выбор языка
            await message.answer(
                get_text("language_selection", "ru"),
                reply_markup=get_language_selection_keyboard(),
            )
            return

        if not await repo.get_privacy_consent_accepted(user_id):
            lang = language if language in ("ru", "en") else "ru"
            await message.answer(
                get_text("privacy_notice", lang),
                reply_markup=get_privacy_consent_keyboard(lang),
                parse_mode="HTML",
            )
            return

        # Язык выбран, согласие есть — показываем приветствие
        # Создаем топик в админ-панели при команде /start (если настроено)
        admin_service = get_admin_service(bot)
        if admin_service:
            try:
                await admin_service.get_or_create_topic(user)
            except Exception:
                pass
        
        # Отправляем приветствие и главное меню на выбранном языке
        await message.answer(
            get_text("welcome", language),
            reply_markup=get_main_menu_keyboard(language),
            parse_mode="HTML",
        )
        
    except Exception as e:
        logger.error(f"Ошибка в /start для пользователя {user.id}: {e}")
        # Используем русский по умолчанию для ошибок
        await message.answer(
            get_text("start_error", "ru"),
        )
