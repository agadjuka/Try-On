"""Скрипт для проверки соединений с Google Cloud сервисами и тестирования Try-On API."""

import asyncio

from bot.core.config import get_settings
from bot.core.logger import setup_logger
from bot.database.repo import FirestoreRepo
from bot.services.storage import CloudStorageService
from bot.services.try_on import VertexTryOnService
from loguru import logger


async def main() -> None:
    """Основная функция проверки соединений и тестирования Try-On."""
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

        # Тестирование Try-On сервиса
        logger.info("\n" + "="*60)
        logger.info("Тестирование Vertex AI Try-On сервиса...")
        logger.info("="*60)

        # Тестовые GCS URI (замените на реальные ссылки на ваши изображения)
        person_gcs_uri = "gs://your-bucket-name/path/to/person/image.jpg"
        garment_gcs_uri = "gs://your-bucket-name/path/to/garment/image.jpg"

        logger.warning(
            f"ВНИМАНИЕ: Используются тестовые GCS URI.\n"
            f"Person: {person_gcs_uri}\n"
            f"Garment: {garment_gcs_uri}\n"
            f"Замените их на реальные ссылки перед запуском!"
        )

        try:
            try_on_service = VertexTryOnService(settings)
            result_uri = await try_on_service.generate_try_on(
                person_gcs_uri=person_gcs_uri,
                garment_gcs_uri=garment_gcs_uri,
                storage_service=storage_service,
            )
            logger.success(f"Try-On генерация завершена успешно!")
            logger.success(f"Результат сохранен: {result_uri}")
        except Exception as e:
            logger.error(f"Ошибка при генерации Try-On: {str(e)}")
            logger.exception(e)

    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
        raise
    finally:
        # Закрываем соединения
        if "firestore_repo" in locals():
            await firestore_repo.close()


if __name__ == "__main__":
    asyncio.run(main())
