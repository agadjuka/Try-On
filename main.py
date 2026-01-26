"""Скрипт для проверки соединений с Google Cloud сервисами."""

import asyncio

from bot.core.config import get_settings
from bot.core.logger import setup_logger
from bot.database.repo import FirestoreRepo
from bot.services.storage import CloudStorageService
from loguru import logger


async def main() -> None:
    """Основная функция проверки соединений."""
    setup_logger()
    logger.info("Запуск проверки соединений с Google Cloud сервисами...")

    try:
        # Загрузка конфигурации
        settings = get_settings()
        logger.info(f"Конфигурация загружена. Project ID: {settings.google_cloud_project_id}")

        # Проверка подключения к Firestore
        logger.info("Проверка подключения к Firestore...")
        firestore_repo = FirestoreRepo(settings)
        firestore_connected = await firestore_repo.check_connection()

        if not firestore_connected:
            logger.error("Не удалось подключиться к Firestore")
            return

        # Проверка загрузки файла в GCS
        logger.info("Проверка загрузки файла в Google Cloud Storage...")
        storage_service = CloudStorageService(settings)

        test_content = b"Test file for connection check"
        test_path = "test/connection_check.txt"

        try:
            gs_uri = await storage_service.upload_file(
                file_bytes=test_content,
                destination_path=test_path,
                content_type="text/plain",
            )
            logger.success(f"Файл успешно загружен: {gs_uri}")
        except Exception as e:
            logger.error(f"Ошибка загрузки файла в GCS: {str(e)}")
            return

        logger.success("Все проверки пройдены успешно!")

    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
        raise
    finally:
        # Закрываем соединения
        if "firestore_repo" in locals():
            await firestore_repo.close()


if __name__ == "__main__":
    asyncio.run(main())
