"""Вспомогательные функции для примерки."""

from typing import List

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, BufferedInputFile
from loguru import logger

from bot.services.storage import CloudStorageService
from bot.keyboards.user_kb import get_back_keyboard, get_model_selection_keyboard
from bot.locales.texts import get_text
from bot.utils.message_utils import delete_messages


async def delete_try_on_selection_messages(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
) -> None:
    """
    Удалить все сообщения выбора модели для примерки (фотографии и сообщение с кнопками).

    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        state: Контекст FSM
    """
    state_data = await state.get_data()
    album_message_ids = state_data.get("album_message_ids", [])
    selection_message_id = state_data.get("selection_message_id")
    
    message_ids_to_delete = list(album_message_ids)
    if selection_message_id:
        message_ids_to_delete.append(selection_message_id)
    
    await delete_messages(bot, chat_id, message_ids_to_delete)
    
    # Очищаем данные из FSM
    # Важно: сохраняем существующие try_on_result_album_message_ids, чтобы не удалить фотографии результата
    existing_result_album_ids = state_data.get("try_on_result_album_message_ids", [])
    await state.update_data(
        album_message_ids=[],
        selection_message_id=None,
        try_on_result_album_message_ids=existing_result_album_ids,  # Сохраняем фотографии результата
    )


async def send_models_album(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    models: List,
    storage_service: CloudStorageService,
    lang: str = "ru",
) -> bool:
    """
    Отправить альбом с фотографиями моделей.

    Args:
        callback: Callback запрос
        state: Контекст FSM
        bot: Экземпляр бота
        models: Список моделей
        storage_service: Сервис для работы с GCS
        lang: Язык интерфейса

    Returns:
        True если успешно, False иначе
    """
    try:
        from bot.utils.model_utils import prepare_models_media_group
        
        media_group = await prepare_models_media_group(models, storage_service)

        if not media_group:
            await callback.message.edit_text(
                get_text("models_album_error", lang),
                reply_markup=get_back_keyboard(lang),
            )
            await callback.answer()
            return False

        # Удаляем все предыдущие сообщения выбора модели (если есть)
        await delete_try_on_selection_messages(
            bot=bot,
            chat_id=callback.from_user.id,
            state=state,
        )
        
        # Удаляем исходное сообщение с кнопкой "Примерка"
        try:
            await callback.message.delete()
        except Exception:
            pass

        # Сохраняем существующие try_on_result_album_message_ids ПЕРЕД отправкой нового альбома
        # Это важно, чтобы не потерять ID фотографий результата
        state_data_before = await state.get_data()
        existing_result_album_ids = state_data_before.get("try_on_result_album_message_ids", [])
        logger.info(f"Сохраняем ID фотографий результата перед отправкой альбома моделей: {existing_result_album_ids}")
        
        # Отправляем альбом с фото моделей
        sent_messages = await bot.send_media_group(
            chat_id=callback.from_user.id,
            media=media_group,
        )

        # Сохраняем ID сообщений альбома в FSM для последующего удаления
        # Важно: сохраняем существующие try_on_result_album_message_ids, чтобы не удалить фотографии результата
        album_message_ids = [msg.message_id for msg in sent_messages] if sent_messages else []
        await state.update_data(
            album_message_ids=album_message_ids,
            try_on_result_album_message_ids=existing_result_album_ids,  # Сохраняем фотографии результата
        )
        logger.info(f"Восстановили ID фотографий результата после отправки альбома моделей: {existing_result_album_ids}")

        # Отправляем сообщение с кнопками (после фотографий)
        from bot.states.user_states import TryOnStates
        
        selection_message = await bot.send_message(
            chat_id=callback.from_user.id,
            text=get_text("try_on_select_model_or_photo", lang),
            reply_markup=get_model_selection_keyboard(models, lang),
        )
        
        # Устанавливаем состояние ожидания выбора модели или фото
        # Это позволит обработать фото, если пользователь пришлет его вместо нажатия кнопки
        await state.set_state(TryOnStates.waiting_for_model_photo)

        # Сохраняем ID сообщения с кнопками для последующего удаления
        await state.update_data(selection_message_id=selection_message.message_id)

        return True

    except Exception as e:
        logger.error(f"Ошибка при отправке альбома моделей: {e}")
        return False
