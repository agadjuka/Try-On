"""Обработчики навигации."""

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger

from bot.keyboards.user_kb import get_main_menu_keyboard
from bot.locales.texts import get_text
from bot.services.instruction_photo import INSTRUCTION_PHOTO_MESSAGE_ID_KEY


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
    # Мгновенно отвечаем на callback - убирает "часики" на кнопке
    await callback.answer()
    
    # Сохраняем старые ID ДО любых изменений state
    state_data = await state.get_data()
    old_models_album_ids = state_data.get("models_album_message_ids", [])
    old_models_menu_id = state_data.get("models_menu_message_id")
    old_album_ids = state_data.get("album_message_ids", [])
    old_selection_id = state_data.get("selection_message_id")
    garment_instruction_message_id = state_data.get("garment_instruction_message_id")
    instruction_photo_message_id = state_data.get(INSTRUCTION_PHOTO_MESSAGE_ID_KEY)
    result_message_id = state_data.get("try_on_result_message_id")
    callback_message_id = callback.message.message_id if callback.message else None
    
    # СНАЧАЛА показываем новое меню - пользователь сразу видит результат
    await bot.send_message(
        chat_id=callback.from_user.id,
        text=get_text("welcome", lang),
        reply_markup=get_main_menu_keyboard(lang),
        parse_mode="HTML",
    )
    
    # ПОТОМ удаляем ВСЕ старые сообщения по СОХРАНЁННЫМ ID
    from bot.utils.message_utils import delete_messages
    
    ids_to_delete = []
    ids_to_delete.extend(old_models_album_ids)
    if old_models_menu_id:
        ids_to_delete.append(old_models_menu_id)
    ids_to_delete.extend(old_album_ids)
    if old_selection_id:
        ids_to_delete.append(old_selection_id)
    if garment_instruction_message_id:
        ids_to_delete.append(garment_instruction_message_id)
    if instruction_photo_message_id:
        ids_to_delete.append(instruction_photo_message_id)
    if result_message_id:
        ids_to_delete.append(result_message_id)
    if callback_message_id and callback_message_id not in ids_to_delete:
        ids_to_delete.append(callback_message_id)
    
    await delete_messages(bot, callback.from_user.id, ids_to_delete)
    
    await state.clear()
