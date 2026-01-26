"""Обработчики для примерки одежды."""

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger

from bot.database.repo import FirestoreRepo
from bot.services.storage import CloudStorageService
from bot.keyboards.user_kb import get_back_keyboard
from bot.handlers.try_on_utils import send_models_album, delete_try_on_selection_messages


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
    user_id = str(callback.from_user.id)

    try:
        # Получаем все модели пользователя
        models = await repo.get_user_models(user_id)

        # Удаляем все предыдущие сообщения выбора модели (если есть)
        await delete_try_on_selection_messages(
            bot=bot,
            chat_id=callback.from_user.id,
            state=state,
        )
        
        # Удаляем исходное сообщение из главного меню
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        if not models:
            # Если нет моделей - просим прислать фото
            from bot.locales.texts import get_text
            instruction_message = await bot.send_message(
                chat_id=callback.from_user.id,
                text=get_text("try_on_send_photo", lang),
                reply_markup=get_back_keyboard(lang),
            )
            
            # Сохраняем ID сообщения с инструкцией для последующего удаления
            await state.update_data(
                selection_message_id=instruction_message.message_id,
                album_message_ids=[],
            )
            
            # Устанавливаем состояние ожидания фото модели
            from bot.states.user_states import TryOnStates
            await state.set_state(TryOnStates.waiting_for_model_photo)
            
            await callback.answer()
            return

        # Отправляем альбом с моделями
        success = await send_models_album(
            callback=callback,
            state=state,
            bot=bot,
            models=models,
            storage_service=storage_service,
            lang=lang,
        )

        if success:
            await callback.answer()
        else:
            await callback.answer("Произошла ошибка")

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
            text="❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_back_keyboard(lang),
        )
        await callback.answer()


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
    user_id = str(callback.from_user.id)

    try:
        # Получаем данные из FSM
        state_data = await state.get_data()
        
        # Сохраняем ID фотографий результата, чтобы они не удалились
        result_album_message_ids = state_data.get("try_on_result_album_message_ids", [])
        logger.info(f"Сохраняем ID фотографий результата перед обработкой: {result_album_message_ids}")
        
        # Удаляем только сообщение с кнопками (фотографии результата остаются в чате)
        result_message_id = state_data.get("try_on_result_message_id")
        
        if result_message_id:
            try:
                await bot.delete_message(
                    chat_id=callback.from_user.id,
                    message_id=result_message_id,
                )
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение с кнопками: {e}")
        
        # Удаляем все предыдущие сообщения выбора модели (если есть)
        # Важно: это удаляет только album_message_ids (фотографии моделей), не try_on_result_album_message_ids
        await delete_try_on_selection_messages(
            bot=bot,
            chat_id=callback.from_user.id,
            state=state,
        )
        
        # Получаем все модели пользователя
        models = await repo.get_user_models(user_id)

        # Удаляем сообщение с кнопками
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        # Восстанавливаем ID фотографий результата в FSM (чтобы они не удалились)
        # Очищаем только ID сообщения с кнопками
        await state.update_data(
            try_on_result_message_id=None,
            try_on_result_album_message_ids=result_album_message_ids,  # Восстанавливаем
        )
        logger.info(f"Восстановили ID фотографий результата в FSM после удаления сообщений: {result_album_message_ids}")
        
        if not models:
            # Если нет моделей - просим прислать фото
            from bot.locales.texts import get_text
            from bot.states.user_states import TryOnStates
            
            instruction_message = await bot.send_message(
                chat_id=callback.from_user.id,
                text=get_text("try_on_send_photo", lang),
                reply_markup=get_back_keyboard(lang),
            )
            
            # Сохраняем ID сообщения с инструкцией для последующего удаления
            # Сохраняем существующие try_on_result_album_message_ids, чтобы не удалить фотографии результата
            await state.update_data(
                selection_message_id=instruction_message.message_id,
                album_message_ids=[],
                try_on_result_album_message_ids=result_album_message_ids,  # Сохраняем фотографии результата
            )
            
            # Устанавливаем состояние ожидания фото модели
            await state.set_state(TryOnStates.waiting_for_model_photo)
            
            await callback.answer()
            return

        # Отправляем альбом с моделями (send_models_album удалит callback.message сам)
        success = await send_models_album(
            callback=callback,
            state=state,
            bot=bot,
            models=models,
            storage_service=storage_service,
            lang=lang,
        )

        if success:
            await callback.answer()
        else:
            await callback.answer("Произошла ошибка")

    except Exception as e:
        logger.error(f"Ошибка в handle_try_on_callback: {e}")
        await callback.answer("Произошла ошибка")
