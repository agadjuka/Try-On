"""Роутер для регистрации всех хендлеров."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.database.repo import FirestoreRepo
from bot.services.storage import CloudStorageService
from bot.services.try_on import VertexTryOnService
from bot.states.user_states import ModelStates, TryOnStates
from bot.handlers import start, models, try_on, try_on_selection, try_on_processing
from bot.middlewares.album import AlbumMiddleware


def setup_handlers(
    router: Router,
    bot,
    repo: FirestoreRepo,
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
    async def add_model_handler(callback, state: FSMContext):
        await models.handle_add_model_callback(callback, state, lang)
    router.callback_query.register(
        add_model_handler,
        F.data == "add_model",
    )
    
    # Callback: Добавить новую модель (из списка моделей)
    async def add_new_model_from_list_handler(callback, state: FSMContext):
        await models.handle_add_new_model_from_list(callback, state, bot, lang)
    router.callback_query.register(
        add_new_model_from_list_handler,
        F.data == "add_new_model_from_list",
    )
    
    # Callback: Мои модели
    async def my_models_handler(callback, state: FSMContext):
        await models.handle_my_models_callback(callback, state, bot, repo, storage_service, lang)
    router.callback_query.register(
        my_models_handler,
        F.data == "my_models",
    )
    
    # Callback: Назад в меню
    async def back_to_menu_handler(callback, state: FSMContext):
        await models.handle_back_to_menu(callback, state, bot, lang)
    router.callback_query.register(
        back_to_menu_handler,
        F.data == "back_to_menu",
    )
    
    # Callback: Удалить модель
    async def model_delete_handler(callback, state: FSMContext):
        await models.handle_model_delete(callback, state, repo, bot, storage_service, lang)
    router.callback_query.register(
        model_delete_handler,
        lambda c: c.data and c.data.startswith("model_delete_"),
    )
    
    # Фото модели в состоянии waiting_for_model_photo
    async def model_photo_handler(message, state: FSMContext):
        await models.handle_model_photo(message, state, bot, repo, storage_service, lang)
    router.message.register(
        model_photo_handler,
        F.photo,
        ModelStates.waiting_for_model_photo,
    )
    
    # Callback: Примерка
    async def try_on_handler(callback, state: FSMContext):
        await try_on.handle_try_on_callback(
            callback, state, bot, repo, storage_service, lang
        )
    router.callback_query.register(
        try_on_handler,
        F.data == "try_on",
    )
    
    # Callback: Выбор модели для примерки
    async def try_on_model_select_handler(callback, state: FSMContext):
        await try_on_selection.handle_model_selection_for_try_on(
            callback, state, bot, repo, lang
        )
    router.callback_query.register(
        try_on_model_select_handler,
        lambda c: c.data and c.data.startswith("try_on_select_model_"),
    )
    
    # Фото одежды в состоянии waiting_for_garment_photo
    async def garment_photo_handler(message, state: FSMContext, album=None):
        # album передается из middleware через data, если это альбом
        await try_on_processing.handle_garment_photo(
            message, state, bot, storage_service, try_on_service, album, lang
        )
    router.message.register(
        garment_photo_handler,
        F.photo,
        TryOnStates.waiting_for_garment_photo,
    )
