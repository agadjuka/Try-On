"""Блокировка действий до принятия условий обработки данных."""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from loguru import logger

from bot.database.repo import FirestoreRepo
from bot.keyboards.user_kb import get_privacy_consent_keyboard
from bot.locales.texts import get_text
from bot.services.language import prime_language_cache


class PrivacyConsentMiddleware(BaseMiddleware):
    """Показывает экран согласия, пока в Firestore не установлен privacy_consent_accepted."""

    def __init__(self, repo: FirestoreRepo) -> None:
        self._repo = repo
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        telegram_id: int | None = None

        if isinstance(event, Message):
            if not event.from_user:
                return await handler(event, data)
            telegram_id = event.from_user.id
            if event.text:
                cmd = event.text.split()[0].split("@", 1)[0]
                if cmd == "/start":
                    return await handler(event, data)
        elif isinstance(event, CallbackQuery):
            if not event.from_user or not event.data:
                return await handler(event, data)
            telegram_id = event.from_user.id
            if event.data.startswith("select_language_"):
                return await handler(event, data)
            if event.data == "privacy_consent_accept":
                return await handler(event, data)
        else:
            return await handler(event, data)

        user_id = str(telegram_id)
        language, privacy_ok = await self._repo.get_user_language_and_privacy(user_id)
        if language is None:
            return await handler(event, data)

        lang = language if language in ("ru", "en") else "ru"
        prime_language_cache(telegram_id, lang)

        if privacy_ok:
            return await handler(event, data)
        text = get_text("privacy_notice", lang)
        keyboard = get_privacy_consent_keyboard(lang)

        try:
            if isinstance(event, Message):
                await event.answer(text, reply_markup=keyboard, parse_mode="HTML")
            else:
                cq = event
                await cq.answer(get_text("privacy_consent_required", lang))
                if cq.message:
                    try:
                        await cq.message.edit_text(
                            text=text,
                            reply_markup=keyboard,
                            parse_mode="HTML",
                        )
                    except TelegramBadRequest as e:
                        err = str(e).lower()
                        if "message is not modified" in err:
                            pass
                        else:
                            await cq.message.answer(
                                text, reply_markup=keyboard, parse_mode="HTML"
                            )
        except Exception as e:
            logger.warning(f"PrivacyConsentMiddleware: не удалось отправить напоминание: {e}")

        return None
