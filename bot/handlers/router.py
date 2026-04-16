"""Роутер для регистрации всех хендлеров."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.filters.state import StateFilter

from bot.database.repo_factory import UserRepository
from bot.services.storage import CloudStorageService
from bot.services.try_on import VertexTryOnService
from bot.services.upscale import UpscaleService
from bot.states.user_states import ModelStates, TryOnStates, FeedbackStates
from bot.handlers import (
    start,
    model_upload,
    model_list,
    model_gallery,
    navigation,
    try_on,
    try_on_selection,
    try_on_processing,
    download_menu,
    language,
    privacy,
    debug_photo_file_id,
    feedback,
)
from bot.middlewares.album import AlbumMiddleware
from bot.middlewares.privacy_consent import PrivacyConsentMiddleware
from bot.services.language import get_user_language


def setup_handlers(
    router: Router,
    bot,
    repo: UserRepository,
    storage_service: CloudStorageService,
    try_on_service: VertexTryOnService,
    upscale_service: UpscaleService,
) -> None:
    """
    Настроить все хендлеры.

    Args:
        router: Роутер aiogram
        bot: Экземпляр бота
        repo: Репозиторий для работы с БД
        storage_service: Сервис для работы с GCS
        try_on_service: Сервис для генерации примерки
        upscale_service: Сервис для апскейла изображений
    """
    privacy_middleware = PrivacyConsentMiddleware(repo)
    router.message.middleware(privacy_middleware)
    router.callback_query.middleware(privacy_middleware)

    # Регистрируем middleware для альбомов
    album_middleware = AlbumMiddleware(delay=1.5)
    router.message.middleware(album_middleware)
    
    # Команда /start
    async def start_handler(message):
        await start.start_command(message, bot, repo)
    
    router.message.register(
        start_handler,
        Command("start"),
    )
    
    # Callback: Выбор языка
    async def language_selection_handler(callback, state):
        await language.handle_language_selection(callback, bot, repo)
    
    router.callback_query.register(
        language_selection_handler,
        lambda c: c.data and c.data.startswith("select_language_"),
    )

    async def privacy_consent_handler(callback, state):
        await privacy.handle_privacy_consent_accept(callback, bot, repo)

    router.callback_query.register(
        privacy_consent_handler,
        F.data == "privacy_consent_accept",
    )

    # Callback: Смена языка
    async def switch_language_handler(callback, state):
        await language.handle_switch_language(callback, bot, repo)
    
    router.callback_query.register(
        switch_language_handler,
        F.data == "switch_language",
    )
    
    # Callback: Добавить модель (из главного меню)
    async def add_model_handler(callback, state):
        lang = await get_user_language(repo, callback.from_user.id)
        await model_upload.handle_add_model_callback(
            callback, state, bot, repo, storage_service, lang
        )
    
    router.callback_query.register(
        add_model_handler,
        F.data == "add_model",
    )
    
    # Callback: Добавить новую модель (из списка моделей)
    async def add_new_model_handler(callback, state):
        lang = await get_user_language(repo, callback.from_user.id)
        await model_upload.handle_add_new_model_from_list(callback, state, bot, lang)
    
    router.callback_query.register(
        add_new_model_handler,
        F.data == "add_new_model_from_list",
    )
    
    # Callback: Мои модели
    async def my_models_handler(callback, state):
        lang = await get_user_language(repo, callback.from_user.id)
        await model_list.handle_my_models_callback(callback, state, bot, repo, storage_service, lang)
    
    router.callback_query.register(
        my_models_handler,
        F.data == "my_models",
    )
    
    # Callback: Назад в меню
    async def back_to_menu_handler(callback, state):
        lang = await get_user_language(repo, callback.from_user.id)
        await navigation.handle_back_to_menu(callback, state, bot, lang)
    
    router.callback_query.register(
        back_to_menu_handler,
        F.data == "back_to_menu",
    )
    
    # Callback: Удалить модель
    async def model_delete_handler(callback, state):
        lang = await get_user_language(repo, callback.from_user.id)
        await model_list.handle_model_delete(callback, state, repo, bot, storage_service, lang)
    
    router.callback_query.register(
        model_delete_handler,
        lambda c: c.data and c.data.startswith("model_delete_"),
    )
    
    # Callback: Навигация по галерее моделей
    async def model_navigation_handler(callback):
        lang = await get_user_language(repo, callback.from_user.id)
        await model_gallery.handle_model_navigation(callback, bot, repo, storage_service, lang)
    
    router.callback_query.register(
        model_navigation_handler,
        lambda c: c.data and (c.data.startswith("model_prev_") or c.data.startswith("model_next_")),
    )
    
    # Фото модели в состоянии waiting_for_model_photo
    async def model_photo_handler(message, state):
        lang = await get_user_language(repo, message.from_user.id)
        await model_upload.handle_model_photo(message, state, bot, repo, storage_service, lang)
    
    router.message.register(
        model_photo_handler,
        F.photo,
        ModelStates.waiting_for_model_photo,
    )
    
    # Callback: Примерка
    async def try_on_handler(callback, state):
        lang = await get_user_language(repo, callback.from_user.id)
        await try_on.handle_try_on_callback(callback, state, bot, repo, storage_service, lang)
    
    router.callback_query.register(
        try_on_handler,
        F.data == "try_on",
    )
    
    # Callback: Новая примерка (из результата)
    async def new_try_on_handler(callback, state):
        lang = await get_user_language(repo, callback.from_user.id)
        await try_on.handle_new_try_on_callback(callback, state, bot, repo, storage_service, lang)
    
    router.callback_query.register(
        new_try_on_handler,
        F.data == "new_try_on",
    )
    
    # Callback: Выбор модели для примерки
    async def try_on_select_model_handler(callback, state):
        lang = await get_user_language(repo, callback.from_user.id)
        await try_on_selection.handle_model_selection_for_try_on(callback, state, bot, repo, lang)
    
    router.callback_query.register(
        try_on_select_model_handler,
        lambda c: c.data and c.data.startswith("try_on_select_model_"),
    )
    
    # Фото модели в состоянии waiting_for_model_photo (для примерки)
    async def try_on_model_photo_handler(message, state):
        lang = await get_user_language(repo, message.from_user.id)
        await try_on_selection.handle_model_photo_for_try_on(message, state, bot, repo, storage_service, lang)
    
    router.message.register(
        try_on_model_photo_handler,
        F.photo,
        TryOnStates.waiting_for_model_photo,
    )
    
    # Фото одежды в состоянии waiting_for_garment_photo
    async def garment_photo_handler(message, state, **kwargs):
        album = kwargs.get("album")
        lang = await get_user_language(repo, message.from_user.id)
        await try_on_processing.handle_garment_photo(
            message, state, bot, try_on_service, storage_service, repo, album, lang
        )
    
    router.message.register(
        garment_photo_handler,
        F.photo,
        TryOnStates.waiting_for_garment_photo,
    )
    
    # Callback: Переключение меню скачивания
    async def toggle_download_menu_handler(callback, state):
        lang = await get_user_language(repo, callback.from_user.id)
        await download_menu.handle_toggle_download_menu(callback, state, bot, lang)
    
    router.callback_query.register(
        toggle_download_menu_handler,
        F.data == "toggle_download_menu",
    )
    
    # Callback: Скачивание отдельного фото
    async def download_photo_handler(callback, state):
        lang = await get_user_language(repo, callback.from_user.id)
        await download_menu.handle_download_photo(
            callback, state, bot, storage_service, repo, upscale_service, lang
        )
    
    router.callback_query.register(
        download_photo_handler,
        lambda c: c.data and (
            c.data.startswith("download_photo_") or c.data == "download_photo_single"
        ),
    )

    # Callback: Открыть меню отзыва
    async def open_feedback_handler(callback, state):
        lang = await get_user_language(repo, callback.from_user.id)
        await feedback.open_feedback_menu(callback, state, bot, lang)

    router.callback_query.register(
        open_feedback_handler,
        F.data == "open_feedback",
    )

    # Callback: Отменить отзыв
    async def cancel_feedback_handler(callback, state):
        lang = await get_user_language(repo, callback.from_user.id)
        await feedback.cancel_feedback(callback, state, bot, lang)

    router.callback_query.register(
        cancel_feedback_handler,
        F.data == "cancel_feedback",
    )

    # Сообщение: Получение текста/фото отзыва
    async def feedback_message_handler(message, state):
        lang = await get_user_language(repo, message.from_user.id)
        await feedback.handle_feedback_message(message, state, bot, lang)

    router.message.register(
        feedback_message_handler,
        FeedbackStates.waiting_for_feedback,
    )

    # ВРЕМЕННО: Лог file_id при отправке фото без активного состояния FSM
    router.message.register(
        debug_photo_file_id.log_photo_file_id,
        F.photo,
        StateFilter(None),
    )
