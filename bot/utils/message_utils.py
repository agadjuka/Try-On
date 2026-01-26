"""Утилиты для работы с сообщениями."""

import asyncio
from typing import List, Optional

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from loguru import logger


async def delete_messages(
    bot: Bot,
    chat_id: int,
    message_ids: List[int],
) -> None:
    """
    Удалить список сообщений параллельно.

    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        message_ids: Список ID сообщений для удаления
    """
    if not message_ids:
        return
    
    delete_tasks = [
        bot.delete_message(chat_id=chat_id, message_id=msg_id)
        for msg_id in message_ids
    ]
    
    await asyncio.gather(*delete_tasks, return_exceptions=True)


async def delete_models_menu_messages(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
) -> None:
    """
    Удалить все сообщения меню моделей (фотографии и сообщение с кнопками).

    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        state: Контекст FSM
    """
    state_data = await state.get_data()
    album_message_ids = state_data.get("models_album_message_ids", [])
    menu_message_id = state_data.get("models_menu_message_id")
    
    message_ids_to_delete = list(album_message_ids)
    if menu_message_id:
        message_ids_to_delete.append(menu_message_id)
    
    await delete_messages(bot, chat_id, message_ids_to_delete)
    
    await state.update_data(
        models_album_message_ids=[],
        models_menu_message_id=None,
    )
