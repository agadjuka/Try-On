"""Обработчики выбора модели для примерки."""

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger

from bot.database.repo import FirestoreRepo
from bot.states.user_states import TryOnStates
from bot.keyboards.user_kb import get_back_keyboard


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
            await callback.answer("Модель не найдена")
            return

        # Получаем данные из FSM
        state_data = await state.get_data()
        album_message_ids = state_data.get("album_message_ids", [])
        selection_message_id = state_data.get("selection_message_id")

        # Удаляем альбом с фотографиями моделей
        for msg_id in album_message_ids:
            try:
                await bot.delete_message(
                    chat_id=callback.from_user.id,
                    message_id=msg_id,
                )
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение {msg_id}: {e}")

        # Сохраняем выбранную модель в FSM
        await state.update_data(selected_model_gcs_uri=selected_model.gcs_uri)
        await state.set_state(TryOnStates.waiting_for_garment_photo)

        # Редактируем сообщение с кнопками, заменяя его на инструкцию
        instruction_text = (
            "📸 Пришлите фото одежды (до 5 штук).\n\n"
            "Можно отправить одно фото или несколько фото одним альбомом."
        )

        if selection_message_id:
            try:
                await bot.edit_message_text(
                    chat_id=callback.from_user.id,
                    message_id=selection_message_id,
                    text=instruction_text,
                    reply_markup=get_back_keyboard(lang),
                )
            except Exception as e:
                logger.error(f"Ошибка при редактировании сообщения: {e}")
                # Если не удалось отредактировать, отправляем новое
                await bot.send_message(
                    chat_id=callback.from_user.id,
                    text=instruction_text,
                    reply_markup=get_back_keyboard(lang),
                )
        else:
            # Если ID сообщения не найден, отправляем новое
            await bot.send_message(
                chat_id=callback.from_user.id,
                text=instruction_text,
                reply_markup=get_back_keyboard(lang),
            )

        await callback.answer("Модель выбрана")

    except Exception as e:
        logger.error(f"Ошибка в handle_model_selection_for_try_on: {e}")
        await callback.answer("Произошла ошибка")
