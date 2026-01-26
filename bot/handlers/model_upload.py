"""Обработчики загрузки моделей."""

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from loguru import logger

from bot.database.repo import FirestoreRepo
from bot.services.storage import CloudStorageService
from bot.states.user_states import ModelStates
from bot.keyboards.user_kb import get_main_menu_keyboard, get_back_keyboard
from bot.locales.texts import get_text
from bot.utils.photo_utils import get_largest_photo, download_photo_to_bytes
from bot.utils.model_utils import process_model_photo
from bot.utils.message_utils import delete_models_menu_messages, delete_messages
from bot.admin.factory import get_admin_service


async def handle_add_model_callback(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str = "ru",
) -> None:
    """
    Обработчик кнопки "Добавить модель" из главного меню.

    Args:
        callback: Callback запрос
        state: Контекст FSM
        lang: Язык интерфейса
    """
    # Мгновенно отвечаем на callback - убирает "часики" на кнопке
    await callback.answer()
    
    await state.set_state(ModelStates.waiting_for_model_photo)
    await callback.message.edit_text(
        get_text("upload_model_instr", lang),
        reply_markup=get_back_keyboard(lang),
    )
    await state.update_data(
        models_menu_message_id=callback.message.message_id,
        models_album_message_ids=[],
    )


async def handle_add_new_model_from_list(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    lang: str = "ru",
) -> None:
    """
    Обработчик кнопки "Добавить новую модель" из списка моделей.

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
    old_album_ids = state_data.get("models_album_message_ids", [])
    old_menu_id = state_data.get("models_menu_message_id")
    
    await state.set_state(ModelStates.waiting_for_model_photo)
    
    # СНАЧАЛА показываем новое сообщение
    instruction_message = await bot.send_message(
        chat_id=callback.from_user.id,
        text=get_text("upload_model_instr", lang),
        reply_markup=get_back_keyboard(lang),
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


async def handle_model_photo(
    message: Message,
    state: FSMContext,
    bot: Bot,
    repo: FirestoreRepo,
    storage_service: CloudStorageService,
    lang: str = "ru",
) -> None:
    """
    Обработчик загрузки фото модели.

    Args:
        message: Сообщение с фото
        state: Контекст FSM
        bot: Экземпляр бота
        repo: Репозиторий для работы с БД
        storage_service: Сервис для работы с GCS
        lang: Язык интерфейса
    """
    if not message.photo:
        await message.answer(get_text("send_photo_please", lang))
        return

    try:
        largest_photo = await get_largest_photo(message.photo)
        if not largest_photo:
            await message.answer(get_text("photo_get_error", lang))
            return
        
        processing_message = await message.answer(get_text("processing", lang))
        processing_message_id = processing_message.message_id
        
        photo_bytes = await download_photo_to_bytes(bot, largest_photo)
        
        user_id = str(message.from_user.id)
        model_id, gcs_uri = await process_model_photo(
            bot=bot,
            photo_bytes=photo_bytes,
            user_id=user_id,
            repo=repo,
            storage_service=storage_service,
        )
        
        # Отправляем фото модели в админ-панель (если настроено)
        logger.info(f"🔍 Попытка отправить фото модели в админ-панель для user_id={message.from_user.id}...")
        admin_service = get_admin_service(bot)
        if admin_service:
            logger.info("✅ AdminPanelService получен, отправка фото модели...")
            try:
                await admin_service.send_model_photo(
                    user=message.from_user,
                    photo_bytes=photo_bytes,
                    caption="Добавлено новое фото модели",
                )
                logger.success(f"✅ Фото модели успешно отправлено в админ-панель")
            except Exception as e:
                logger.error(f"❌ Не удалось отправить фото модели в админ-панель: {e}", exc_info=True)
        else:
            logger.warning("⚠️ AdminPanelService недоступен, фото модели не будет отправлено в админ-панель")
        
        try:
            await bot.delete_message(
                chat_id=message.from_user.id,
                message_id=processing_message_id,
            )
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение 'Обрабатываю...': {e}")
        
        state_data = await state.get_data()
        instruction_message_id = state_data.get("models_menu_message_id")
        if instruction_message_id:
            try:
                await bot.delete_message(
                    chat_id=message.from_user.id,
                    message_id=instruction_message_id,
                )
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение с инструкцией: {e}")
        
        await state.clear()
        
        await message.answer(
            get_text("model_saved", lang),
            reply_markup=get_main_menu_keyboard(lang),
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке фото модели: {e}")
        await message.answer(
            get_text("model_upload_error", lang),
            reply_markup=get_back_keyboard(lang),
        )
