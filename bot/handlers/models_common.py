"""Общие вспомогательные функции для работы с фото-моделями (лимиты и навигация)."""

import asyncio

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.database.repo_factory import UserRepository
from bot.services.storage import CloudStorageService
from bot.locales.texts import get_text


async def check_models_limit_and_redirect(
    message: Message,
    state: FSMContext,
    bot: Bot,
    repo: UserRepository,
    storage_service: CloudStorageService,
    lang: str = "ru",
    cleanup_try_on_selection: bool = False,
) -> bool:
    """
    Проверить лимит сохранённых фото-моделей (максимум 7) и при превышении
    показать предупреждение и переадресовать пользователя в раздел «Ваши фото».

    Args:
        message: Входящее сообщение пользователя
        state: Контекст FSM
        bot: Экземпляр бота
        repo: Репозиторий для работы с БД
        storage_service: Сервис для работы с GCS
        lang: Язык интерфейса
        cleanup_try_on_selection: Нужно ли дополнительно закрыть экран выбора
            фото при примерке (альбом + сообщение «Выберите Ваше фото...»)

    Returns:
        True, если лимит достигнут и дальнейшую обработку фото нужно прекратить.
        False, если лимит не превышен и можно продолжать обработку.
    """
    user_id = str(message.from_user.id)

    existing_models = await repo.get_user_models(user_id)
    if len(existing_models) < 7:
        return False

    # В режиме примерки сначала закрываем экран выбора фото (альбом + сообщение),
    # чтобы при переходе в "Мои фото" не осталось старых сообщений.
    if cleanup_try_on_selection:
        from bot.handlers.try_on_utils import delete_try_on_selection_messages

        await delete_try_on_selection_messages(
            bot=bot,
            chat_id=message.from_user.id,
            state=state,
        )

    # Переходим в раздел "Мои фото"
    from bot.handlers.model_list import handle_my_models_callback

    class _FakeMessage:
        """Сообщение-заглушка, чтобы handle_my_models_callback мог вызвать delete()."""

        async def delete(self):
            # Ничего не делаем — реальных сообщений удалять не нужно
            return

    class _FakeCallback:
        """Простой объект, имитирующий CallbackQuery для handle_my_models_callback."""

        def __init__(self, from_user):
            self.from_user = from_user
            self.data = "my_models"
            self._message = _FakeMessage()

        @property
        def message(self):
            return self._message

        async def answer(self, *args, **kwargs):
            # Ничего не делаем, чтобы удовлетворить вызов callback.answer()
            return

    fake_callback = _FakeCallback(message.from_user)

    await handle_my_models_callback(
        callback=fake_callback,
        state=state,
        bot=bot,
        repo=repo,
        storage_service=storage_service,
        lang=lang,
    )

    # После того как пользователь уже в разделе "Мои фото",
    # отправляем предупреждение, чтобы оно оказалось внизу.
    warn_message = await message.answer(get_text("models_limit_reached", lang))

    # Удаляем предупреждение через 5 секунд, не блокируя основную логику
    async def _delete_warn():
        await asyncio.sleep(5)
        try:
            await bot.delete_message(
                chat_id=message.chat.id,
                message_id=warn_message.message_id,
            )
        except Exception:
            pass

    asyncio.create_task(_delete_warn())
    return True

