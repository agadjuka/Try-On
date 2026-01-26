"""Обработчики для работы с моделями."""

from datetime import datetime
from typing import Optional

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, BufferedInputFile
from loguru import logger

from bot.database.repo import FirestoreRepo
from bot.services.storage import CloudStorageService
from bot.states.user_states import ModelStates
from bot.keyboards.user_kb import (
    get_main_menu_keyboard,
    get_gallery_keyboard,
    get_back_keyboard,
)
from bot.locales.texts import get_text


async def get_largest_photo(photos: list) -> Optional[object]:
    """
    Получить фото с максимальным размером.

    Args:
        photos: Список размеров фото

    Returns:
        Фото с максимальным размером
    """
    if not photos:
        return None
    return photos[-1]


async def download_photo_to_bytes(bot: Bot, photo) -> bytes:
    """
    Скачать фото в байты.

    Args:
        bot: Экземпляр бота
        photo: Объект фото

    Returns:
        Байты фото
    """
    file = await bot.get_file(photo.file_id)
    
    if not file.file_path:
        raise Exception(f"Не удалось получить file_path для файла {photo.file_id}")
    
    file_io = await bot.download_file(file.file_path)
    file_bytes = file_io.read()
    file_io.close()
    
    return file_bytes


async def handle_add_model_callback(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str = "ru",
) -> None:
    """
    Обработчик кнопки "Добавить модель".

    Args:
        callback: Callback запрос
        state: Контекст FSM
        lang: Язык интерфейса
    """
    await state.set_state(ModelStates.waiting_for_model_photo)
    await callback.message.edit_text(
        get_text("upload_model_instr", lang),
        reply_markup=get_back_keyboard(lang),
    )
    await callback.answer()


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
        await message.answer("Пожалуйста, отправь фото.")
        return

    try:
        # Получаем фото максимального размера
        largest_photo = await get_largest_photo(message.photo)
        if not largest_photo:
            await message.answer("Не удалось получить фото.")
            return
        
        # Скачиваем фото
        await message.answer(get_text("processing", lang))
        photo_bytes = await download_photo_to_bytes(bot, largest_photo)
        
        # Генерируем уникальный путь в GCS
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_id = str(message.from_user.id)
        destination_path = f"bot_uploads/models/{user_id}_{timestamp}.jpg"
        
        # Загружаем фото модели в Cloud Storage
        logger.info(f"Сохранение фото модели в Cloud Storage: {destination_path}")
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
        
        # Сбрасываем состояние
        await state.clear()
        
        # Отправляем подтверждение и возвращаем в меню
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


