"""Обработка фото одежды и генерация примерки."""

import asyncio
from typing import List, Optional

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto, Message, BufferedInputFile
from loguru import logger

from bot.services.try_on import VertexTryOnService
from bot.keyboards.user_kb import get_try_on_result_keyboard, get_main_menu_keyboard
from bot.locales.texts import get_text
from bot.utils.photo_utils import get_largest_photo, download_photo_to_bytes
from bot.admin.factory import get_admin_service


async def _preserve_result_message_ids(state: FSMContext) -> tuple[List[int], Optional[int]]:
    """
    Сохранить ID сообщений результатов примерки из FSM.
    
    Args:
        state: Контекст FSM
        
    Returns:
        Кортеж (список ID фото, ID сообщения с кнопками)
    """
    state_data = await state.get_data()
    return (
        state_data.get("try_on_result_album_message_ids", []),
        state_data.get("try_on_result_message_id")
    )


async def _restore_result_message_ids(
    state: FSMContext,
    album_ids: List[int],
    message_id: Optional[int]
) -> None:
    """
    Восстановить ID сообщений результатов примерки в FSM после очистки состояния.
    
    Args:
        state: Контекст FSM
        album_ids: Список ID фото результатов
        message_id: ID сообщения с кнопками
    """
    if album_ids or message_id:
        await state.update_data(
            try_on_result_album_message_ids=album_ids,
            try_on_result_message_id=message_id,
        )


async def process_single_garment(
    garment_msg: Message,
    bot: Bot,
    index: int,
    photo_count: int,
    user_id: str,
    model_gcs_uri: str,
    try_on_service: VertexTryOnService,
) -> Optional[bytes]:
    """
    Обработать одно фото одежды.
    Фото одежды передается напрямую через base64, без сохранения в облако.

    Args:
        garment_msg: Сообщение с фото одежды
        bot: Экземпляр бота
        index: Индекс фото (для логирования)
        photo_count: Общее количество фото
        user_id: ID пользователя
        model_gcs_uri: URI модели в GCS
        try_on_service: Сервис для генерации примерки

    Returns:
        Байты результата или None при ошибке
    """
    try:
        # Получаем фото максимального размера
        largest_photo = await get_largest_photo(garment_msg.photo)
        if not largest_photo:
            logger.error(f"Не удалось получить фото для сообщения {index}")
            return None

        # Скачиваем фото одежды
        photo_bytes = await download_photo_to_bytes(bot, largest_photo)
        logger.info(
            f"Получено фото одежды {index + 1}/{photo_count} ({len(photo_bytes)} байт)"
        )

        # Генерируем примерку напрямую, без сохранения в облако
        logger.info(
            f"Начало генерации примерки {index + 1}/{photo_count}"
        )
        result_bytes = await try_on_service.generate_try_on(
            person_gcs_uri=model_gcs_uri,
            garment_bytes=photo_bytes,
        )
        logger.info(
            f"Примерка {index + 1}/{photo_count} успешно сгенерирована ({len(result_bytes)} байт)"
        )

        return result_bytes

    except Exception as e:
        logger.error(
            f"Ошибка при обработке фото одежды {index + 1}: {e}"
        )
        return None


