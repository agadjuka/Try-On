"""Обработчики для примерки одежды."""

import asyncio
from datetime import datetime
from typing import List, Optional

from aiogram import Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message, BufferedInputFile
from loguru import logger

from bot.database.repo import FirestoreRepo
from bot.services.storage import CloudStorageService
from bot.services.try_on import VertexTryOnService
from bot.states.user_states import TryOnStates
from bot.keyboards.user_kb import (
    get_main_menu_keyboard,
    get_back_keyboard,
    get_model_selection_keyboard,
)
from bot.locales.texts import get_text
from bot.handlers.models import get_largest_photo, download_photo_to_bytes


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
            await callback.message.edit_text(
                "⚠️ У вас пока нет моделей.\n\n"
                "Добавьте модель через меню 'Добавить модель'.",
                reply_markup=get_back_keyboard(lang),
            )
            await callback.answer()
            return

        # Отправляем все фото моделей альбомом
        from aiogram.types import InputMediaPhoto, BufferedInputFile

        media_group = []
        for idx, model in enumerate(models):
            try:
                # Скачиваем фото из GCS
                photo_bytes = await storage_service.download_file(model.gcs_uri)
                photo_file = BufferedInputFile(
                    file=photo_bytes,
                    filename=f"model_{idx + 1}.jpg",
                )
                # Для последнего фото добавим caption и кнопки после отправки
                caption = None
                media_group.append(InputMediaPhoto(media=photo_file, caption=caption))
            except Exception as e:
                logger.error(f"Ошибка при загрузке фото модели {idx + 1}: {e}")

        if not media_group:
            await callback.message.edit_text(
                "❌ Не удалось загрузить фото моделей.",
                reply_markup=get_back_keyboard(lang),
            )
            await callback.answer()
            return

        # Удаляем исходное сообщение с кнопкой "Примерка"
        await callback.message.delete()

        # Отправляем альбом с фото моделей (сначала фотографии)
        sent_messages = await bot.send_media_group(
            chat_id=callback.from_user.id,
            media=media_group,
        )

        # Сохраняем ID сообщений альбома в FSM для последующего удаления
        album_message_ids = [msg.message_id for msg in sent_messages] if sent_messages else []
        await state.update_data(album_message_ids=album_message_ids)

        # Отправляем сообщение с кнопками (после фотографий)
        selection_message = await bot.send_message(
            chat_id=callback.from_user.id,
            text="👤 Выберите модель для примерки:",
            reply_markup=get_model_selection_keyboard(models, lang),
        )

        # Сохраняем ID сообщения с кнопками для последующего редактирования
        await state.update_data(selection_message_id=selection_message.message_id)

        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка в handle_try_on_callback: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_back_keyboard(lang),
        )
        await callback.answer()


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
    # Формат: "try_on_select_model_{model_id}"
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
        if selection_message_id:
            try:
                await bot.edit_message_text(
                    chat_id=callback.from_user.id,
                    message_id=selection_message_id,
                    text="📸 Пришлите фото одежды (до 5 штук).\n\n"
                    "Можно отправить одно фото или несколько фото одним альбомом.",
                    reply_markup=get_back_keyboard(lang),
                )
            except Exception as e:
                logger.error(f"Ошибка при редактировании сообщения: {e}")
                # Если не удалось отредактировать, отправляем новое
                await bot.send_message(
                    chat_id=callback.from_user.id,
                    text="📸 Пришлите фото одежды (до 5 штук).\n\n"
                    "Можно отправить одно фото или несколько фото одним альбомом.",
                    reply_markup=get_back_keyboard(lang),
                )
        else:
            # Если ID сообщения не найден, отправляем новое
            await bot.send_message(
                chat_id=callback.from_user.id,
                text="📸 Пришлите фото одежды (до 5 штук).\n\n"
                "Можно отправить одно фото или несколько фото одним альбомом.",
                reply_markup=get_back_keyboard(lang),
            )

        await callback.answer("Модель выбрана")

    except Exception as e:
        logger.error(f"Ошибка в handle_model_selection_for_try_on: {e}")
        await callback.answer("Произошла ошибка")


