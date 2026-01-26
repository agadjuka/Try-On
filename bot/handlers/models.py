"""Обработчики для работы с моделями."""

import asyncio
from datetime import datetime
from typing import Optional, List

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
    get_models_list_keyboard,
)
from bot.locales.texts import get_text
from bot.utils.photo_utils import get_largest_photo, download_photo_to_bytes


async def delete_models_menu_messages(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
) -> None:
    """
    Удалить все сообщения меню моделей (фотографии и сообщение с кнопками).
    Удаление происходит параллельно для скорости.

    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        state: Контекст FSM
    """
    state_data = await state.get_data()
    album_message_ids = state_data.get("models_album_message_ids", [])
    menu_message_id = state_data.get("models_menu_message_id")
    
    # Собираем все ID сообщений для удаления
    message_ids_to_delete = list(album_message_ids)
    if menu_message_id:
        message_ids_to_delete.append(menu_message_id)
    
    if not message_ids_to_delete:
        return
    
    # Удаляем все сообщения параллельно
    delete_tasks = []
    for msg_id in message_ids_to_delete:
        delete_tasks.append(
            bot.delete_message(chat_id=chat_id, message_id=msg_id)
        )
    
    # Выполняем удаление параллельно, игнорируем ошибки
    await asyncio.gather(*delete_tasks, return_exceptions=True)
    
    # Очищаем данные из FSM
    await state.update_data(
        models_album_message_ids=[],
        models_menu_message_id=None,
    )


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
    await state.set_state(ModelStates.waiting_for_model_photo)
    await callback.message.edit_text(
        get_text("upload_model_instr", lang),
        reply_markup=get_back_keyboard(lang),
    )
    # Сохраняем ID сообщения с инструкцией для последующего удаления
    await state.update_data(
        models_menu_message_id=callback.message.message_id,
        models_album_message_ids=[],
    )
    await callback.answer()


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
    await state.set_state(ModelStates.waiting_for_model_photo)
    
    # Удаляем все сообщения меню моделей (фотографии и сообщение с кнопками)
    await delete_models_menu_messages(
        bot=bot,
        chat_id=callback.from_user.id,
        state=state,
    )
    
    # Отправляем новое сообщение с инструкцией
    instruction_message = await bot.send_message(
        chat_id=callback.from_user.id,
        text=get_text("upload_model_instr", lang),
        reply_markup=get_back_keyboard(lang),
    )
    
    # Сохраняем ID сообщения с инструкцией для последующего удаления
    await state.update_data(
        models_menu_message_id=instruction_message.message_id,
        models_album_message_ids=[],
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
        await message.answer("Пожалуйста, отправьте фото.")
        return

    try:
        # Получаем фото максимального размера
        largest_photo = await get_largest_photo(message.photo)
        if not largest_photo:
            await message.answer("Не удалось получить фото.")
            return
        
        # Отправляем сообщение "Обрабатываю..." и сохраняем его ID
        processing_message = await message.answer(get_text("processing", lang))
        processing_message_id = processing_message.message_id
        
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
        
        # Удаляем сообщение "Обрабатываю..."
        try:
            await bot.delete_message(
                chat_id=message.from_user.id,
                message_id=processing_message_id,
            )
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение 'Обрабатываю...': {e}")
        
        # Удаляем сообщение с инструкцией "Отправь фото модели" (если есть)
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
            # Удаляем все предыдущие сообщения меню моделей (если есть)
            await delete_models_menu_messages(
                bot=bot,
                chat_id=callback.from_user.id,
                state=state,
            )
            
            # Удаляем исходное сообщение из главного меню
            try:
                await callback.message.delete()
            except Exception:
                pass
            
            # Устанавливаем состояние ожидания фото модели
            await state.set_state(ModelStates.waiting_for_model_photo)
            
            # Отправляем сообщение с инструкцией добавления модели
            instruction_message = await bot.send_message(
                chat_id=callback.from_user.id,
                text=get_text("upload_model_instr", lang),
                reply_markup=get_back_keyboard(lang),
            )
            
            # Сохраняем ID сообщения с инструкцией для последующего удаления
            await state.update_data(
                models_menu_message_id=instruction_message.message_id,
                models_album_message_ids=[],
            )
            
            await callback.answer()
            return
        
        # Удаляем все предыдущие сообщения меню моделей (если есть)
        await delete_models_menu_messages(
            bot=bot,
            chat_id=callback.from_user.id,
            state=state,
        )
        
        # Удаляем исходное сообщение из главного меню
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        # Отправляем альбом со всеми моделями
        media_group = []
        for idx, model in enumerate(models):
            try:
                photo_bytes = await storage_service.download_file(model.gcs_uri)
                photo_file = BufferedInputFile(
                    file=photo_bytes,
                    filename=f"model_{idx + 1}.jpg",
                )
                media_group.append(InputMediaPhoto(media=photo_file, caption=None))
            except Exception as e:
                logger.error(f"Ошибка при загрузке фото модели {idx + 1}: {e}")
        
        album_message_ids = []
        if media_group:
            sent_messages = await bot.send_media_group(
                chat_id=callback.from_user.id,
                media=media_group,
            )
            album_message_ids = [msg.message_id for msg in sent_messages] if sent_messages else []
        
        # Отправляем сообщение с клавиатурой управления
        menu_message = await bot.send_message(
            chat_id=callback.from_user.id,
            text="👤 Ваши фото:",
            reply_markup=get_models_list_keyboard(models, lang),
        )
        
        # Сохраняем ID всех сообщений в FSM для последующего удаления
        await state.update_data(
            models_album_message_ids=album_message_ids,
            models_menu_message_id=menu_message.message_id,
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при получении моделей: {e}")
        try:
            await callback.message.edit_text(
                "Произошла ошибка при загрузке моделей.",
                reply_markup=get_back_keyboard(lang),
            )
        except Exception:
            await bot.send_message(
                chat_id=callback.from_user.id,
                text="Произошла ошибка при загрузке моделей.",
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
            caption=f"Фото {current_index + 1} из {len(models)}",
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
            await callback.answer("Нет фото")
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
        logger.error(f"Ошибка при получении моделей: {e}")
        await callback.answer("Ошибка при навигации")


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
    
    # Извлекаем model_id из callback_data
    callback_data = callback.data
    if not callback_data or not callback_data.startswith("model_delete_"):
        logger.error(f"Неверный формат callback_data: {callback_data}")
        await callback.answer("Неверный формат данных")
        return
    
    model_id = callback_data.replace("model_delete_", "", 1)
    logger.info(f"Удаление модели: user_id={user_id}, model_id={model_id}")
    
    try:
        # Получаем модель перед удалением, чтобы получить gcs_uri
        models = await repo.get_user_models(user_id)
        logger.info(f"Найдено моделей: {len(models)}, их ID: {[m.id for m in models]}")
        
        model_to_delete = next((m for m in models if m.id == model_id), None)
        
        if not model_to_delete:
            logger.error(
                f"Модель не найдена: user_id={user_id}, model_id={model_id}, "
                f"доступные модели: {[m.id for m in models]}"
            )
            await callback.answer("Фото не найдено")
            return
        
        # Удаляем файл из GCS
        try:
            await storage_service.delete_file(model_to_delete.gcs_uri)
            logger.info(f"Файл модели удален из GCS: {model_to_delete.gcs_uri}")
        except Exception as e:
            logger.warning(f"Не удалось удалить файл из GCS: {e}")
        
        # Удаляем модель из БД
        await repo.delete_model(user_id, model_id)
        
        # Получаем обновленный список
        models = await repo.get_user_models(user_id)
        
        # Удаляем все старые сообщения меню моделей (фотографии и сообщение с кнопками)
        await delete_models_menu_messages(
            bot=bot,
            chat_id=callback.from_user.id,
            state=state,
        )
        
        if not models:
            # Если моделей не осталось
            empty_list_message = await bot.send_message(
                chat_id=callback.from_user.id,
                text=get_text("models_list_empty", lang),
                reply_markup=get_back_keyboard(lang),
            )
            # Сохраняем ID сообщения для последующего удаления
            await state.update_data(
                models_menu_message_id=empty_list_message.message_id,
                models_album_message_ids=[],
            )
            await callback.answer(get_text("model_deleted", lang))
            return
        
        # Отправляем обновленный альбом со всеми моделями
        media_group = []
        for idx, model in enumerate(models):
            try:
                photo_bytes = await storage_service.download_file(model.gcs_uri)
                photo_file = BufferedInputFile(
                    file=photo_bytes,
                    filename=f"model_{idx + 1}.jpg",
                )
                media_group.append(InputMediaPhoto(media=photo_file, caption=None))
            except Exception as e:
                logger.error(f"Ошибка при загрузке фото модели {idx + 1}: {e}")
        
        album_message_ids = []
        if media_group:
            sent_messages = await bot.send_media_group(
                chat_id=callback.from_user.id,
                media=media_group,
            )
            album_message_ids = [msg.message_id for msg in sent_messages] if sent_messages else []
        
        # Отправляем обновленное сообщение с клавиатурой
        menu_message = await bot.send_message(
            chat_id=callback.from_user.id,
            text="👤 Ваши фото:",
            reply_markup=get_models_list_keyboard(models, lang),
        )
        
        # Сохраняем ID всех новых сообщений в FSM
        await state.update_data(
            models_album_message_ids=album_message_ids,
            models_menu_message_id=menu_message.message_id,
        )
        
        await callback.answer(get_text("model_deleted", lang))
        
    except Exception as e:
        logger.error(f"Ошибка при удалении модели: {e}")
        await callback.answer(get_text("delete_error", lang))


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
    # Импортируем функцию удаления сообщений примерки
    from bot.handlers.try_on_utils import delete_try_on_selection_messages
    
    # Получаем данные из FSM
    state_data = await state.get_data()
    
    # Удаляем все сообщения меню моделей (фотографии и сообщение с кнопками)
    await delete_models_menu_messages(
        bot=bot,
        chat_id=callback.from_user.id,
        state=state,
    )
    
    # Удаляем все сообщения выбора модели для примерки
    await delete_try_on_selection_messages(
        bot=bot,
        chat_id=callback.from_user.id,
        state=state,
    )
    
    # Удаляем сообщение с инструкцией "Пришлите фото одежды" (если есть)
    garment_instruction_message_id = state_data.get("garment_instruction_message_id")
    if garment_instruction_message_id:
        try:
            await bot.delete_message(
                chat_id=callback.from_user.id,
                message_id=garment_instruction_message_id,
            )
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение с инструкцией: {e}")
    
    # Очищаем состояние
    await state.clear()
    
    # Отправляем главное меню
    await bot.send_message(
        chat_id=callback.from_user.id,
        text=get_text("welcome", lang),
        reply_markup=get_main_menu_keyboard(lang),
    )
    
    await callback.answer()
