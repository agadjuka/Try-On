"""Обработчик выбора языка."""

from aiogram import Bot
from aiogram.types import CallbackQuery
from loguru import logger

from bot.database.repo import FirestoreRepo
from bot.services.language import set_user_language, get_user_language
from bot.keyboards.user_kb import get_main_menu_keyboard
from bot.locales.texts import get_text
from bot.admin.factory import get_admin_service


async def handle_language_selection(
    callback: CallbackQuery,
    bot: Bot,
    repo: FirestoreRepo,
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
        # Получаем user_id
        user_id = str(user.id)
        
        # Сохраняем язык
        await set_user_language(repo, user.id, language, user_id)
        
        # Отвечаем на callback
        await callback.answer(get_text("language_selected", language))
        
        # Создаем топик в админ-панели (если настроено)
        admin_service = get_admin_service(bot)
        if admin_service:
            try:
                await admin_service.get_or_create_topic(user)
            except Exception:
                pass
        
        # Отправляем приветствие и главное меню на выбранном языке
        await callback.message.edit_text(
            get_text("welcome", language),
            reply_markup=get_main_menu_keyboard(language),
            parse_mode="HTML",
        )
        
        logger.info(f"Пользователь {user.id} выбрал язык: {language}")
        
    except Exception as e:
        logger.error(f"Ошибка при выборе языка для пользователя {user.id}: {e}")
        await callback.answer(get_text("error_occurred", language))
