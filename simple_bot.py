"""Простой Telegram-бот для тестирования Virtual Try-On сервисов."""

import asyncio
import base64
from io import BytesIO
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, PhotoSize, BufferedInputFile
from loguru import logger

from bot.core.config import get_settings
from bot.core.logger import setup_logger
from bot.services.storage import CloudStorageService
from bot.services.try_on import VertexTryOnService


class GenStates(StatesGroup):
    """Состояния FSM для генерации."""
    waiting_for_model = State()
    waiting_for_garment = State()


async def get_largest_photo(photos: list[PhotoSize]) -> PhotoSize:
    """
    Получить фото с максимальным размером.
    В Telegram фото приходит в разных размерах, самое большое обычно последнее (photo[-1]).

    Args:
        photos: Список размеров фото

    Returns:
        Фото с максимальным размером (обычно photo[-1])
    """
    # Самый простой способ - взять последний элемент (самое большое фото)
    return photos[-1]


async def download_photo_to_bytes(bot: Bot, photo: PhotoSize) -> bytes:
    """
    Скачать фото в байты через правильный пайплайн Telegram → байты.

    Args:
        bot: Экземпляр бота
        photo: Объект фото

    Returns:
        Байты фото
    """
    # 1. Получаем информацию о файле через get_file()
    file = await bot.get_file(photo.file_id)
    
    # 2. Проверяем наличие file_path
    if not file.file_path:
        raise Exception(f"Не удалось получить file_path для файла {photo.file_id}")
    
    # 3. Скачиваем файл через bot.download_file() - правильный метод в aiogram 3
    # Он автоматически использует https://api.telegram.org/file/bot<TOKEN>/<file_path>
    # и возвращает BytesIO, из которого нужно прочитать байты
    file_io = await bot.download_file(file.file_path)
    
    # 4. Читаем байты из BytesIO
    file_bytes = file_io.read()
    
    # 5. Закрываем BytesIO
    file_io.close()
    
    return file_bytes


async def start_command(message: Message, state: FSMContext) -> None:
    """
    Обработчик команды /start.

    Args:
        message: Сообщение от пользователя
        state: Контекст FSM
    """
    await state.set_state(GenStates.waiting_for_model)
    await message.answer(
        "Привет! Это тест. Скинь фото модели (человека)."
    )


async def handle_model_photo(
    message: Message,
    state: FSMContext,
    bot: Bot,
    storage_service: CloudStorageService,
) -> None:
    """
    Обработчик фото модели.

    Args:
        message: Сообщение с фото
        state: Контекст FSM
        bot: Экземпляр бота
        storage_service: Сервис для работы с GCS
    """
    if not message.photo:
        await message.answer("Пожалуйста, отправь фото.")
        return

    try:
        # Получаем фото максимального размера
        largest_photo = await get_largest_photo(message.photo)
        
        # Скачиваем фото
        await message.answer("Загружаю фото модели...")
        photo_bytes = await download_photo_to_bytes(bot, largest_photo)
        
        # Кодируем в base64 (как в старой версии)
        photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
        
        # Сохраняем base64 в FSM (не загружаем в GCS перед запросом)
        await state.update_data(model_base64=photo_base64)
        
        # Переключаем состояние
        await state.set_state(GenStates.waiting_for_garment)
        await message.answer("Отлично. Теперь скинь фото одежды.")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке фото модели: {e}")
        await message.answer(
            f"Произошла ошибка при загрузке фото модели: {str(e)}\n"
            "Попробуй еще раз или нажми /start."
        )