async def handle_my_models_callback(
    callback: CallbackQuery,
    bot: Bot,
    repo: FirestoreRepo,
    storage_service: CloudStorageService,
    lang: str = "ru",
) -> None:
    """
    Обработчик кнопки "Мои модели".

    Args:
        callback: Callback запрос
        bot: Экземпляр бота
        repo: Репозиторий для работы с БД
        storage_service: Сервис для работы с GCS
        lang: Язык интерфейса
    """
    user_id = str(callback.from_user.id)
    
    try:
        models = await repo.get_user_models(user_id)
        
        if not models:
            await callback.message.edit_text(
                get_text("models_list_empty", lang),
                reply_markup=get_back_keyboard(lang),
            )
            await callback.answer()
            return
        
        # Показываем первую модель
        await show_model_in_gallery(
            message=callback.message,
            bot=bot,
            models=models,
            current_index=0,
            storage_service=storage_service,
            lang=lang,
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при получении моделей: {e}")
        await callback.message.edit_text(
            "Произошла ошибка при загрузке моделей.",
            reply_markup=get_back_keyboard(lang),
        )
        await callback.answer()


async def show_model_in_gallery(
    message: Message,
    bot: Bot,
    models: list,
    current_index: int,
    storage_service: CloudStorageService,
    lang: str = "ru",
) -> None:
    """
    Показать модель в галерее.

    Args:
        message: Сообщение для редактирования
        bot: Экземпляр бота
        models: Список моделей
        current_index: Индекс текущей модели
        storage_service: Сервис для работы с GCS
        lang: Язык интерфейса
    """
    if not models or current_index < 0 or current_index >= len(models):
        return
    
    model = models[current_index]
    
    try:
        # Скачиваем фото из GCS
        photo_bytes = await storage_service.download_file(model.gcs_uri)
        
        # Создаем InputMediaPhoto для редактирования сообщения
        photo_file = BufferedInputFile(
            file=photo_bytes,
            filename="model.jpg"
        )
        
        media = InputMediaPhoto(
            media=photo_file,
            caption=f"Модель {current_index + 1} из {len(models)}",
        )
        
        # Получаем клавиатуру
        keyboard = get_gallery_keyboard(
            current_index=current_index,
            total_count=len(models),
            model_id=model.id,
            lang=lang,
        )
        
        # Редактируем сообщение
        await message.edit_media(media=media, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка при показе модели: {e}")
        await message.edit_text(
            "Ошибка при загрузке фото модели.",
            reply_markup=get_back_keyboard(lang),
        )


async def handle_model_navigation(
    callback: CallbackQuery,
    bot: Bot,
    repo: FirestoreRepo,
    storage_service: CloudStorageService,
    lang: str = "ru",
) -> None:
    """
    Обработчик навигации по галерее моделей.

    Args:
        callback: Callback запрос
        bot: Экземпляр бота
        repo: Репозиторий для работы с БД
        storage_service: Сервис для работы с GCS
        lang: Язык интерфейса
    """
    user_id = str(callback.from_user.id)
    callback_data = callback.data
    
    try:
        # Получаем модели
        models = await repo.get_user_models(user_id)
        
        if not models:
            await callback.answer("Нет моделей")
            return
        
        # Определяем направление навигации и текущий индекс
        if callback_data.startswith("model_prev_"):
            # Извлекаем индекс из callback_data: "model_prev_0" -> 0
            current_index = int(callback_data.replace("model_prev_", "")) - 1
        elif callback_data.startswith("model_next_"):
            # Извлекаем индекс из callback_data: "model_next_0" -> 1
            current_index = int(callback_data.replace("model_next_", "")) + 1
        else:
            await callback.answer("Неизвестная команда")
            return
        
        # Проверяем границы
        if current_index < 0 or current_index >= len(models):
            await callback.answer("Достигнут конец списка")
            return
        
        # Показываем модель
        await show_model_in_gallery(
            message=callback.message,
            bot=bot,
            models=models,
            current_index=current_index,
            storage_service=storage_service,
            lang=lang,
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при навигации по моделям: {e}")
        await callback.answer("Ошибка при навигации")


async def handle_model_delete(
    callback: CallbackQuery,
    repo: FirestoreRepo,
    bot: Bot,
    storage_service: CloudStorageService,
    lang: str = "ru",
) -> None:
    """
    Обработчик удаления модели.

    Args:
        callback: Callback запрос
        repo: Репозиторий для работы с БД
        bot: Экземпляр бота
        storage_service: Сервис для работы с GCS
        lang: Язык интерфейса
    """
    user_id = str(callback.from_user.id)
    model_id = callback.data.split("_")[-1]
    
    try:
        # Получаем модели до удаления
        models = await repo.get_user_models(user_id)
        current_model = next((m for m in models if m.id == model_id), None)
        
        if not current_model:
            await callback.answer("Модель не найдена")
            return
        
        current_index = models.index(current_model)
        
        # Удаляем модель
        await repo.delete_model(user_id, model_id)
        
        # Получаем обновленный список
        models = await repo.get_user_models(user_id)
        
        if not models:
            # Если моделей не осталось, возвращаемся в меню
            await callback.message.edit_text(
                get_text("models_list_empty", lang),
                reply_markup=get_back_keyboard(lang),
            )
            await callback.answer(get_text("model_deleted", lang))
            return
        
        # Определяем индекс для показа после удаления
        new_index = min(current_index, len(models) - 1)
        
        # Показываем следующую модель
        await show_model_in_gallery(
            message=callback.message,
            bot=bot,
            models=models,
            current_index=new_index,
            storage_service=storage_service,
            lang=lang,
        )
        await callback.answer(get_text("model_deleted", lang))
        
    except Exception as e:
        logger.error(f"Ошибка при удалении модели: {e}")
        await callback.answer(get_text("delete_error", lang))


async def handle_back_to_menu(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str = "ru",
) -> None:
    """
    Обработчик кнопки "Назад".

    Args:
        callback: Callback запрос
        state: Контекст FSM
        lang: Язык интерфейса
    """
    await state.clear()
    await callback.message.edit_text(
        get_text("welcome", lang),
        reply_markup=get_main_menu_keyboard(lang),
    )
    await callback.answer()
