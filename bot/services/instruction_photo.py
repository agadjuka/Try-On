"""Временный сервис для показа инструкции фото по Telegram file_id."""

from typing import Optional

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from loguru import logger

# Временный file_id инструкции (можно быстро заменить/удалить).
INSTRUCTION_PHOTO_FILE_ID = (
    "AgACAgIAAxkBAAInj2m81D4mjjyW1iDzgiJ2yLLuWvkeAAJ4FmsbN3ngSa3_gyiatC3AAQADAgADeQADOgQ"
)
INSTRUCTION_PHOTO_MESSAGE_ID_KEY = "instruction_photo_message_id"


async def show_instruction_photo(
    bot: Bot,
    state: FSMContext,
    chat_id: int,
) -> Optional[int]:
    """Отправить инструкционное фото и сохранить его message_id в FSM."""
    state_data = await state.get_data()
    old_message_id = state_data.get(INSTRUCTION_PHOTO_MESSAGE_ID_KEY)

    try:
        sent_message = await bot.send_photo(
            chat_id=chat_id,
            photo=INSTRUCTION_PHOTO_FILE_ID,
        )
        new_message_id = sent_message.message_id
        await state.update_data(**{INSTRUCTION_PHOTO_MESSAGE_ID_KEY: new_message_id})

        if old_message_id and old_message_id != new_message_id:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=old_message_id)
            except Exception:
                pass

        return new_message_id
    except Exception as e:
        logger.warning(f"Не удалось отправить инструкционное фото: {e}")
        return None


async def delete_instruction_photo(
    bot: Bot,
    state: FSMContext,
    chat_id: int,
) -> None:
    """Удалить инструкционное фото (если оно есть) и очистить id в FSM."""
    state_data = await state.get_data()
    message_id = state_data.get(INSTRUCTION_PHOTO_MESSAGE_ID_KEY)

    if message_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass

    await state.update_data(**{INSTRUCTION_PHOTO_MESSAGE_ID_KEY: None})
