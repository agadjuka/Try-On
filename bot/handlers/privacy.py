"""Согласие с условиями обработки данных и политикой конфиденциальности."""

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from loguru import logger

from bot.database.repo_factory import UserRepository
from bot.keyboards.user_kb import get_main_menu_keyboard
from bot.locales.texts import get_text


async def handle_privacy_consent_accept(
    callback: CallbackQuery,
    bot: Bot,
    repo: UserRepository,
) -> None:
    """
    Сохранить согласие пользователя и показать приветствие с главным меню.

    Args:
        callback: Callback с кнопки «Я согласен»
        bot: Экземпляр бота
        repo: Репозиторий Firestore
    """
    user = callback.from_user
    user_id = str(user.id)

    try:
        language = await repo.get_user_language(user_id)
        if language is None or language not in ("ru", "en"):
            language = "ru"

        await repo.set_privacy_consent_accepted(user_id)
        await callback.answer(get_text("privacy_consent_saved", language))

        if callback.message:
            try:
                await callback.message.edit_text(
                    get_text("welcome", language),
                    reply_markup=get_main_menu_keyboard(language),
                    parse_mode="HTML",
                )
            except TelegramBadRequest as e:
                err = str(e).lower()
                if "message is not modified" in err:
                    pass
                else:
                    await callback.message.answer(
                        get_text("welcome", language),
                        reply_markup=get_main_menu_keyboard(language),
                        parse_mode="HTML",
                    )
        logger.info(f"Пользователь {user_id} принял условия обработки данных")
    except Exception as e:
        logger.error(f"Ошибка при сохранении согласия для {user.id}: {e}")
        await callback.answer(get_text("error_occurred", "ru"))

