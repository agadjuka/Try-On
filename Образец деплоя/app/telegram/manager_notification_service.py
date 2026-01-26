"""
Сервис для отправки уведомлений менеджеру
"""
import logging
from typing import Optional
from telegram import Bot

logger = logging.getLogger(__name__)


class ManagerNotificationService:
    """Сервис для отправки уведомлений менеджеру"""
    
    def __init__(self, bot_token: Optional[str] = None):
        """Инициализация сервиса."""
        self.bot_token = bot_token
    
    async def send_manager_notification(
        self,
        bot: Bot,
        client_telegram_id: int,
        reason: str,
        recent_messages: list,
        manager_chat_id: Optional[int] = None
    ) -> None:
        """
        Отправляет уведомление менеджеру о вызове
        
        Args:
            bot: Экземпляр Telegram бота
            client_telegram_id: ID клиента в Telegram
            reason: Причина вызова менеджера
            recent_messages: Последние сообщения из переписки (5-6 сообщений)
            manager_chat_id: ID чата менеджера. Если None, отправляется клиенту (для тестирования)
        """
        try:
            recipient_id = manager_chat_id if manager_chat_id is not None else client_telegram_id
            
            message_lines = [
                "[ЭТО СООБЩЕНИЕ ОТПРАВЛЕНО ДЛЯ ДЕМОНСТРАЦИИ. В РАБОЧЕЙ ВЕРСИИ ОНО БУДЕТ ОТПРАВЛЯТЬСЯ МЕНЕДЖЕРУ]",
                "",
                "🔔 Вызов менеджера",
                "",
                f"👤 Клиент: ID {client_telegram_id}",
                "",
                f"📋 Причина: {reason}",
                "",
                "💬 Последние сообщения из переписки:",
                ""
            ]
            
            from langchain_core.messages import HumanMessage, AIMessage
            
            for msg in recent_messages[-6:]:
                if not isinstance(msg, (HumanMessage, AIMessage)):
                    continue
                
                content = msg.content
                if content is None:
                    continue
                if isinstance(content, list):
                    content = " ".join(str(item) for item in content)
                else:
                    content = str(content)
                
                if not content.strip():
                    continue
                
                if len(content) > 200:
                    content = content[:200] + "..."
                
                sender = "👤 Клиент" if isinstance(msg, HumanMessage) else "🤖 Агент"
                message_lines.append(f"{sender}: {content}")
                message_lines.append("")
            
            message_text = "\n".join(message_lines)
            await bot.send_message(
                chat_id=recipient_id,
                text=message_text
            )
            
            logger.info(f"Уведомление менеджеру отправлено в чат {recipient_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления менеджеру: {e}", exc_info=True)
            # Не прерываем выполнение, если не удалось отправить уведомление

