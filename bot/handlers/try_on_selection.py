"""Обработчики выбора модели для примерки."""

from datetime import datetime

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger

from bot.database.repo import FirestoreRepo
from bot.states.user_states import TryOnStates
from bot.keyboards.user_kb import get_back_keyboard
from bot.services.storage import CloudStorageService
from bot.utils.photo_utils import get_largest_photo, download_photo_to_bytes


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
        await callback.answer("Неверный формат данных")
        return
    
    model_id = callback_data.replace("try_on_select_model_", "", 1)
    logger.info(f"Выбор модели для примерки: user_id={user_id}, model_id={model_id}")

    try:
        # Получаем модель
        models = await repo.get_user_models(user_id)
        logger.info(f"Найдено моделей: {len(models)}, их ID: {[m.id for m in models]}")
        
        selected_model = next((m for m in models if m.id == model_id), None)

        if not selected_model:
            logger.error(
                f"Модель не найдена: user_id={user_id}, model_id={model_id}, "
                f"доступные модели: {[m.id for m in models]}"
            )
            await callback.answer("Фото не найдено")
            return

        # Импортируем функцию удаления
        from bot.handlers.try_on_utils import delete_try_on_selection_messages
        
        # Удаляем все сообщения выбора модели (фотографии и сообщение с кнопками) параллельно
        await delete_try_on_selection_messages(
            bot=bot,
            chat_id=callback.from_user.id,
            state=state,
        )

        # Сохраняем выбранную модель в FSM
        await state.update_data(selected_model_gcs_uri=selected_model.gcs_uri)
        # Сбрасываем состояние выбора модели
        await state.set_state(TryOnStates.waiting_for_garment_photo)

        # Отправляем новое сообщение с инструкцией
        instruction_message = await bot.send_message(
            chat_id=callback.from_user.id,
            text=(
                "📸 Пришлите фото одежды (до 5 штук).\n\n"
                "Можно отправить одно фото или несколько фото одним альбомом."
            ),
            reply_markup=get_back_keyboard(lang),
        )
        
        # Сохраняем ID сообщения с инструкцией для последующего удаления
        await state.update_data(garment_instruction_message_id=instruction_message.message_id)

        await callback.answer("Фото выбрано")

    except Exception as e:
        logger.error(f"Ошибка в handle_model_selection_for_try_on: {e}")
        await callback.answer("Произошла ошибка")


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
        await message.answer("Пожалуйста, отправьте фото.")
        return

    try:
        user_id = str(message.from_user.id)
        
        # Получаем фото максимального размера
        largest_photo = await get_largest_photo(message.photo)
        if not largest_photo:
            await message.answer("Не удалось получить фото.")
            return
        
        # Отправляем сообщение "Обрабатываю..."
        from bot.locales.texts import get_text
        processing_message = await message.answer(get_text("processing", lang))
        processing_message_id = processing_message.message_id
        
        # Скачиваем фото
        photo_bytes = await download_photo_to_bytes(bot, largest_photo)
        
        # Генерируем уникальный путь в GCS
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination_path = f"bot_uploads/models/{user_id}_{timestamp}.jpg"
        
        # Загружаем фото модели в Cloud Storage
        logger.info(f"Сохранение фото модели для примерки в Cloud Storage: {destination_path}")
        gcs_uri = await storage_service.upload_image(
            file_bytes=photo_bytes,
            destination_path=destination_path,
        )
        logger.info(f"Фото модели сохранено: {gcs_uri}")
        
        # Сохраняем модель в БД
        model_id = await repo.add_model(
            user_id=user_id,
            gcs_uri=gcs_uri,
        )
        logger.info(f"Модель {model_id} сохранена в БД")
        
        # Удаляем сообщение "Обрабатываю..."
        try:
            await bot.delete_message(
                chat_id=message.from_user.id,
                message_id=processing_message_id,
            )
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение 'Обрабатываю...': {e}")
        
        # Удаляем все старые сообщения выбора модели (если есть)
        from bot.handlers.try_on_utils import delete_try_on_selection_messages
        await delete_try_on_selection_messages(
            bot=bot,
            chat_id=message.from_user.id,
            state=state,
        )
        
        # Сохраняем выбранную модель в FSM
        await state.update_data(selected_model_gcs_uri=gcs_uri)
        await state.set_state(TryOnStates.waiting_for_garment_photo)
        
        # Отправляем новое сообщение с инструкцией для фото одежды
        instruction_message = await bot.send_message(
            chat_id=message.from_user.id,
            text=(
                "📸 Пришлите фото одежды (до 5 штук).\n\n"
                "Можно отправить одно фото или несколько фото одним альбомом."
            ),
            reply_markup=get_back_keyboard(lang),
        )
        
        # Сохраняем ID сообщения с инструкцией для последующего удаления
        await state.update_data(garment_instruction_message_id=instruction_message.message_id)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке фото модели для примерки: {e}")
        await message.answer(
            "❌ Произошла ошибка при сохранении фото.\nПопробуйте еще раз.",
            reply_markup=get_back_keyboard(lang),
        )
