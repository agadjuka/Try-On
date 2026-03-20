"""Обработчики списка моделей."""

import asyncio

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, BufferedInputFile
from loguru import logger

from bot.database.repo import FirestoreRepo
from bot.services.storage import CloudStorageService
from bot.services.result_cleanup import cleanup_user_results
from bot.states.user_states import ModelStates
from bot.keyboards.user_kb import (
    get_main_menu_keyboard,
    get_back_keyboard,
    get_models_list_keyboard,
)
from bot.locales.texts import get_text
from bot.utils.message_utils import delete_models_menu_messages, delete_messages
from bot.utils.model_utils import prepare_models_media_group
from bot.services.instruction_photo import show_instruction_photo
from bot.services.instruction_photo import delete_instruction_photo


async def handle_my_models_callback(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    repo: FirestoreRepo,
    storage_service: CloudStorageService,
    lang: str = "ru",
) -> None:
    """
    Обработчик кнопки "Мои модели".
    Отправляет альбом со всеми моделями и клавиатуру управления.

    Args:
        callback: Callback запрос
        state: Контекст FSM
        bot: Экземпляр бота
        repo: Репозиторий для работы с БД
        storage_service: Сервис для работы с GCS
        lang: Язык интерфейса
    """
    # Мгновенно отвечаем на callback - убирает "часики" на кнопке
    await callback.answer()
    
    user_id = str(callback.from_user.id)
    
    # Сохраняем старые ID ДО любых изменений state
    state_data = await state.get_data()
    old_album_ids = state_data.get("models_album_message_ids", [])
    old_menu_id = state_data.get("models_menu_message_id")
    result_message_id = state_data.get("try_on_result_message_id")
    result_album_message_ids = state_data.get("try_on_result_album_message_ids", [])
    
    # Удаляем только сообщение с кнопками (фотографии остаются в чате)
    if result_message_id:
        try:
            await bot.delete_message(chat_id=callback.from_user.id, message_id=result_message_id)
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение с кнопками: {e}")
    
    # Фотографии результатов НЕ удаляем из чата - они остаются для пользователя
    
    try:
        await delete_instruction_photo(bot, state, callback.from_user.id)
        models = await repo.get_user_models(user_id)
        
        if not models:
            await state.set_state(ModelStates.waiting_for_model_photo)
            await show_instruction_photo(bot, state, callback.from_user.id)
            
            # СНАЧАЛА показываем новое сообщение
            instruction_message = await bot.send_message(
                chat_id=callback.from_user.id,
                text=get_text("upload_model_instr", lang),
                reply_markup=get_back_keyboard(lang),
                parse_mode="HTML",
            )
            
            await state.update_data(
                models_menu_message_id=instruction_message.message_id,
                models_album_message_ids=[],
            )
            
            # ПОТОМ удаляем старые по сохранённым ID
            old_ids_to_delete = list(old_album_ids)
            if old_menu_id:
                old_ids_to_delete.append(old_menu_id)
            await delete_messages(bot, callback.from_user.id, old_ids_to_delete)
            
            try:
                await callback.message.delete()
            except Exception:
                pass
            
            return
        
        # Скачиваем фото параллельно (уже оптимизировано в prepare_models_media_group)
        media_group = await prepare_models_media_group(models, storage_service)
        
        # СНАЧАЛА отправляем новый контент
        album_message_ids = []
        if media_group:
            sent_messages = await bot.send_media_group(
                chat_id=callback.from_user.id,
                media=media_group,
            )
            album_message_ids = [msg.message_id for msg in sent_messages] if sent_messages else []
        
        menu_message = await bot.send_message(
            chat_id=callback.from_user.id,
            text=get_text("my_photos_title", lang),
            reply_markup=get_models_list_keyboard(models, lang),
        )
        
        await state.update_data(
            models_album_message_ids=album_message_ids,
            models_menu_message_id=menu_message.message_id,
            try_on_result_message_id=None,
            try_on_result_album_message_ids=[],
        )
        
        # ПОТОМ удаляем старые по сохранённым ID
        old_ids_to_delete = list(old_album_ids)
        if old_menu_id:
            old_ids_to_delete.append(old_menu_id)
        await delete_messages(bot, callback.from_user.id, old_ids_to_delete)
        
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        # Запускаем очистку результатов в фоне (после открытия нового меню)
        if result_message_id or result_album_message_ids:
            asyncio.create_task(cleanup_user_results(user_id, repo, storage_service))
        
    except Exception as e:
        logger.error(f"Ошибка при получении моделей: {e}")
        error_text = get_text("models_load_error", lang)
        try:
            await callback.message.edit_text(
                error_text,
                reply_markup=get_back_keyboard(lang),
            )
        except Exception:
            await bot.send_message(
                chat_id=callback.from_user.id,
                text=error_text,
                reply_markup=get_back_keyboard(lang),
            )


