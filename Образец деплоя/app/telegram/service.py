"""Сервис для взаимодействия с агентом через Telegram."""

import logging
import uuid
from typing import Any, Optional

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from telegram import Bot

from app.agent import agent
from app.app_utils.message_time_injector import ensure_time_context
from app.app_utils.typing import ensure_valid_config
from app.app_utils.call_manager_handler import set_call_manager_content_if_empty, check_call_manager_in_messages
from app.fast_api_app import set_tracing_properties
from app.telegram.manager_notification_service import ManagerNotificationService

logger = logging.getLogger(__name__)


class AgentService:
    """Сервис для обработки сообщений через агента."""

    def __init__(self) -> None:
        """Инициализирует сервис."""
        self.agent = agent
        self.manager_notification_service = ManagerNotificationService()

    async def process_message(
        self,
        user_message: str,
        user_id: str,
        bot: Bot,
        chat_id: int,
        session_id: str | None = None
    ) -> Optional[str]:
        """Обрабатывает сообщение пользователя и возвращает ответ агента.

        Args:
            user_message: Текст сообщения от пользователя
            user_id: ID пользователя Telegram
            bot: Экземпляр Telegram бота
            chat_id: ID чата для отправки сообщений
            session_id: ID сессии (опционально)

        Returns:
            Текст ответа от агента или None, если был вызван CallManager
        """
        try:
            logger.info("Обработка сообщения от пользователя %s: %s", user_id, user_message[:100])

            # Создаем HumanMessage из текста пользователя
            input_messages = ensure_time_context([HumanMessage(content=user_message)])

            # Создаем конфигурацию (используем user_id как thread_id для checkpoint)
            initial_config = RunnableConfig()
            if initial_config.get("metadata") is None:
                initial_config["metadata"] = {}
            initial_config["metadata"]["session_id"] = str(user_id)
            initial_config["metadata"]["user_id"] = str(user_id)
            config = ensure_valid_config(initial_config)
            set_tracing_properties(config)
            
            result = self.agent.invoke({"messages": input_messages}, config=config)

            # Извлекаем ответ из результата
            if isinstance(result, dict) and "messages" in result:
                all_messages = result["messages"]
            elif isinstance(result, list):
                all_messages = result
            else:
                all_messages = [result]
            
            # Находим последний HumanMessage (текущий запрос пользователя)
            # Проверяем CallManager только в сообщениях после него (новые сообщения от текущего запроса)
            last_human_index = -1
            for i in range(len(all_messages) - 1, -1, -1):
                if isinstance(all_messages[i], HumanMessage):
                    last_human_index = i
                    break
            
            # Берем только новые сообщения после последнего HumanMessage
            new_messages = all_messages[last_human_index + 1:] if last_human_index >= 0 else all_messages[-3:]
            call_manager_info = check_call_manager_in_messages(new_messages)
            
            if call_manager_info:
                # Устанавливаем reason из tool_calls как content, если пустой
                for msg in reversed(all_messages):
                    if isinstance(msg, AIMessage):
                        set_call_manager_content_if_empty(msg)
                
                logger.info("Обнаружен вызов CallManager. Причина: %s", call_manager_info["reason"])
                await bot.send_message(chat_id=chat_id, text="Пару минут уточню у менеджера")
                await self.manager_notification_service.send_manager_notification(
                    bot=bot,
                    client_telegram_id=int(user_id),
                    reason=call_manager_info["reason"],
                    recent_messages=all_messages[-6:],
                    manager_chat_id=None
                )
                return None

            # Обычная обработка - находим последнее AI сообщение
            ai_response = None
            for msg in reversed(all_messages):
                if isinstance(msg, AIMessage):
                    ai_response = msg
                    break

            if ai_response:
                response_text = ai_response.content
                if isinstance(response_text, list):
                    # Если content - список (например, мультимодальный контент)
                    response_text = " ".join(str(item) for item in response_text)
                else:
                    response_text = str(response_text)
            else:
                response_text = "Не удалось получить ответ от агента"

            logger.info("Ответ агента для пользователя %s: %s", user_id, response_text[:100])
            return response_text

        except Exception as e:
            logger.error("Ошибка при обработке сообщения: %s", str(e), exc_info=True)
            error_message = f"Произошла ошибка при обработке запроса: {str(e)}"
            return error_message
    

