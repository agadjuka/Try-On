"""Обработчик команды /start."""

from aiogram import Bot
from aiogram.types import Message
from loguru import logger

from bot.database.repo import FirestoreRepo
from bot.keyboards.user_kb import get_main_menu_keyboard
from bot.locales.texts import get_text
from bot.admin.factory import get_admin_service


async def start_command(
    message: Message,
    bot: Bot,
    repo: FirestoreRepo,
) -> None:
    """
    Обработчик команды /start.

    Args:
        message: Сообщение от пользователя
        bot: Экземпляр бота
        repo: Репозиторий для работы с БД
    """
    user = message.from_user
    lang = "ru"  # TODO: получать из настроек пользователя
    
    try:
        # Проверяем/создаем пользователя в БД
        user_id = await repo.add_user(
            telegram_id=user.id,
            username=user.username,
        )
        logger.info(f"Пользователь {user_id} обработан в /start")
        
        # Создаем топик в админ-панели при команде /start (если настроено)
        logger.info(f"🔍 Попытка создать топик в админ-панели для user_id={user.id}...")
        admin_service = get_admin_service(bot)
        if admin_service:
            logger.info("✅ AdminPanelService получен, создание топика...")
            try:
                topic_id = await admin_service.get_or_create_topic(user)
                logger.success(f"✅ Топик успешно создан/получен: topic_id={topic_id} для user_id={user.id}")
            except Exception as e:
                logger.error(f"❌ Не удалось создать топик в админ-панели для user_id={user.id}: {e}", exc_info=True)
        else:
            logger.warning(f"⚠️ AdminPanelService недоступен (админ-панель не настроена или ошибка инициализации)")
        
        # Отправляем приветствие и главное меню
        await message.answer(
            get_text("welcome", lang),
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode="HTML",
        )
        
    except Exception as e:
        logger.error(f"Ошибка в /start для пользователя {user.id}: {e}")
        await message.answer(
            "Произошла ошибка. Попробуй позже.",
        )
