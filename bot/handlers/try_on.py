"""Обработчики для примерки одежды."""

import asyncio
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger

from bot.database.repo import FirestoreRepo
from bot.services.storage import CloudStorageService
from bot.services.result_cleanup import cleanup_user_results
from bot.keyboards.user_kb import get_back_keyboard
from bot.handlers.try_on_utils import send_models_album, delete_try_on_selection_messages
from bot.utils.message_utils import delete_messages
from bot.locales.texts import get_text
from bot.services.instruction_photo import show_instruction_photo


async def handle_try_on_callback(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    repo: FirestoreRepo,
    storage_service: CloudStorageService,
    lang: str = "ru",
) -> None:
    """
    Обработчик кнопки "Примерка" из главного меню.
    Показывает все модели с кнопками выбора.

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

    try:
        # Сохраняем старые ID ДО любых изменений state
        state_data = await state.get_data()
        old_album_ids = state_data.get("album_message_ids", [])
        old_selection_id = state_data.get("selection_message_id")
        
        # Получаем все модели пользователя
        models = await repo.get_user_models(user_id)
        
        if not models:
            # Если нет моделей - просим прислать фото
            from bot.states.user_states import TryOnStates
            
            await show_instruction_photo(bot, state, callback.from_user.id, lang)

            # СНАЧАЛА показываем новое сообщение
            instruction_message = await bot.send_message(
                chat_id=callback.from_user.id,
                text=get_text("try_on_send_photo", lang),
                reply_markup=get_back_keyboard(lang),
                parse_mode="HTML",
            )
            
            # Сохраняем ID сообщения с инструкцией для последующего удаления
            await state.update_data(
                selection_message_id=instruction_message.message_id,
                album_message_ids=[],
            )
            
            # Устанавливаем состояние ожидания фото модели
            await state.set_state(TryOnStates.waiting_for_model_photo)
            
            # ПОТОМ удаляем старые по СОХРАНЁННЫМ ID
            old_ids_to_delete = list(old_album_ids)
            if old_selection_id:
                old_ids_to_delete.append(old_selection_id)
            await delete_messages(bot, callback.from_user.id, old_ids_to_delete)
            try:
                await callback.message.delete()
            except Exception:
                pass
            
            return

        # Отправляем альбом с моделями (внутри уже оптимизировано)
        success = await send_models_album(
            callback=callback,
            state=state,
            bot=bot,
            models=models,
            storage_service=storage_service,
            lang=lang,
        )

        if not success:
            logger.error("Ошибка при отправке альбома моделей")

    except Exception as e:
        logger.error(f"Ошибка в handle_try_on_callback: {e}")
        # Удаляем все предыдущие сообщения выбора модели (если есть)
        await delete_try_on_selection_messages(
            bot=bot,
            chat_id=callback.from_user.id,
            state=state,
        )
        # Удаляем исходное сообщение
        try:
            await callback.message.delete()
        except Exception:
            pass
        # Отправляем сообщение об ошибке
        await bot.send_message(
            chat_id=callback.from_user.id,
            text=get_text("try_on_error_general", lang),
            reply_markup=get_back_keyboard(lang),
        )


async def handle_new_try_on_callback(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    repo: FirestoreRepo,
    storage_service: CloudStorageService,
    lang: str = "ru",
) -> None:
    """
    Обработчик кнопки "Новая примерка" из результата примерки.
    Удаляет сообщение с результатом и показывает экран выбора модели.

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

    try:
        # Получаем данные из FSM и сохраняем старые ID ДО любых изменений
        state_data = await state.get_data()
        result_album_message_ids = state_data.get("try_on_result_album_message_ids", [])
        old_album_ids = state_data.get("album_message_ids", [])
        old_selection_id = state_data.get("selection_message_id")
        result_message_id = state_data.get("try_on_result_message_id")
        
        # Получаем все модели пользователя
        models = await repo.get_user_models(user_id)
        
        if not models:
            # Если нет моделей - просим прислать фото
            from bot.states.user_states import TryOnStates
            
            await show_instruction_photo(bot, state, callback.from_user.id, lang)

            # СНАЧАЛА показываем новое сообщение
            instruction_message = await bot.send_message(
                chat_id=callback.from_user.id,
                text=get_text("try_on_send_photo", lang),
                reply_markup=get_back_keyboard(lang),
                parse_mode="HTML",
            )
            
            # Сохраняем ID сообщения с инструкцией для последующего удаления
            await state.update_data(
                selection_message_id=instruction_message.message_id,
                album_message_ids=[],
                try_on_result_album_message_ids=result_album_message_ids,
            )
            
            # Устанавливаем состояние ожидания фото модели
            await state.set_state(TryOnStates.waiting_for_model_photo)
            
            # ПОТОМ удаляем старые по СОХРАНЁННЫМ ID
            if result_message_id:
                try:
                    await bot.delete_message(chat_id=callback.from_user.id, message_id=result_message_id)
                except Exception as e:
                    logger.warning(f"Не удалось удалить сообщение с кнопками: {e}")
            
            old_ids_to_delete = list(old_album_ids)
            if old_selection_id:
                old_ids_to_delete.append(old_selection_id)
            await delete_messages(bot, callback.from_user.id, old_ids_to_delete)
            
            # Фотографии результатов НЕ удаляем из чата - они остаются для пользователя
            
            try:
                await callback.message.delete()
            except Exception:
                pass
            
            # Запускаем очистку результатов из облака в фоне (файлы из GCS и Firestore)
            asyncio.create_task(cleanup_user_results(user_id, repo, storage_service))
            
            return

        # Удаляем только сообщение с кнопками (фотографии остаются в чате)
        if result_message_id:
            try:
                await bot.delete_message(chat_id=callback.from_user.id, message_id=result_message_id)
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение с кнопками: {e}")
        
        # Фотографии результатов НЕ удаляем из чата - они остаются для пользователя
        
        # Восстанавливаем ID фотографий результата в FSM
        await state.update_data(
            try_on_result_message_id=None,
            try_on_result_album_message_ids=[],
        )
        
        # Отправляем альбом с моделями (внутри уже оптимизировано)
        success = await send_models_album(
            callback=callback,
            state=state,
            bot=bot,
            models=models,
            storage_service=storage_service,
            lang=lang,
        )

        if not success:
            logger.error("Ошибка при отправке альбома моделей")
        
        # Запускаем очистку результатов в фоне (после открытия нового меню)
        asyncio.create_task(cleanup_user_results(user_id, repo, storage_service))

    except Exception as e:
        logger.error(f"Ошибка в handle_new_try_on_callback: {e}")