async def handle_garment_photo(
    message: Message,
    state: FSMContext,
    bot: Bot,
    storage_service: CloudStorageService,
    try_on_service: VertexTryOnService,
) -> None:
    """
    Обработчик фото одежды.

    Args:
        message: Сообщение с фото
        state: Контекст FSM
        bot: Экземпляр бота
        storage_service: Сервис для работы с GCS
        try_on_service: Сервис для генерации try-on
    """
    if not message.photo:
        await message.answer("Пожалуйста, отправь фото.")
        return

    try:
        # Получаем данные из FSM
        data = await state.get_data()
        model_base64 = data.get("model_base64")
        
        if not model_base64:
            await message.answer(
                "Не найдено фото модели. Нажми /start для начала."
            )
            await state.clear()
            return

        # Защита от повторных вызовов: проверяем, не идет ли уже обработка
        if data.get("processing", False):
            await message.answer(
                "Генерация уже выполняется. Пожалуйста, подожди..."
            )
            return

        # Защита от повторных вызовов: проверяем еще раз после получения данных
        if data.get("processing", False):
            await message.answer(
                "Генерация уже выполняется. Пожалуйста, подожди..."
            )
            return

        # Устанавливаем флаг обработки
        await state.update_data(processing=True)

        # Уведомляем о начале генерации
        await message.answer(
            "Начинаю генерацию... Подожди 15-30 секунд."
        )

        # Получаем фото максимального размера
        largest_photo = await get_largest_photo(message.photo)
        
        # Скачиваем фото одежды
        photo_bytes = await download_photo_to_bytes(bot, largest_photo)
        
        # Кодируем в base64 (как в старой версии)
        garment_base64 = base64.b64encode(photo_bytes).decode("utf-8")
        
        # Логируем перед вызовом API
        logger.info("=" * 60)
        logger.info("ВЫЗОВ generate_try_on - ОДИН РАЗ")
        logger.info("=" * 60)
        
        # Генерируем try-on используя base64 (как в старой версии)
        result_gcs_uri = await try_on_service.generate_try_on(
            person_image_base64=model_base64,
            product_image_base64=garment_base64,
            storage_service=storage_service,
        )
        
        logger.info("=" * 60)
        logger.info("generate_try_on ЗАВЕРШЕН УСПЕШНО")
        logger.info("=" * 60)
        
        # Скачиваем результат из GCS
        result_bytes = await storage_service.download_file(result_gcs_uri)
        
        # Отправляем результат пользователю
        photo_file = BufferedInputFile(
            file=result_bytes,
            filename="result.png"
        )
        
        await message.answer_photo(
            photo=photo_file,
            caption="Готово! Жми /start для новой пары."
        )
        
        # Сбрасываем состояние и флаг обработки
        await state.clear()
        
    except ValueError as e:
        logger.error(f"Ошибка валидации при генерации: {e}")
        await message.answer(
            f"Ошибка при генерации: {str(e)}\n"
            "Попробуй другие фото или нажми /start."
        )
        # Сбрасываем флаг обработки и состояние
        await state.update_data(processing=False)
        await state.clear()
        
    except RuntimeError as e:
        logger.error(f"Ошибка API при генерации: {e}")
        error_msg = str(e)
        
        # Проверяем на лимит запросов (429)
        if "429" in error_msg or "too many requests" in error_msg.lower():
            await message.answer(
                "⚠️ Превышен лимит запросов к Vertex AI API.\n"
                "Это означает, что было слишком много запросов за короткое время.\n"
                "Подожди 1-2 минуты и попробуй снова.\n"
                "Или нажми /start для начала заново."
            )
        # Проверяем на safety filter
        elif "safety" in error_msg.lower() or "blocked" in error_msg.lower():
            await message.answer(
                "Генерация заблокирована системой безопасности.\n"
                "Попробуй другие фото или нажми /start."
            )
        else:
            await message.answer(
                f"Ошибка API: {error_msg}\n"
                "Попробуй еще раз или нажми /start."
            )
        # Сбрасываем флаг обработки и состояние
        await state.update_data(processing=False)
        await state.clear()
        
    except Exception as e:
        logger.error(f"Неожиданная ошибка при генерации: {e}")
        await message.answer(
            f"Произошла неожиданная ошибка: {str(e)}\n"
            "Попробуй еще раз или нажми /start."
        )
        # Сбрасываем флаг обработки и состояние
        await state.update_data(processing=False)
        await state.clear()


async def handle_unknown_message(message: Message, state: FSMContext) -> None:
    """
    Обработчик неизвестных сообщений.

    Args:
        message: Сообщение от пользователя
        state: Контекст FSM
    """
    current_state = await state.get_state()
    
    if current_state == GenStates.waiting_for_model:
        await message.answer("Пожалуйста, отправь фото модели.")
    elif current_state == GenStates.waiting_for_garment:
        await message.answer("Пожалуйста, отправь фото одежды.")
    else:
        await message.answer("Нажми /start для начала.")


async def main() -> None:
    """Основная функция запуска бота."""
    setup_logger()
    logger.info("Запуск тестового бота...")

    # Загружаем настройки
    try:
        settings = get_settings()
    except Exception as e:
        logger.error(
            f"Ошибка загрузки настроек: {e}\n"
            "Убедитесь, что файл .env существует и содержит все необходимые переменные:\n"
            "- BOT_TOKEN\n"
            "- GOOGLE_CLOUD_PROJECT_ID\n"
            "- GOOGLE_CLOUD_REGION\n"
            "- GCS_BUCKET_NAME"
        )
        return

    # Проверяем наличие токена
    if not settings.bot_token or not settings.bot_token.strip():
        logger.error(
            "BOT_TOKEN не найден или пустой в файле .env\n"
            "Получите токен у @BotFather в Telegram и добавьте в .env файл:\n"
            "BOT_TOKEN=ваш_токен_бота"
        )
        return

    logger.info(f"Конфигурация загружена. Project ID: {settings.google_cloud_project_id}")

    # Инициализируем сервисы
    storage_service = CloudStorageService(settings)
    try_on_service = VertexTryOnService(settings)

    # Создаем бота и диспетчер
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Создаем обертки для хендлеров с зависимостями
    async def model_photo_handler(message: Message, state: FSMContext) -> None:
        """Обертка для обработчика фото модели."""
        await handle_model_photo(message, state, bot, storage_service)
    
    async def garment_photo_handler(message: Message, state: FSMContext) -> None:
        """Обертка для обработчика фото одежды."""
        await handle_garment_photo(message, state, bot, storage_service, try_on_service)
    
    # Регистрируем хендлеры
    dp.message.register(start_command, Command("start"))
    
    # Хендлер фото в состоянии waiting_for_model
    dp.message.register(
        model_photo_handler,
        F.photo,
        GenStates.waiting_for_model,
    )
    
    # Хендлер фото в состоянии waiting_for_garment
    dp.message.register(
        garment_photo_handler,
        F.photo,
        GenStates.waiting_for_garment,
    )
    
    # Хендлер для всех остальных сообщений
    dp.message.register(handle_unknown_message)

    try:
        logger.info("Проверка подключения к Telegram API...")
        # Проверяем подключение перед запуском polling
        me = await bot.get_me()
        logger.success(f"Бот успешно подключен: @{me.username} ({me.first_name})")
        logger.info("Бот запущен и готов к работе")
        await dp.start_polling(bot)
    except TelegramUnauthorizedError:
        logger.error(
            "Ошибка авторизации: неверный токен бота\n"
            "Проверьте BOT_TOKEN в файле .env:\n"
            "1. Получите новый токен у @BotFather в Telegram\n"
            "2. Убедитесь, что токен скопирован полностью без пробелов\n"
            "3. Формат в .env: BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        )
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        logger.exception(e)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
