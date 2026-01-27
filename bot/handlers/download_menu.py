"""Обработчики для меню скачивания результатов примерки."""

import asyncio
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, BufferedInputFile
from loguru import logger

from bot.services.upscale import UpscaleService
from bot.services.storage import CloudStorageService
from bot.database.repo import FirestoreRepo
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
            "🔄В случае неудовлетворительного результата, попробуйте выбрать другое исходное (Ваше) фото."
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
    storage_service: CloudStorageService,
    repo: FirestoreRepo,
    upscale_service: UpscaleService,
    lang: str = "ru",
) -> None:
    """
    Обработчик кнопки скачивания отдельного фото с апскейлом.

    Args:
        callback: Callback запрос
        state: Контекст FSM
        bot: Экземпляр бота
        storage_service: Сервис для работы с облачным хранилищем
        repo: Репозиторий для работы с БД
        upscale_service: Сервис для апскейла изображений
        lang: Язык интерфейса
    """
    await callback.answer()
    
    try:
        # Определяем номер фото из callback_data
        callback_data = callback.data
        if callback_data == "download_photo_single":
            photo_index = 0
        elif callback_data.startswith("download_photo_"):
            try:
                photo_index = int(callback_data.replace("download_photo_", "")) - 1
            except ValueError:
                logger.error(f"Неверный формат callback_data: {callback_data}")
                await callback.answer(get_text("error_occurred", lang), show_alert=True)
                return
        else:
            logger.error(f"Неизвестный callback_data: {callback_data}")
            await callback.answer(get_text("error_occurred", lang), show_alert=True)
            return
        
        # Получаем сохраненные ID результатов из FSM
        state_data = await state.get_data()
        saved_result_ids = state_data.get("saved_result_ids", [])
        
        if not saved_result_ids:
            logger.warning("Не найдены сохраненные ID результатов")
            await callback.answer("Результаты не найдены", show_alert=True)
            return
        
        if photo_index < 0 or photo_index >= len(saved_result_ids):
            logger.error(f"Неверный индекс фото: {photo_index}, доступно: {len(saved_result_ids)}")
            await callback.answer("Фото не найдено", show_alert=True)
            return
        
        # Получаем ID результата
        result_id = saved_result_ids[photo_index]
        user_id = str(callback.from_user.id)
        
        # Получаем результат из БД
        try:
            result = await repo.get_final_result(user_id, result_id)
            if not result:
                logger.error(f"Результат {result_id} не найден в БД")
                await callback.answer("Результат не найден", show_alert=True)
                return
            
            gcs_uri = result.gcs_uri
        except Exception as e:
            logger.error(f"Ошибка при получении результата из БД: {e}")
            await callback.answer(get_text("error_occurred", lang), show_alert=True)
            return
        
        # Отправляем сообщение ожидания
        waiting_message = await bot.send_message(
            chat_id=callback.from_user.id,
            text=get_text("upscaling", lang),
        )
        waiting_message_id = waiting_message.message_id
        
        try:
            # Скачиваем изображение из облака
            logger.info(f"Скачивание изображения из облака: {gcs_uri}")
            image_bytes = await storage_service.download_file(gcs_uri)
            
            # Отправляем на апскейл
            logger.info(f"Отправка изображения на апскейл (фото {photo_index + 1})")
            upscaled_bytes = await upscale_service.upscale_image(image_bytes)
            
            # Удаляем сообщение ожидания
            try:
                await bot.delete_message(
                    chat_id=callback.from_user.id,
                    message_id=waiting_message_id,
                )
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение ожидания: {e}")
            
            # Отправляем результат как файл
            file = BufferedInputFile(
                file=upscaled_bytes,
                filename=f"try_on_result_hq_{photo_index + 1}.png",
            )
            
            await bot.send_document(
                chat_id=callback.from_user.id,
                document=file,
            )
            
            logger.info(f"Апскейленное изображение отправлено (фото {photo_index + 1})")
            
        except Exception as e:
            logger.error(f"Ошибка при апскейле изображения: {e}", exc_info=True)
            
            # Удаляем сообщение ожидания
            try:
                await bot.delete_message(
                    chat_id=callback.from_user.id,
                    message_id=waiting_message_id,
                )
            except Exception:
                pass
            
            await callback.answer(get_text("upscale_error", lang), show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка в handle_download_photo: {e}", exc_info=True)
        try:
            await callback.answer(get_text("error_occurred", lang), show_alert=True)
        except Exception:
            pass
