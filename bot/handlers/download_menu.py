"""Обработчики для меню скачивания результатов примерки."""

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger

from bot.keyboards.user_kb import get_try_on_result_keyboard
from bot.locales.texts import get_text


def _get_result_message_text(photo_count: int, total_count: int, lang: str = "ru") -> str:
    """
    Получить текст сообщения с результатами примерки.
    
    Args:
        photo_count: Количество успешно обработанных фото
        total_count: Общее количество отправленных фото
        lang: Язык интерфейса
        
    Returns:
        Текст сообщения
    """
    if photo_count == 1:
        return get_text("try_on_ready", lang)
    else:
        return (
            f"✅ Готово! Успешно обработано {photo_count} из {total_count} фото.\n"
            "В случае неудовлетворительного результата, попробуйте выбрать другое исходное фото."
        )


async def handle_toggle_download_menu(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    lang: str = "ru",
) -> None:
    """
    Обработчик переключения меню скачивания.
    Открывает/закрывает меню с кнопками для скачивания отдельных фото.

    Args:
        callback: Callback запрос
        state: Контекст FSM
        bot: Экземпляр бота
        lang: Язык интерфейса
    """
    await callback.answer()
    
    try:
        state_data = await state.get_data()
        photo_count = state_data.get("try_on_photo_count", 1)
        total_photo_count = state_data.get("try_on_total_photo_count", photo_count)
        download_menu_open = state_data.get("download_menu_open", False)
        result_message_id = state_data.get("try_on_result_message_id")
        
        if not result_message_id:
            logger.warning("Не найден ID сообщения с результатами")
            return
        
        # Переключаем состояние меню
        new_menu_state = not download_menu_open
        
        # Обновляем состояние в FSM
        await state.update_data(download_menu_open=new_menu_state)
        
        # Получаем текст сообщения
        message_text = _get_result_message_text(photo_count, total_photo_count, lang)
        
        # Обновляем сообщение с новой клавиатурой
        await bot.edit_message_text(
            chat_id=callback.from_user.id,
            message_id=result_message_id,
            text=message_text,
            reply_markup=get_try_on_result_keyboard(
                lang=lang,
                photo_count=photo_count,
                download_menu_open=new_menu_state,
            ),
        )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_toggle_download_menu: {e}", exc_info=True)
        try:
            await callback.answer("Произошла ошибка", show_alert=True)
        except Exception:
            pass


async def handle_download_photo(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    lang: str = "ru",
) -> None:
    """
    Обработчик кнопки скачивания отдельного фото.
    Пока не реализован функционал - просто отвечает на callback.

    Args:
        callback: Callback запрос
        state: Контекст FSM
        bot: Экземпляр бота
        lang: Язык интерфейса
    """
    await callback.answer("Функционал будет реализован позже")
