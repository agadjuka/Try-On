"""Обработчик выбора языка."""

from aiogram import Bot
from aiogram.types import CallbackQuery
from loguru import logger

from bot.database.repo_factory import UserRepository
from bot.services.language import set_user_language, get_user_language
from bot.keyboards.user_kb import get_main_menu_keyboard, get_privacy_consent_keyboard
from bot.locales.texts import get_text
from bot.admin.factory import get_admin_service


async def handle_language_selection(
    callback: CallbackQuery,
    bot: Bot,
    repo: UserRepository,
) -> None:
    """
    Обработчик выбора языка.

    Args:
        callback: Callback запрос
        bot: Экземпляр бота
        repo: Репозиторий для работы с БД
    """
    user = callback.from_user
    
    # Извлекаем язык из callback_data (select_language_ru или select_language_en)
    if not callback.data:
        return
    
    language = callback.data.replace("select_language_", "")
    
    if language not in ["ru", "en"]:
        logger.warning(f"Неверный язык: {language}")
        return
    
    try:
        # Сохраняем язык (user_id всегда равен str(user.id), не передаем его)
        await set_user_language(repo, user.id, language)
        
        # Отвечаем на callback
        await callback.answer(get_text("language_selected", language))
        
        # Создаем топик в админ-панели (если настроено)
        admin_service = get_admin_service(bot)
        if admin_service:
            try:
                await admin_service.get_or_create_topic(user)
            except Exception:
                pass
        
        # Условия обработки данных — до приветствия
        await callback.message.edit_text(
            get_text("privacy_notice", language),
            reply_markup=get_privacy_consent_keyboard(language),
            parse_mode="HTML",
        )
        
        logger.info(f"Пользователь {user.id} выбрал язык: {language}")
        
    except Exception as e:
        logger.error(f"Ошибка при выборе языка для пользователя {user.id}: {e}")
        # Используем выбранный язык для ошибки (language уже определена выше)
        await callback.answer(get_text("error_occurred", language))


async def handle_switch_language(
    callback: CallbackQuery,
    bot: Bot,
    repo: UserRepository,
) -> None:
    """
    Обработчик смены языка.

    Args:
        callback: Callback запрос
        bot: Экземпляр бота
        repo: Репозиторий для работы с БД
    """
    user = callback.from_user
    
    try:
        # Получаем текущий язык (user_id всегда равен str(user.id), не передаем его)
        current_language = await get_user_language(repo, user.id)
        
        # Инвертируем язык
        new_language = "en" if current_language == "ru" else "ru"
        
        # Сохраняем новый язык (user_id всегда равен str(user.id), не передаем его)
        await set_user_language(repo, user.id, new_language)
        
        # Отвечаем на callback
        await callback.answer(get_text("language_changed", new_language))

        user_id = str(user.id)
        if not await repo.get_privacy_consent_accepted(user_id):
            await callback.message.edit_text(
                get_text("privacy_notice", new_language),
                reply_markup=get_privacy_consent_keyboard(new_language),
                parse_mode="HTML",
            )
            return

        await callback.message.edit_text(
            get_text("welcome", new_language),
            reply_markup=get_main_menu_keyboard(new_language),
            parse_mode="HTML",
        )
        
        logger.info(f"Пользователь {user.id} сменил язык с {current_language} на {new_language}")
        
    except Exception as e:
        logger.error(f"Ошибка при смене языка для пользователя {user.id}: {e}")
        # Используем русский по умолчанию для ошибок
        await callback.answer(get_text("error_occurred", "ru"))
