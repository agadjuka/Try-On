"""Обработчики навигации."""

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger

from bot.keyboards.user_kb import get_main_menu_keyboard
from bot.locales.texts import get_text
from bot.utils.message_utils import delete_models_menu_messages
from bot.handlers.try_on_utils import delete_try_on_selection_messages


async def handle_back_to_menu(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    lang: str = "ru",
) -> None:
    """
    Обработчик кнопки "Назад".
    Удаляет все сообщения меню моделей/примерки и возвращает в главное меню.

    Args:
        callback: Callback запрос
        state: Контекст FSM
        bot: Экземпляр бота
        lang: Язык интерфейса
    """
    state_data = await state.get_data()
    
    await delete_models_menu_messages(
        bot=bot,
        chat_id=callback.from_user.id,
        state=state,
    )
    
    await delete_try_on_selection_messages(
        bot=bot,
        chat_id=callback.from_user.id,
        state=state,
    )
    
    garment_instruction_message_id = state_data.get("garment_instruction_message_id")
    if garment_instruction_message_id:
        try:
            await bot.delete_message(
                chat_id=callback.from_user.id,
                message_id=garment_instruction_message_id,
            )
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение с инструкцией: {e}")
    
    result_message_id = state_data.get("try_on_result_message_id")
    if result_message_id:
        try:
            await bot.delete_message(
                chat_id=callback.from_user.id,
                message_id=result_message_id,
            )
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение с кнопками результата: {e}")
    
    await state.clear()
    
    await bot.send_message(
        chat_id=callback.from_user.id,
        text=get_text("welcome", lang),
        reply_markup=get_main_menu_keyboard(lang),
    )
    
    await callback.answer()
