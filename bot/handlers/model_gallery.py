"""Обработчики галереи моделей."""

from aiogram import Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InputMediaPhoto
from loguru import logger

from bot.database.repo import FirestoreRepo
from bot.services.storage import CloudStorageService
from bot.keyboards.user_kb import get_gallery_keyboard, get_back_keyboard
from bot.locales.texts import get_text


async def show_model_in_gallery(
    message: Message,
    bot: Bot,
    models: list,
    current_index: int,
    storage_service: CloudStorageService,
    lang: str = "ru",
) -> None:
    """
    Показать модель в галерее.

    Args:
        message: Сообщение для редактирования
        bot: Экземпляр бота
        models: Список моделей
        current_index: Индекс текущей модели
        storage_service: Сервис для работы с GCS
        lang: Язык интерфейса
    """
    if not models or current_index < 0 or current_index >= len(models):
        return
    
    model = models[current_index]
    
    try:
        photo_bytes = await storage_service.download_file(model.gcs_uri)
        
        photo_file = BufferedInputFile(
            file=photo_bytes,
            filename="model.png"
        )
        
        media = InputMediaPhoto(
            media=photo_file,
            caption=f"Фото {current_index + 1} из {len(models)}",
        )
        
        keyboard = get_gallery_keyboard(
            current_index=current_index,
            total_count=len(models),
            model_id=model.id,
            lang=lang,
        )
        
        await message.edit_media(media=media, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка при показе модели: {e}")
        await message.edit_text(
            get_text("model_gallery_error", lang),
            reply_markup=get_back_keyboard(lang),
        )


async def handle_model_navigation(
    callback: CallbackQuery,
    bot: Bot,
    repo: FirestoreRepo,
    storage_service: CloudStorageService,
    lang: str = "ru",
) -> None:
    """
    Обработчик навигации по галерее моделей.

    Args:
        callback: Callback запрос
        bot: Экземпляр бота
        repo: Репозиторий для работы с БД
        storage_service: Сервис для работы с GCS
        lang: Язык интерфейса
    """
    # Мгновенно отвечаем на callback - убирает "часики" на кнопке
    await callback.answer()
    
    user_id = str(callback.from_user.id)
    callback_data = callback.data
    
    try:
        models = await repo.get_user_models(user_id)
        
        if not models:
            return
        
        if callback_data.startswith("model_prev_"):
            current_index = int(callback_data.replace("model_prev_", "")) - 1
        elif callback_data.startswith("model_next_"):
            current_index = int(callback_data.replace("model_next_", "")) + 1
        else:
            return
        
        if current_index < 0 or current_index >= len(models):
            return
        
        await show_model_in_gallery(
            message=callback.message,
            bot=bot,
            models=models,
            current_index=current_index,
            storage_service=storage_service,
            lang=lang,
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении моделей: {e}")
