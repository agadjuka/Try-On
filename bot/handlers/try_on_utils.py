"""Вспомогательные функции для примерки."""

import asyncio
from typing import List

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, BufferedInputFile
from loguru import logger

from bot.services.storage import CloudStorageService
from bot.keyboards.user_kb import get_back_keyboard, get_model_selection_keyboard


async def delete_try_on_selection_messages(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
) -> None:
    """
    Удалить все сообщения выбора модели для примерки (фотографии и сообщение с кнопками).
    Удаление происходит параллельно.

    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        state: Контекст FSM
    """
    state_data = await state.get_data()
    album_message_ids = state_data.get("album_message_ids", [])
    selection_message_id = state_data.get("selection_message_id")
    
    # Собираем все ID сообщений для удаления
    message_ids_to_delete = list(album_message_ids)
    if selection_message_id:
        message_ids_to_delete.append(selection_message_id)
    
    if not message_ids_to_delete:
        return
    
    # Удаляем все сообщения параллельно
    delete_tasks = []
    for msg_id in message_ids_to_delete:
        delete_tasks.append(
            bot.delete_message(chat_id=chat_id, message_id=msg_id)
        )
    
    # Выполняем удаление параллельно, игнорируем ошибки
    results = await asyncio.gather(*delete_tasks, return_exceptions=True)
    
    # Логируем ошибки, если есть
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"Не удалось удалить сообщение {message_ids_to_delete[idx]}: {result}")
    
    # Очищаем данные из FSM
    await state.update_data(
        album_message_ids=[],
        selection_message_id=None,
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
        media_group = []
        for idx, model in enumerate(models):
            try:
                # Скачиваем фото из GCS
                photo_bytes = await storage_service.download_file(model.gcs_uri)
                photo_file = BufferedInputFile(
                    file=photo_bytes,
                    filename=f"model_{idx + 1}.jpg",
                )
                media_group.append(InputMediaPhoto(media=photo_file, caption=None))
            except Exception as e:
                logger.error(f"Ошибка при загрузке фото модели {idx + 1}: {e}")

        if not media_group:
            await callback.message.edit_text(
                "❌ Не удалось загрузить фото моделей.",
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

        # Отправляем альбом с фото моделей
        sent_messages = await bot.send_media_group(
            chat_id=callback.from_user.id,
            media=media_group,
        )

        # Сохраняем ID сообщений альбома в FSM для последующего удаления
        album_message_ids = [msg.message_id for msg in sent_messages] if sent_messages else []
        await state.update_data(album_message_ids=album_message_ids)

        # Отправляем сообщение с кнопками (после фотографий)
        selection_message = await bot.send_message(
            chat_id=callback.from_user.id,
            text="👤 Выберите модель для примерки:",
            reply_markup=get_model_selection_keyboard(models, lang),
        )

        # Сохраняем ID сообщения с кнопками для последующего удаления
        await state.update_data(selection_message_id=selection_message.message_id)

        return True

    except Exception as e:
        logger.error(f"Ошибка при отправке альбома моделей: {e}")
        return False
