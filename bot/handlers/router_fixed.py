"""Роутер для регистрации всех хендлеров."""

from aiogram import Router, F
from aiogram.filters import Command

from bot.database.repo_factory import UserRepository
from bot.services.storage import CloudStorageService
from bot.services.try_on import VertexTryOnService
from bot.states.user_states import ModelStates, TryOnStates
from bot.handlers import (
    start,
    model_upload,
    model_list,
    model_gallery,
    navigation,
    try_on,
    try_on_selection,
    try_on_processing,
)
from bot.middlewares.album import AlbumMiddleware


def setup_handlers(
    router: Router,
    bot,
    repo: UserRepository,
    storage_service: CloudStorageService,
    try_on_service: VertexTryOnService,
) -> None:
    """
    Настроить все хендлеры.

    Args:
        router: Роутер aiogram
        bot: Экземпляр бота
        repo: Репозиторий для работы с БД
        storage_service: Сервис для работы с GCS
        try_on_service: Сервис для генерации примерки
    """
    lang = "ru"  # TODO: получать из настроек пользователя
    
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
    
    # Callback: Добавить модель (из главного меню)
    async def add_model_handler(callback, state):
        await model_upload.handle_add_model_callback(callback, state, lang)
    
    router.callback_query.register(
        add_model_handler,
        F.data == "add_model",
    )
    
    # Callback: Добавить новую модель (из списка моделей)
    async def add_new_model_handler(callback, state):
        await model_upload.handle_add_new_model_from_list(callback, state, bot, lang)
    
    router.callback_query.register(
        add_new_model_handler,
        F.data == "add_new_model_from_list",
    )
    
    # Callback: Мои модели
    async def my_models_handler(callback, state):
        await model_list.handle_my_models_callback(callback, state, bot, repo, storage_service, lang)
    
    router.callback_query.register(
        my_models_handler,
        F.data == "my_models",
    )
    
    # Callback: Назад в меню
    async def back_to_menu_handler(callback, state):
        await navigation.handle_back_to_menu(callback, state, bot, lang)
    
    router.callback_query.register(
        back_to_menu_handler,
        F.data == "back_to_menu",
    )
    
    # Callback: Удалить модель
    async def model_delete_handler(callback, state):
        await model_list.handle_model_delete(callback, state, repo, bot, storage_service, lang)
    
    router.callback_query.register(
        model_delete_handler,
        lambda c: c.data and c.data.startswith("model_delete_"),
    )
    
    # Callback: Навигация по галерее моделей
    async def model_navigation_handler(callback):
        await model_gallery.handle_model_navigation(callback, bot, repo, storage_service, lang)
    
    router.callback_query.register(
        model_navigation_handler,
        lambda c: c.data and (c.data.startswith("model_prev_") or c.data.startswith("model_next_")),
    )
    
    # Фото модели в состоянии waiting_for_model_photo
    async def model_photo_handler(message, state):
        await model_upload.handle_model_photo(message, state, bot, repo, storage_service, lang)
    
    router.message.register(
        model_photo_handler,
        F.photo,
        ModelStates.waiting_for_model_photo,
    )
    
    # Callback: Примерка
    async def try_on_handler(callback, state):
        await try_on.handle_try_on_callback(callback, state, bot, repo, storage_service, lang)
    
    router.callback_query.register(
        try_on_handler,
        F.data == "try_on",
    )
    
    # Callback: Новая примерка (из результата)
    async def new_try_on_handler(callback, state):
        await try_on.handle_new_try_on_callback(callback, state, bot, repo, storage_service, lang)
    
    router.callback_query.register(
        new_try_on_handler,
        F.data == "new_try_on",
    )
    
    # Callback: Выбор модели для примерки
    async def try_on_select_model_handler(callback, state):
        await try_on_selection.handle_model_selection_for_try_on(callback, state, bot, repo, lang)
    
    router.callback_query.register(
        try_on_select_model_handler,
        lambda c: c.data and c.data.startswith("try_on_select_model_"),
    )
    
    # Фото модели в состоянии waiting_for_model_photo (для примерки)
    async def try_on_model_photo_handler(message, state):
        await try_on_selection.handle_model_photo_for_try_on(message, state, bot, repo, storage_service, lang)
    
    router.message.register(
        try_on_model_photo_handler,
        F.photo,
        TryOnStates.waiting_for_model_photo,
    )
    
    # Фото одежды в состоянии waiting_for_garment_photo
    async def garment_photo_handler(message, state, **kwargs):
        album = kwargs.get("album")
        await try_on_processing.handle_garment_photo(
            message, state, bot, try_on_service, storage_service, repo, album, lang
        )
    
    router.message.register(
        garment_photo_handler,
        F.photo,
        TryOnStates.waiting_for_garment_photo,
    )
    
