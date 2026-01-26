"""Обработчики списка моделей."""

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, BufferedInputFile
from loguru import logger

from bot.database.repo import FirestoreRepo
from bot.services.storage import CloudStorageService
from bot.states.user_states import ModelStates
from bot.keyboards.user_kb import (
    get_main_menu_keyboard,
    get_back_keyboard,
    get_models_list_keyboard,
)
from bot.locales.texts import get_text
from bot.utils.message_utils import delete_models_menu_messages
from bot.utils.model_utils import prepare_models_media_group


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
    user_id = str(callback.from_user.id)
    
    try:
        models = await repo.get_user_models(user_id)
        
        if not models:
            await delete_models_menu_messages(
                bot=bot,
                chat_id=callback.from_user.id,
                state=state,
            )
            
            try:
                await callback.message.delete()
            except Exception:
                pass
            
            await state.set_state(ModelStates.waiting_for_model_photo)
            
            instruction_message = await bot.send_message(
                chat_id=callback.from_user.id,
                text=get_text("upload_model_instr", lang),
                reply_markup=get_back_keyboard(lang),
            )
            
            await state.update_data(
                models_menu_message_id=instruction_message.message_id,
                models_album_message_ids=[],
            )
            
            await callback.answer()
            return
        
        await delete_models_menu_messages(
            bot=bot,
            chat_id=callback.from_user.id,
            state=state,
        )
        
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        media_group = await prepare_models_media_group(models, storage_service)
        
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
        
        await callback.answer()
        
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
        await callback.answer()


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
    
    model_id = callback_data.replace("model_delete_", "", 1)
    logger.info(f"Удаление модели: user_id={user_id}, model_id={model_id}")
    
    try:
        models = await repo.get_user_models(user_id)
        logger.info(f"Найдено моделей: {len(models)}, их ID: {[m.id for m in models]}")
        
        model_to_delete = next((m for m in models if m.id == model_id), None)
        
        if not model_to_delete:
            logger.error(
                f"Модель не найдена: user_id={user_id}, model_id={model_id}, "
                f"доступные модели: {[m.id for m in models]}"
            )
            await callback.answer(get_text("photo_not_found", lang))
            return
        
        try:
            await storage_service.delete_file(model_to_delete.gcs_uri)
            logger.info(f"Файл модели удален из GCS: {model_to_delete.gcs_uri}")
        except Exception as e:
            logger.warning(f"Не удалось удалить файл из GCS: {e}")
        
        await repo.delete_model(user_id, model_id)
        
        models = await repo.get_user_models(user_id)
        
        await delete_models_menu_messages(
            bot=bot,
            chat_id=callback.from_user.id,
            state=state,
        )
        
        if not models:
            empty_list_message = await bot.send_message(
                chat_id=callback.from_user.id,
                text=get_text("models_list_empty", lang),
                reply_markup=get_back_keyboard(lang),
            )
            await state.update_data(
                models_menu_message_id=empty_list_message.message_id,
                models_album_message_ids=[],
            )
            await callback.answer(get_text("model_deleted", lang))
            return
        
        media_group = await prepare_models_media_group(models, storage_service)
        
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
        
        await callback.answer(get_text("model_deleted", lang))
        
    except Exception as e:
        logger.error(f"Ошибка при удалении модели: {e}")
        await callback.answer(get_text("delete_error", lang))