async def handle_model_delete(
    callback: CallbackQuery,
    state: FSMContext,
    repo: FirestoreRepo,
    bot: Bot,
    storage_service: CloudStorageService,
    lang: str = "ru",
) -> None:
    """
    Обработчик удаления модели.
    После удаления обновляет список моделей.

    Args:
        callback: Callback запрос
        state: Контекст FSM
        repo: Репозиторий для работы с БД
        bot: Экземпляр бота
        storage_service: Сервис для работы с GCS
        lang: Язык интерфейса
    """
    user_id = str(callback.from_user.id)
    
    callback_data = callback.data
    if not callback_data or not callback_data.startswith("model_delete_"):
        logger.error(f"Неверный формат callback_data: {callback_data}")
        await callback.answer(get_text("invalid_data_format", lang))
        return
    
    # Мгновенно отвечаем с сообщением об удалении
    await callback.answer(get_text("model_deleted", lang))
    
    # Сохраняем ТЕКУЩИЕ отображаемые ID ДО любых изменений state
    # Это те сообщения, которые нужно удалить (альбом + сообщение с кнопками)
    state_data = await state.get_data()
    current_album_ids = state_data.get("models_album_message_ids", [])
    current_menu_id = state_data.get("models_menu_message_id")
    callback_message_id = callback.message.message_id if callback.message else None
    
    model_id = callback_data.replace("model_delete_", "", 1)
    
    try:
        models = await repo.get_user_models(user_id)
        
        model_to_delete = next((m for m in models if m.id == model_id), None)
        
        if not model_to_delete:
            return
        
        try:
            await storage_service.delete_file(model_to_delete.gcs_uri)
        except Exception:
            pass
        
        await repo.delete_model(user_id, model_id)
        
        models = await repo.get_user_models(user_id)
        
        if not models:
            # СНАЧАЛА показываем новое
            empty_list_message = await bot.send_message(
                chat_id=callback.from_user.id,
                text=get_text("models_list_empty", lang),
                reply_markup=get_back_keyboard(lang),
            )
            await state.update_data(
                models_menu_message_id=empty_list_message.message_id,
                models_album_message_ids=[],
            )
            # ПОТОМ удаляем ВСЕ старые сообщения: альбом + сообщение с кнопками + само сообщение callback
            ids_to_delete = list(current_album_ids)
            if current_menu_id:
                ids_to_delete.append(current_menu_id)
            if callback_message_id and callback_message_id not in ids_to_delete:
                ids_to_delete.append(callback_message_id)
            await delete_messages(bot, callback.from_user.id, ids_to_delete)
            return
        
        media_group = await prepare_models_media_group(models, storage_service)
        
        # СНАЧАЛА показываем новое
        album_message_ids = []
        if media_group:
            sent_messages = await bot.send_media_group(
                chat_id=callback.from_user.id,
                media=media_group,
            )
            album_message_ids = [msg.message_id for msg in sent_messages] if sent_messages else []
        
        menu_message = await bot.send_message(
            chat_id=callback.from_user.id,
            text=get_text("my_photos_title", lang),
            reply_markup=get_models_list_keyboard(models, lang),
        )
        
        await state.update_data(
            models_album_message_ids=album_message_ids,
            models_menu_message_id=menu_message.message_id,
        )
        
        # ПОТОМ удаляем ВСЕ старые сообщения: альбом + сообщение с кнопками + само сообщение callback
        ids_to_delete = list(current_album_ids)
        if current_menu_id:
            ids_to_delete.append(current_menu_id)
        if callback_message_id and callback_message_id not in ids_to_delete:
            ids_to_delete.append(callback_message_id)
        await delete_messages(bot, callback.from_user.id, ids_to_delete)
        
    except Exception as e:
        logger.error(f"Ошибка при удалении модели: {e}")
