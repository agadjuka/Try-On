"""Модуль для отправки ошибок в админ-панель."""

import asyncio
import traceback
from typing import Optional
from loguru import logger

from aiogram import Bot
from aiogram.types import User

from bot.admin.service import AdminPanelService


class ErrorReporter:
    """Класс для отправки ошибок в админ-панель в топик пользователя."""

    SEND_TIMEOUT = 30.0

    def __init__(self, admin_service: AdminPanelService):
        """
        Инициализирует репортер ошибок.

        Args:
            admin_service: Сервис админ-панели
        """
        self.admin_service = admin_service

    def _format_error_message(
        self,
        user: User,
        error: Exception,
        context: str = "",
        raw_response: Optional[str] = None,
    ) -> str:
        """
        Форматирует сообщение об ошибке.

        Args:
            user: Пользователь, у которого произошла ошибка
            error: Исключение
            context: Контекст ошибки (например, "Try-On Generation")
            raw_response: Сырой ответ от API (JSON строка)

        Returns:
            Отформатированное сообщение
        """
        # Формируем информацию о пользователе
        if user.username:
            user_info = f"@{user.username} (ID: {user.id})"
        else:
            user_info = f"ID: {user.id}"
            if user.full_name:
                user_info = f"{user.full_name} ({user_info})"

        # Формируем заголовок
        context_text = f" [{context}]" if context else ""
        message_parts = [f"❌ Ошибка{context_text}\n"]

        # Информация о пользователе
        message_parts.append(f"Пользователь: {user_info}\n")

        # Тип и текст ошибки
        error_type = type(error).__name__
        error_message = str(error)
        message_parts.append(f"Тип: {error_type}")
        message_parts.append(f"Ошибка: {error_message}\n")

        # Сырой ответ от API (если есть)
        if raw_response:
            message_parts.append(f"Сырой ответ API:\n<code>{raw_response}</code>\n")

        # Traceback (если есть)
        tb = traceback.format_exc()
        if tb and tb != "NoneType: None\n":
            # Ограничиваем длину traceback (первые 1500 символов)
            tb_short = tb[:1500]
            if len(tb) > 1500:
                tb_short += "\n... (обрезано)"
            message_parts.append(f"Traceback:\n<pre>{tb_short}</pre>")

        return "\n".join(message_parts)

    async def send_error(
        self,
        user: User,
        error: Exception,
        context: str = "",
        raw_response: Optional[str] = None,
    ) -> None:
        """
        Отправляет ошибку в админ-панель в топик пользователя.

        Args:
            user: Пользователь, у которого произошла ошибка
            error: Исключение
            context: Контекст ошибки (например, "Try-On Generation")
            raw_response: Сырой ответ от API (JSON строка)
        """
        if not self.admin_service:
            logger.warning("AdminPanelService недоступен, ошибка не отправлена")
            return
            
        if not self.admin_service._should_forward(user):
            return

        try:
            # Форматируем сообщение
            error_message = self._format_error_message(
                user=user,
                error=error,
                context=context,
                raw_response=raw_response,
            )

            # Получаем или создаем топик
            topic_id = await asyncio.wait_for(
                self.admin_service.get_or_create_topic(user),
                timeout=self.SEND_TIMEOUT,
            )

            # Отправляем сообщение в топик
            await asyncio.wait_for(
                self.admin_service.bot.send_message(
                    chat_id=self.admin_service.admin_group_id,
                    text=error_message,
                    message_thread_id=topic_id,
                    parse_mode="HTML",
                ),
                timeout=self.SEND_TIMEOUT,
            )

            logger.info(f"Ошибка отправлена в админ-панель для пользователя {user.id}")

        except asyncio.TimeoutError:
            logger.error(
                f"Таймаут отправки ошибки в админ-панель (превышен лимит {self.SEND_TIMEOUT}с)"
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке ошибки в админ-панель: {e}")

    def send_error_async(
        self,
        user: User,
        error: Exception,
        context: str = "",
        raw_response: Optional[str] = None,
    ) -> None:
        """
        Отправляет ошибку в админ-панель асинхронно в фоне (не блокирует).

        Args:
            user: Пользователь, у которого произошла ошибка
            error: Исключение
            context: Контекст ошибки (например, "Try-On Generation")
            raw_response: Сырой ответ от API (JSON строка)
        """
        asyncio.create_task(
            self.send_error(
                user=user,
                error=error,
                context=context,
                raw_response=raw_response,
            )
        )


def get_error_reporter(bot: Bot) -> Optional[ErrorReporter]:
    """
    Получает экземпляр ErrorReporter.

    Args:
        bot: Экземпляр Telegram бота

    Returns:
        Экземпляр ErrorReporter или None, если админ-панель не настроена
    """
    from bot.admin.factory import get_admin_service

    admin_service = get_admin_service(bot)
    if admin_service is None:
        return None

    return ErrorReporter(admin_service)
