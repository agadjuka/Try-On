"""Фоновая обработка задачи виртуальной примерки через API.

Поток:
  1. Загружаем фото модели в GCS (временная папка api_uploads/).
  2. Параллельно запускаем try-on для каждого фото одежды (до 5 штук).
  3. Сохраняем каждый результат в GCS (папка api_results/).
  4. Обновляем статус задачи в Firestore.
  5. Удаляем временное фото модели.
  6. Через 1 час удаляем результаты из GCS (best-effort).
"""
import asyncio
from typing import Optional

from bot.api.task_repo import RESULT_TTL_HOURS

from loguru import logger

from bot.api.task_repo import ApiTaskRepo
from bot.services.container import ServiceContainer


async def _process_single_garment(
    task_id: str,
    index: int,
    person_gcs_uri: str,
    garment_bytes: bytes,
) -> Optional[str]:
    """Обработать одно фото одежды. Возвращает GCS URI результата или None."""
    container = ServiceContainer.get()
    try:
        result_bytes = await container.try_on_service.generate_try_on(
            person_gcs_uri=person_gcs_uri,
            garment_bytes=garment_bytes,
        )
        path = f"api_results/{task_id}/{index}.png"
        gcs_uri = await container.storage_service.upload_image(result_bytes, path)
        logger.info(f"[{task_id}] Результат #{index} сохранён: {gcs_uri}")
        return gcs_uri
    except Exception as e:
        logger.error(f"[{task_id}] Ошибка обработки гармента #{index}: {e}")
        return None


async def _cleanup_model(model_uri: str) -> None:
    """Удалить временное фото модели из GCS."""
    try:
        await ServiceContainer.get().storage_service.delete_file(model_uri)
    except Exception as e:
        logger.warning(f"Не удалось удалить временное фото модели ({model_uri}): {e}")


async def _cleanup_results_after_ttl(task_id: str, result_uris: list[str]) -> None:
    """Удалить GCS-файлы результатов по истечении TTL (best-effort)."""
    delay = RESULT_TTL_HOURS * 3600
    await asyncio.sleep(delay)
    storage = ServiceContainer.get().storage_service
    for uri in result_uris:
        try:
            await storage.delete_file(uri)
        except Exception as e:
            logger.warning(f"[{task_id}] Не удалось удалить результат ({uri}): {e}")
    logger.info(f"[{task_id}] GCS-результаты удалены после {RESULT_TTL_HOURS}ч TTL")


async def process_try_on_task(
    task_id: str,
    model_bytes: bytes,
    garments_bytes: list[bytes],
    repo: ApiTaskRepo,
) -> None:
    """Полный цикл обработки задачи примерки (запускается как фоновая задача)."""
    container = ServiceContainer.get()

    try:
        model_path = f"api_uploads/{task_id}/model.png"
        person_gcs_uri = await container.storage_service.upload_image(model_bytes, model_path)
        await repo.set_processing(task_id, person_gcs_uri)
        logger.info(f"[{task_id}] Модель загружена: {person_gcs_uri}, гарментов: {len(garments_bytes)}")

        coros = [
            _process_single_garment(task_id, i, person_gcs_uri, garment_bytes)
            for i, garment_bytes in enumerate(garments_bytes)
        ]
        raw_results = await asyncio.gather(*coros)

        result_uris = [uri for uri in raw_results if uri is not None]

        if not result_uris:
            await repo.set_failed(task_id, "Все попытки обработки завершились ошибкой")
        else:
            await repo.set_completed(task_id, result_uris)
            asyncio.create_task(_cleanup_results_after_ttl(task_id, result_uris))

        await _cleanup_model(person_gcs_uri)

    except Exception as e:
        logger.exception(f"[{task_id}] Критическая ошибка: {e}")
        await repo.set_failed(task_id, str(e))
