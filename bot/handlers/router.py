"""Роутер для регистрации всех хендлеров."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.database.repo import FirestoreRepo
from bot.services.storage import CloudStorageService
from bot.states.user_states import ModelStates
from bot.handlers import start, models


def setup_handlers(
    router: Router,
    bot,
    repo: FirestoreRepo,
    storage_service: CloudStorageService,
) -> None:
    """
    Настроить все хендлеры.

    Args:
        router: Роутер aiogram
        bot: Экземпляр бота
        repo: Репозиторий для работы с БД
        storage_service: Сервис для работы с GCS
    """
    lang = "ru"  # TODO: получать из настроек пользователя
    
    # Команда /start
    async def start_handler(message):
        await start.start_command(message, bot, repo)
    router.message.register(
        start_handler,
        Command("start"),
    )
    
    # Callback: Добавить модель
    async def add_model_handler(callback, state: FSMContext):
        await models.handle_add_model_callback(callback, state, lang)
    router.callback_query.register(
        add_model_handler,
        F.data == "add_model",
    )
    
    # Callback: Мои модели
    async def my_models_handler(callback):
        await models.handle_my_models_callback(callback, bot, repo, storage_service, lang)
    router.callback_query.register(
        my_models_handler,
        F.data == "my_models",
    )
    
    # Callback: Назад в меню
    async def back_to_menu_handler(callback, state: FSMContext):
        await models.handle_back_to_menu(callback, state, lang)
    router.callback_query.register(
        back_to_menu_handler,
        F.data == "back_to_menu",
    )
    
    # Callback: Навигация по моделям
    async def model_navigation_handler(callback):
        await models.handle_model_navigation(callback, bot, repo, storage_service, lang)
    router.callback_query.register(
        model_navigation_handler,
        lambda c: c.data and (c.data.startswith("model_prev_") or c.data.startswith("model_next_")),
    )
    
    # Callback: Выбрать модель
    async def model_select_handler(callback):
        await models.handle_model_select(callback, repo, bot, storage_service, lang)
    router.callback_query.register(
        model_select_handler,
        lambda c: c.data and c.data.startswith("model_select_"),
    )
    
    # Callback: Удалить модель
    async def model_delete_handler(callback):
        await models.handle_model_delete(callback, repo, bot, storage_service, lang)
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
