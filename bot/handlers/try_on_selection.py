"""Обработчики выбора модели для примерки."""

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger

from bot.database.repo import FirestoreRepo
from bot.states.user_states import TryOnStates
from bot.keyboards.user_kb import get_back_keyboard
from bot.services.storage import CloudStorageService
from bot.locales.texts import get_text
from bot.utils.photo_utils import get_largest_photo, download_photo_to_bytes
from bot.handlers.try_on_utils import delete_try_on_selection_messages
from bot.utils.model_utils import process_model_photo


async def handle_model_selection_for_try_on(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    repo: FirestoreRepo,
    lang: str = "ru",
) -> None:
    """
    Обработчик выбора модели для примерки.

    Args:
        callback: Callback запрос
        state: Контекст FSM
        bot: Экземпляр бота
        repo: Репозиторий для работы с БД
        lang: Язык интерфейса
    """
    user_id = str(callback.from_user.id)
    
    # Извлекаем model_id из callback_data
    callback_data = callback.data
    if not callback_data or not callback_data.startswith("try_on_select_model_"):
        logger.error(f"Неверный формат callback_data: {callback_data}")
        await callback.answer(get_text("invalid_data_format", lang))
        return
    
    model_id = callback_data.replace("try_on_select_model_", "", 1)
    logger.info(f"Выбор модели для примерки: user_id={user_id}, model_id={model_id}")

    try:
        models = await repo.get_user_models(user_id)
        logger.info(f"Найдено моделей: {len(models)}, их ID: {[m.id for m in models]}")
        
        selected_model = next((m for m in models if m.id == model_id), None)

        if not selected_model:
            logger.error(
                f"Модель не найдена: user_id={user_id}, model_id={model_id}, "
                f"доступные модели: {[m.id for m in models]}"
            )
            await callback.answer(get_text("photo_not_found", lang))
            return

        await delete_try_on_selection_messages(
            bot=bot,
            chat_id=callback.from_user.id,
            state=state,
        )

        await state.update_data(selected_model_gcs_uri=selected_model.gcs_uri)
        await state.set_state(TryOnStates.waiting_for_garment_photo)

        instruction_message = await bot.send_message(
            chat_id=callback.from_user.id,
            text=get_text("try_on_garment_instr", lang),
            reply_markup=get_back_keyboard(lang),
        )
        
        await state.update_data(garment_instruction_message_id=instruction_message.message_id)

        await callback.answer(get_text("photo_selected", lang))

    except Exception as e:
        logger.error(f"Ошибка в handle_model_selection_for_try_on: {e}")
        await callback.answer(get_text("error_occurred", lang))


async def handle_model_photo_for_try_on(
    message: Message,
    state: FSMContext,
    bot: Bot,
    repo: FirestoreRepo,
    storage_service: CloudStorageService,
    lang: str = "ru",
) -> None:
    """
    Обработчик фото модели при примерке.
    Сохраняет фото как модель и переходит к следующему шагу (ожидание фото одежды).

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
        user_id = str(message.from_user.id)
        
        largest_photo = await get_largest_photo(message.photo)
        if not largest_photo:
            await message.answer(get_text("photo_get_error", lang))
            return
        
        processing_message = await message.answer(get_text("processing", lang))
        processing_message_id = processing_message.message_id
        
        photo_bytes = await download_photo_to_bytes(bot, largest_photo)
        
        model_id, gcs_uri = await process_model_photo(
            bot=bot,
            photo_bytes=photo_bytes,
            user_id=user_id,
            repo=repo,
            storage_service=storage_service,
        )
        
        try:
            await bot.delete_message(
                chat_id=message.from_user.id,
                message_id=processing_message_id,
            )
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение 'Обрабатываю...': {e}")
        
        await delete_try_on_selection_messages(
            bot=bot,
            chat_id=message.from_user.id,
            state=state,
        )
        
        await state.update_data(selected_model_gcs_uri=gcs_uri)
        await state.set_state(TryOnStates.waiting_for_garment_photo)
        
        instruction_message = await bot.send_message(
            chat_id=message.from_user.id,
            text=get_text("try_on_garment_instr", lang),
            reply_markup=get_back_keyboard(lang),
        )
        
        await state.update_data(garment_instruction_message_id=instruction_message.message_id)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке фото модели для примерки: {e}")
        await message.answer(
            get_text("model_upload_error", lang),
            reply_markup=get_back_keyboard(lang),
        )