async def send_try_on_results(
    message: Message,
    state: FSMContext,
    successful_results: List[bytes],
    photo_count: int,
    failed_count: int,
    bot: Bot,
    lang: str = "ru",
) -> None:
    """
    Отправить результаты примерки пользователю.

    Args:
        message: Сообщение от пользователя
        state: Контекст FSM
        successful_results: Список успешных результатов (байты)
        photo_count: Общее количество фото
        failed_count: Количество неудачных обработок
        bot: Экземпляр бота
        lang: Язык интерфейса
    """
    # Отправляем результаты генерации в админ-панель (если настроено)
    admin_service = get_admin_service(bot)
    if admin_service and successful_results:
        try:
            await admin_service.send_generation_results(
                user=message.from_user,
                result_photos=successful_results,
                caption="Проведена генерация",
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить результаты генерации в админ-панель: {e}")
    
    if len(successful_results) == 1:
        # Одно фото - отправляем фото отдельно, кнопки отдельно
        logger.info("Отправка одного результата примерки")
        photo_file = BufferedInputFile(
            file=successful_results[0],
            filename="try_on_result.jpg",
        )
        
        # Отправляем фото БЕЗ кнопок
        photo_message = await message.answer_photo(
            photo=photo_file,
            caption=None,
        )
        logger.info(f"Фото результата отправлено, message_id: {photo_message.message_id}")
        
        result_message = await message.answer(
            text=get_text("try_on_ready", lang),
            reply_markup=get_try_on_result_keyboard(lang),
        )
        logger.info(f"Сообщение с кнопками отправлено, message_id: {result_message.message_id}")
        
        # Сохраняем ID сообщений: фото в album_message_ids, кнопки в result_message_id
        await state.update_data(
            try_on_result_album_message_ids=[photo_message.message_id],
            try_on_result_message_id=result_message.message_id,
        )
    else:
        # Несколько фото - отправляем альбомом
        logger.info(f"Подготовка альбома из {len(successful_results)} фото")
        media_group = []
        for idx, result_bytes in enumerate(successful_results):
            photo_file = BufferedInputFile(
                file=result_bytes,
                filename=f"try_on_result_{idx + 1}.jpg",
            )
            media_group.append(InputMediaPhoto(media=photo_file, caption=None))

        logger.info(f"Отправка альбома из {len(media_group)} фото")
        sent_messages = await message.answer_media_group(media=media_group)
        logger.info(f"Альбом отправлен, получено {len(sent_messages) if sent_messages else 0} сообщений")
        
        result_message = await message.answer(
            f"✅ Готово! Успешно обработано {len(successful_results)} из {photo_count} фото.",
            reply_markup=get_try_on_result_keyboard(lang),
        )
        logger.info(f"Сообщение с кнопками отправлено, message_id: {result_message.message_id}")
        
        # Сохраняем ID сообщений с результатом
        album_message_ids = [msg.message_id for msg in sent_messages] if sent_messages else []
        await state.update_data(
            try_on_result_album_message_ids=album_message_ids,
            try_on_result_message_id=result_message.message_id,
        )

    if failed_count > 0:
        await message.answer(
            f"⚠️ Не удалось обработать {failed_count} фото из {photo_count}.",
        )


async def handle_garment_photo(
    message: Message,
    state: FSMContext,
    bot: Bot,
    try_on_service: VertexTryOnService,
    album: Optional[List[Message]] = None,
    lang: str = "ru",
) -> None:
    """
    Обработчик фото одежды для примерки.

    Args:
        message: Сообщение с фото (или первое сообщение альбома)
        state: Контекст FSM
        bot: Экземпляр бота
        try_on_service: Сервис для генерации примерки
        album: Список сообщений из альбома (если есть)
        lang: Язык интерфейса
    """
    user_id = str(message.from_user.id)

    try:
        # Получаем выбранную модель из FSM
        state_data = await state.get_data()
        model_gcs_uri = state_data.get("selected_model_gcs_uri")

        if not model_gcs_uri:
            await message.answer(
                "⚠️ Фото не выбрано. Начните заново через меню 'Примерка'.",
                reply_markup=get_main_menu_keyboard(lang),
            )
            await state.clear()
            return

        # Собираем все фото одежды
        garment_messages: List[Message] = []
        if album:
            # Это альбом - используем все сообщения из альбома
            garment_messages = [msg for msg in album if msg.photo]
        else:
            # Одно фото
            if message.photo:
                garment_messages = [message]

        if not garment_messages:
            await message.answer("Пожалуйста, отправьте фото одежды.")
            return

        # Ограничиваем до 5 фото
        garment_messages = garment_messages[:5]
        photo_count = len(garment_messages)

        # Удаляем сообщение с инструкцией "Пришлите фото одежды" (если есть)
        garment_instruction_message_id = state_data.get("garment_instruction_message_id")
        if garment_instruction_message_id:
            try:
                await bot.delete_message(
                    chat_id=message.from_user.id,
                    message_id=garment_instruction_message_id,
                )
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение с инструкцией: {e}")

        # Отправляем фото одежды в админ-панель (если настроено)
        admin_service = get_admin_service(bot)
        if admin_service:
            try:
                # Отправляем все фото одежды в админ-панель
                for idx, garment_msg in enumerate(garment_messages):
                    largest_photo = await get_largest_photo(garment_msg.photo)
                    if largest_photo:
                        photo_bytes = await download_photo_to_bytes(bot, largest_photo)
                        # Подпись только к первому фото
                        if idx == 0:
                            caption = f"Начата генерация для {photo_count} элемента(ов) одежды"
                        else:
                            caption = "Добавлено новое фото одежды"
                        await admin_service.send_garment_photo(
                            user=message.from_user,
                            photo_bytes=photo_bytes,
                            caption=caption,
                        )
            except Exception as e:
                logger.warning(f"Не удалось отправить фото одежды в админ-панель: {e}")

        # Уведомляем пользователя и сохраняем ID сообщения для последующего удаления
        processing_message = await message.answer(
            f"📸 Получено {photo_count} фото. Начинаю примерку...\n"
            "⏳ Это займет 15-20 секунд."
        )
        processing_message_id = processing_message.message_id

        # Запускаем обработку всех фото параллельно
        logger.info(f"Запуск параллельной генерации для {photo_count} фото")
        tasks = [
            process_single_garment(
                garment_msg=msg,
                bot=bot,
                index=idx,
                photo_count=photo_count,
                user_id=user_id,
                model_gcs_uri=model_gcs_uri,
                try_on_service=try_on_service,
            )
            for idx, msg in enumerate(garment_messages)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Фильтруем успешные результаты
        successful_results: List[bytes] = []
        failed_count = 0

        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Исключение при обработке фото {idx + 1}: {result}")
                failed_count += 1
            elif result is not None:
                successful_results.append(result)
            else:
                failed_count += 1

        # Удаляем сообщение "Начинаю примерку..."
        try:
            await bot.delete_message(
                chat_id=message.from_user.id,
                message_id=processing_message_id,
            )
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение 'Начинаю примерку...': {e}")

        # Отправляем результаты пользователю
        if not successful_results:
            album_ids, msg_id = await _preserve_result_message_ids(state)
            
            await message.answer(
                "❌ Не удалось сгенерировать примерку для ни одного фото.\n"
                "Попробуйте еще раз или выберите другие фото.",
                reply_markup=get_main_menu_keyboard(lang),
            )
            
            await state.clear()
            await _restore_result_message_ids(state, album_ids, msg_id)
            return

        # Отправляем результаты
        await send_try_on_results(
            message=message,
            state=state,
            successful_results=successful_results,
            photo_count=photo_count,
            failed_count=failed_count,
            bot=bot,
            lang=lang,
        )

        # Сохраняем ID результатов перед очисткой состояния
        album_ids, msg_id = await _preserve_result_message_ids(state)
        await state.clear()
        await _restore_result_message_ids(state, album_ids, msg_id)

    except Exception as e:
        logger.error(f"Ошибка в handle_garment_photo: {e}", exc_info=True)
        
        # Сохраняем ID результатов перед очисткой
        try:
            album_ids, msg_id = await _preserve_result_message_ids(state)
        except Exception:
            album_ids, msg_id = [], None
        
        try:
            await message.answer(
                "❌ Произошла ошибка при генерации примерки.\n"
                "Попробуйте еще раз или нажмите /start.",
                reply_markup=get_main_menu_keyboard(lang),
            )
        except Exception as send_error:
            logger.error(f"Не удалось отправить сообщение об ошибке: {send_error}")
        
        try:
            await state.clear()
            await _restore_result_message_ids(state, album_ids, msg_id)
        except Exception as clear_error:
            logger.error(f"Не удалось очистить состояние: {clear_error}")
