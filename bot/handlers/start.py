"""Обработчик команды /start."""

from aiogram import Bot
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger

from bot.database.repo import FirestoreRepo
from bot.keyboards.user_kb import get_main_menu_keyboard
from bot.locales.texts import get_text


async def start_command(
    message: Message,
    bot: Bot,
    repo: FirestoreRepo,
) -> None:
    """
    Обработчик команды /start.

    Args:
        message: Сообщение от пользователя
        bot: Экземпляр бота
        repo: Репозиторий для работы с БД
    """
    user = message.from_user
    lang = "ru"  # TODO: получать из настроек пользователя
    
    try:
        # Проверяем/создаем пользователя в БД
        user_id = await repo.add_user(
            telegram_id=user.id,
            username=user.username,
        )
        logger.info(f"Пользователь {user_id} обработан в /start")
        
        # Отправляем приветствие и главное меню
        await message.answer(
            get_text("welcome", lang),
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode="HTML",
        )
        
    except Exception as e:
        logger.error(f"Ошибка в /start для пользователя {user.id}: {e}")
        await message.answer(
            "Произошла ошибка. Попробуй позже.",
        )
