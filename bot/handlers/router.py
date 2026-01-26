"""Роутер для регистрации всех хендлеров."""

from aiogram import Router, F
from aiogram.filters import Command

from bot.database.repo import FirestoreRepo
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
    router.message.register(
        lambda m: start.start_command(m, bot, repo),
        Command("start"),
    )
    
    # Callback: Добавить модель (из главного меню)
    router.callback_query.register(
        lambda c, s: model_upload.handle_add_model_callback(c, s, lang),
        F.data == "add_model",
    )
    
    # Callback: Добавить новую модель (из списка моделей)
    router.callback_query.register(
        lambda c, s: model_upload.handle_add_new_model_from_list(c, s, bot, lang),
        F.data == "add_new_model_from_list",
    )
    
    # Callback: Мои модели
    router.callback_query.register(
        lambda c, s: model_list.handle_my_models_callback(c, s, bot, repo, storage_service, lang),
        F.data == "my_models",
    )
    
    # Callback: Назад в меню
    router.callback_query.register(
        lambda c, s: navigation.handle_back_to_menu(c, s, bot, lang),
        F.data == "back_to_menu",
    )
    
    # Callback: Удалить модель
    router.callback_query.register(
        lambda c, s: model_list.handle_model_delete(c, s, repo, bot, storage_service, lang),
        lambda c: c.data and c.data.startswith("model_delete_"),
    )
    
    # Callback: Навигация по галерее моделей
    router.callback_query.register(
        lambda c: model_gallery.handle_model_navigation(c, bot, repo, storage_service, lang),
        lambda c: c.data and (c.data.startswith("model_prev_") or c.data.startswith("model_next_")),
    )
    
    # Фото модели в состоянии waiting_for_model_photo
    router.message.register(
        lambda m, s: model_upload.handle_model_photo(m, s, bot, repo, storage_service, lang),
        F.photo,
        ModelStates.waiting_for_model_photo,
    )
    
    # Callback: Примерка
    router.callback_query.register(
        lambda c, s: try_on.handle_try_on_callback(c, s, bot, repo, storage_service, lang),
        F.data == "try_on",
    )
    
    # Callback: Новая примерка (из результата)
    router.callback_query.register(
        lambda c, s: try_on.handle_new_try_on_callback(c, s, bot, repo, storage_service, lang),
        F.data == "new_try_on",
    )
    
    # Callback: Выбор модели для примерки
    router.callback_query.register(
        lambda c, s: try_on_selection.handle_model_selection_for_try_on(c, s, bot, repo, lang),
        lambda c: c.data and c.data.startswith("try_on_select_model_"),
    )
    
    # Фото модели в состоянии waiting_for_model_photo (для примерки)
    router.message.register(
        lambda m, s: try_on_selection.handle_model_photo_for_try_on(m, s, bot, repo, storage_service, lang),
        F.photo,
        TryOnStates.waiting_for_model_photo,
    )
    
    # Фото одежды в состоянии waiting_for_garment_photo
    router.message.register(
        lambda m, s, **d: try_on_processing.handle_garment_photo(
            m, s, bot, try_on_service, d.get("album"), lang
        ),
        F.photo,
        TryOnStates.waiting_for_garment_photo,
    )