async def handle_garment_photo(
    message: Message,
    state: FSMContext,
    bot: Bot,
    repo: FirestoreRepo,
    storage_service: CloudStorageService,
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
        repo: Репозиторий для работы с БД
        storage_service: Сервис для работы с GCS
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
                "⚠️ Модель не выбрана. Начните заново через меню 'Примерка'.",
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

        # Уведомляем пользователя
        await message.answer(
            f"📸 Получено {photo_count} фото. Начинаю примерку...\n"
            "⏳ Это займет 15-20 секунд."
        )

        # Функция для обработки одного фото одежды
        async def process_single_garment(
            garment_msg: Message, index: int
        ) -> Optional[bytes]:
            """
            Обработать одно фото одежды.

            Args:
                garment_msg: Сообщение с фото одежды
                index: Индекс фото (для логирования)

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

                # Генерируем уникальный путь в GCS
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                destination_path = (
                    f"bot_uploads/garments/{user_id}_{timestamp}_{index}.jpg"
                )

                # Загружаем фото одежды в Cloud Storage
                logger.info(
                    f"Загрузка фото одежды {index + 1}/{photo_count} в GCS: {destination_path}"
                )
                garment_gcs_uri = await storage_service.upload_image(
                    file_bytes=photo_bytes,
                    destination_path=destination_path,
                )

                # Генерируем примерку
                logger.info(
                    f"Начало генерации примерки {index + 1}/{photo_count} "
                    f"(garment: {garment_gcs_uri})"
                )
                result_gcs_uri = await try_on_service.generate_try_on(
                    person_gcs_uri=model_gcs_uri,
                    garment_gcs_uri=garment_gcs_uri,
                    storage_service=storage_service,
                )

                # Скачиваем результат из GCS
                result_bytes = await storage_service.download_file(result_gcs_uri)
                logger.info(
                    f"Примерка {index + 1}/{photo_count} успешно сгенерирована"
                )

                return result_bytes

            except Exception as e:
                logger.error(
                    f"Ошибка при обработке фото одежды {index + 1}: {e}"
                )
                return None

        # Запускаем обработку всех фото параллельно
        logger.info(f"Запуск параллельной генерации для {photo_count} фото")
        tasks = [
            process_single_garment(msg, idx)
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

        # Отправляем результаты пользователю
        if not successful_results:
            await message.answer(
                "❌ Не удалось сгенерировать примерку для ни одного фото.\n"
                "Попробуйте еще раз или выберите другие фото.",
                reply_markup=get_main_menu_keyboard(lang),
            )
            await state.clear()
            return

        # Отправляем результаты
        if len(successful_results) == 1:
            # Одно фото - отправляем как обычное фото
            photo_file = BufferedInputFile(
                file=successful_results[0],
                filename="try_on_result.jpg",
            )
            await message.answer_photo(
                photo=photo_file,
                caption="✅ Примерка готова!",
                reply_markup=get_main_menu_keyboard(lang),
            )
        else:
            # Несколько фото - отправляем альбомом
            media_group = []
            for idx, result_bytes in enumerate(successful_results):
                photo_file = BufferedInputFile(
                    file=result_bytes,
                    filename=f"try_on_result_{idx + 1}.jpg",
                )
                caption = (
                    f"✅ Примерка {idx + 1}/{len(successful_results)}"
                    if idx == len(successful_results) - 1
                    else None
                )
                media_group.append(InputMediaPhoto(media=photo_file, caption=caption))

            await message.answer_media_group(media=media_group)
            await message.answer(
                f"✅ Готово! Успешно обработано {len(successful_results)} из {photo_count} фото.",
                reply_markup=get_main_menu_keyboard(lang),
            )

        if failed_count > 0:
            await message.answer(
                f"⚠️ Не удалось обработать {failed_count} фото из {photo_count}.",
            )

        # Сбрасываем состояние
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка в handle_garment_photo: {e}")
        await message.answer(
            "❌ Произошла ошибка при генерации примерки.\n"
            "Попробуйте еще раз или нажмите /start.",
            reply_markup=get_main_menu_keyboard(lang),
        )
        await state.clear()
