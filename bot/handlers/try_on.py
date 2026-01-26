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

        if not models:
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
            
            # Отправляем сообщение об отсутствии моделей
            await bot.send_message(
                chat_id=callback.from_user.id,
                text=(
                    "⚠️ У вас пока нет моделей.\n\n"
                    "Добавьте модель через меню 'Добавить модель'."
                ),
                reply_markup=get_back_keyboard(lang),
            )
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
