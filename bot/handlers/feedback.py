"""Обработчики отправки отзыва."""

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger

from bot.admin.factory import get_admin_service
from bot.keyboards.user_kb import (
    get_feedback_keyboard,
    get_main_menu_keyboard,
    get_try_on_result_keyboard,
)
from bot.locales.texts import get_text
from bot.states.user_states import FeedbackStates
from bot.utils.message_utils import delete_messages


async def open_feedback_menu(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    lang: str = "ru",
) -> None:
    """Открыть меню отправки отзыва."""
    await callback.answer()

    state_data = await state.get_data()
    return_to = "result" if state_data.get("try_on_result_message_id") else "main"

    prompt_message = await bot.send_message(
        chat_id=callback.from_user.id,
        text=get_text("feedback_prompt", lang),
        reply_markup=get_feedback_keyboard(lang),
        disable_web_page_preview=True,
    )

    await state.set_state(FeedbackStates.waiting_for_feedback)
    await state.update_data(
        feedback_return_to=return_to,
        feedback_prompt_message_id=prompt_message.message_id,
    )

    try:
        await callback.message.delete()
    except Exception:
        pass


async def cancel_feedback(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    lang: str = "ru",
) -> None:
    """Отменить отправку отзыва и вернуть пользователя назад."""
    await callback.answer()
    state_data = await state.get_data()
    await _return_to_previous_menu(
        bot=bot,
        user_id=callback.from_user.id,
        state=state,
        lang=lang,
        with_thanks=False,
    )

    ids_to_delete = [state_data.get("feedback_prompt_message_id"), callback.message.message_id]
    await delete_messages(bot, callback.from_user.id, [msg_id for msg_id in ids_to_delete if msg_id])


async def handle_feedback_message(
    message: Message,
    state: FSMContext,
    bot: Bot,
    lang: str = "ru",
) -> None:
    """Принять отзыв (текст и/или фото) и отправить в админ-топик клиента."""
    has_text = bool(message.text and message.text.strip())
    has_photo = bool(message.photo)

    if not (has_text or has_photo):
        await message.answer(get_text("feedback_unsupported", lang), reply_markup=get_feedback_keyboard(lang))
        return

    try:
        admin_service = get_admin_service(bot)
        if admin_service:
            topic_id = await admin_service.get_or_create_topic(message.from_user)
            await bot.send_message(
                chat_id=admin_service.admin_group_id,
                message_thread_id=topic_id,
                text=get_text("admin_feedback_label", lang),
            )
            await bot.copy_message(
                chat_id=admin_service.admin_group_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                message_thread_id=topic_id,
            )
    except Exception as e:
        logger.error(f"Ошибка отправки отзыва в админ-панель: {e}")

    await _return_to_previous_menu(
        bot=bot,
        user_id=message.from_user.id,
        state=state,
        lang=lang,
        with_thanks=True,
    )


async def _return_to_previous_menu(
    bot: Bot,
    user_id: int,
    state: FSMContext,
    lang: str,
    with_thanks: bool,
) -> None:
    state_data = await state.get_data()
    return_to = state_data.get("feedback_return_to", "main")
    prompt_id = state_data.get("feedback_prompt_message_id")

    if return_to == "result":
        photo_count = state_data.get("try_on_photo_count", 1)
        total_photo_count = state_data.get("try_on_total_photo_count", photo_count)
        download_menu_open = state_data.get("download_menu_open", False)
        text = (
            get_text("feedback_sent", lang) + "\n\n" + get_text("try_on_ready", lang)
            if with_thanks and photo_count == 1
            else (
                get_text("feedback_sent", lang) + "\n\n" + get_text("try_on_results_multiple", lang).format(
                    success=photo_count, total=total_photo_count
                )
                if with_thanks
                else (
                    get_text("try_on_ready", lang)
                    if photo_count == 1
                    else get_text("try_on_results_multiple", lang).format(success=photo_count, total=total_photo_count)
                )
            )
        )
        result_message = await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=get_try_on_result_keyboard(
                lang=lang,
                photo_count=photo_count,
                download_menu_open=download_menu_open,
            ),
        )
        await state.update_data(try_on_result_message_id=result_message.message_id)
    else:
        text = get_text("feedback_sent", lang) + "\n\n" + get_text("welcome", lang) if with_thanks else get_text("welcome", lang)
        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode="HTML",
        )

    await state.set_state(None)
    await state.update_data(
        feedback_return_to=None,
        feedback_prompt_message_id=None,
    )

    if prompt_id:
        await delete_messages(bot, user_id, [prompt_id])
