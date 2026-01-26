"""Основной класс Telegram бота."""

import logging
import os
from typing import Any

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.telegram.checkpoint_cleaner import delete_user_checkpoint
from app.telegram.handlers import MessageHandlers
from app.telegram.service import AgentService

logger = logging.getLogger(__name__)

# Глобальное Application для webhook режима (переиспользуется для всех обновлений)
_webhook_application: Application | None = None
_webhook_bot_token: str | None = None


async def _get_webhook_application(bot_token: str) -> Application:
    """Получает или создает глобальное Application для webhook режима.
    
    Args:
        bot_token: Токен Telegram бота
        
    Returns:
        Application объект (инициализированное и запущенное)
    """
    global _webhook_application, _webhook_bot_token
    
    # Если Application уже создан и токен совпадает, возвращаем его
    if _webhook_application is not None and _webhook_bot_token == bot_token:
        # Убеждаемся, что Application запущено
        if not _webhook_application.running:
            await _webhook_application.initialize()
            await _webhook_application.start()
        return _webhook_application
    
    # Создаем новое Application
    _webhook_application = Application.builder().token(bot_token).build()
    _webhook_bot_token = bot_token
    
    # Создаем сервисы для обработки
    agent_service = AgentService()
    handlers = MessageHandlers(agent_service)
    
    # Настраиваем обработчики
    _webhook_application.add_handler(
        MessageHandler((filters.TEXT | filters.VOICE) & ~filters.COMMAND, handlers.handle_message)
    )
    _webhook_application.add_handler(CommandHandler("start", _handle_start_command))
    _webhook_application.add_handler(CommandHandler("new", _handle_new_command))
    _webhook_application.add_error_handler(handlers.handle_error)
    
    # Инициализируем и запускаем Application
    await _webhook_application.initialize()
    await _webhook_application.start()
    
    logger.info("Создано и запущено глобальное Application для webhook режима")
    return _webhook_application


class TelegramBot:
    """Класс для управления Telegram ботом."""

    def __init__(self, token: str | None = None) -> None:
        """Инициализирует бота.

        Args:
            token: Токен Telegram бота. Если не указан, берется из переменной окружения TELEGRAM_BOT_TOKEN
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError(
                "Токен Telegram бота не найден. "
                "Укажите его в параметре token или в переменной окружения TELEGRAM_BOT_TOKEN"
            )

        self.agent_service = AgentService()
        self.handlers = MessageHandlers(self.agent_service)
        self.application: Application | None = None

    def _setup_handlers(self) -> None:
        """Настраивает обработчики команд и сообщений."""
        if not self.application:
            raise RuntimeError("Приложение не инициализировано")

        # Обработчик текстовых и голосовых сообщений
        self.application.add_handler(
            MessageHandler((filters.TEXT | filters.VOICE) & ~filters.COMMAND, self.handlers.handle_message)
        )

        # Обработчик команды /start
        self.application.add_handler(CommandHandler("start", self._handle_start))
        
        # Обработчик команды /new
        self.application.add_handler(CommandHandler("new", self._handle_new))

        # Обработчик ошибок
        self.application.add_error_handler(self.handlers.handle_error)

    async def _handle_start(self, update: Update, context: Any) -> None:
        """Обрабатывает команду /start.

        Args:
            update: Обновление от Telegram
            context: Контекст бота
        """
        welcome_message = (
            "Привет! Я AI-консультант. "
            "Отправьте мне сообщение, и я постараюсь помочь вам."
        )
        await update.message.reply_text(welcome_message)

    async def _handle_new(self, update: Update, context: Any) -> None:
        """Обрабатывает команду /new - удаляет checkpoint пользователя из Firestore.

        Args:
            update: Обновление от Telegram
            context: Контекст бота
        """
        user_id = str(update.effective_user.id)
        
        if delete_user_checkpoint(user_id):
            await update.message.reply_text("Память очищена. Начинаем с чистого листа!")
        else:
            await update.message.reply_text("Не удалось очистить память. Попробуйте позже.")

    async def initialize(self) -> None:
        """Инициализирует приложение бота."""
        self.application = Application.builder().token(self.token).build()
        self._setup_handlers()

    async def start_polling(self) -> None:
        """Запускает бота в режиме polling."""
        if not self.application:
            await self.initialize()

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

    async def stop(self) -> None:
        """Останавливает бота."""
        if self.application:
            logger.info("Остановка Telegram бота...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Telegram бот остановлен")


async def process_update(update_json: dict, bot_token: str) -> None:
    """Обрабатывает обновление от Telegram в формате JSON.
    
    Эта функция может использоваться как для polling, так и для webhook режима.
    
    Args:
        update_json: Обновление от Telegram в формате словаря (JSON)
        bot_token: Токен Telegram бота
    """
    update = None
    application: Application | None = None
    try:
        # Получаем глобальное Application (создается один раз и переиспользуется)
        application = await _get_webhook_application(bot_token)
        
        # Преобразуем словарь в Update объект, используя бот Application
        update = Update.de_json(update_json, application.bot)
        
        if not update:
            logger.warning("Не удалось распарсить обновление")
            return
        
        # Обрабатываем обновление через Application
        await application.process_update(update)
        
    except Exception as e:
        logger.error("Ошибка при обработке обновления: %s", str(e), exc_info=True)
        
        # Пытаемся отправить сообщение об ошибке пользователю
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "Произошла ошибка при обработке вашего сообщения. Попробуйте позже."
                )
        except Exception as send_error:
            logger.error("Не удалось отправить сообщение об ошибке: %s", str(send_error))


async def _handle_start_command(update: Update, context: Any) -> None:
    """Обрабатывает команду /start.
    
    Args:
        update: Обновление от Telegram
        context: Контекст бота
    """
    welcome_message = (
        "Привет! Я AI-консультант. "
        "Отправьте мне сообщение, и я постараюсь помочь вам."
    )
    await update.message.reply_text(welcome_message)


async def _handle_new_command(update: Update, context: Any) -> None:
    """Обрабатывает команду /new - удаляет checkpoint пользователя из Firestore.
    
    Args:
        update: Обновление от Telegram
        context: Контекст бота
    """
    user_id = str(update.effective_user.id)
    
    if delete_user_checkpoint(user_id):
        await update.message.reply_text("Память очищена. Начинаем с чистого листа!")
    else:
        await update.message.reply_text("Не удалось очистить память. Попробуйте позже.")

