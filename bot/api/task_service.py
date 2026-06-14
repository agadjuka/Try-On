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
from datetime import datetime
from typing import Optional

import pytz
from loguru import logger

from bot.database.repo_factory import ApiTaskRepository
from bot.services.try_on import (
    SAFETY_BLOCKED_MESSAGE_EN,
    SAFETY_PARTIAL_BLOCKED_MESSAGE_EN,
    TryOnSafetyError,
)

RESULT_TTL_HOURS = 1
from bot.services.container import ServiceContainer


async def _process_single_garment(
    task_id: str,
    index: int,
    person_uri: str,
    person_image_bytes: bytes,
    garment_bytes: bytes,
) -> Optional[str | TryOnSafetyError]:
    """Обработать одно фото одежды. Возвращает GCS URI результата или None."""
    container = ServiceContainer.get()
    try:
        result_bytes = await container.try_on_service.generate_try_on(
            garment_bytes=garment_bytes,
            person_image_uri=person_uri,
            person_image_bytes=person_image_bytes,
        )
        path = f"api_results/{task_id}/{index}.png"
        gcs_uri = await container.storage_service.upload_image(result_bytes, path)
        logger.info(f"[{task_id}] Результат #{index} сохранён: {gcs_uri}")
        return gcs_uri
    except TryOnSafetyError as e:
        logger.warning(f"[{task_id}] Гармент #{index} отклонён системой безопасности: {e}")
        return e
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


async def _notify_admin_panel(
    task_id: str,
    model_bytes: bytes,
    garments_bytes: list[bytes],
    result_uris: list[str],
) -> None:
    """Отправить фото модели, одежды и результаты в Telegram-админку (best-effort)."""
    container = ServiceContainer.get()
    if container.bot is None:
        return

    from bot.admin.factory import get_admin_service
    admin_service = get_admin_service(container.bot)
    if admin_service is None:
        return

    try:
        sg_tz = pytz.timezone("Asia/Singapore")
        topic_name = datetime.now(sg_tz).strftime("%d.%m.%Y %H:%M")
        topic_id = await admin_service.create_api_topic(topic_name)
        if topic_id is None:
            return

        await admin_service.send_photos_to_topic(topic_id, [model_bytes], "Фото модели")

        if garments_bytes:
            await admin_service.send_photos_to_topic(
                topic_id,
                garments_bytes,
                f"Одежда ({len(garments_bytes)} фото)",
            )

        if result_uris:
            result_bytes_list: list[bytes] = []
            for uri in result_uris:
                try:
                    b = await container.storage_service.download_file(uri)
                    result_bytes_list.append(b)
                except Exception as e:
                    logger.warning(f"[{task_id}] Не удалось скачать результат для админки ({uri}): {e}")
            if result_bytes_list:
                await admin_service.send_photos_to_topic(
                    topic_id,
                    result_bytes_list,
                    "Результаты примерки",
                )

        logger.info(f"[{task_id}] Задача отправлена в админ-панель (топик {topic_id})")
    except Exception as e:
        logger.error(f"[{task_id}] Ошибка отправки в админ-панель: {e}")


async def process_try_on_task(
    task_id: str,
    model_bytes: bytes,
    garments_bytes: list[bytes],
    repo: ApiTaskRepository,
) -> None:
    """Полный цикл обработки задачи примерки (запускается как фоновая задача)."""
    container = ServiceContainer.get()

    try:
        model_path = f"api_uploads/{task_id}/model.png"
        person_uri = await container.storage_service.upload_image(model_bytes, model_path)
        await repo.set_processing(task_id, person_uri)
        logger.info(f"[{task_id}] Модель загружена: {person_uri}, гарментов: {len(garments_bytes)}")

        coros = [
            _process_single_garment(task_id, i, person_uri, model_bytes, garment_bytes)
            for i, garment_bytes in enumerate(garments_bytes)
        ]
        raw_results = await asyncio.gather(*coros)

        result_uris = [uri for uri in raw_results if isinstance(uri, str)]
        safety_failures = [
            result for result in raw_results if isinstance(result, TryOnSafetyError)
        ]

        if not result_uris:
            if safety_failures:
                await repo.set_failed(task_id, SAFETY_BLOCKED_MESSAGE_EN)
            else:
                await repo.set_failed(task_id, "All try-on attempts failed")
        else:
            await repo.set_completed(
                task_id,
                result_uris,
                SAFETY_PARTIAL_BLOCKED_MESSAGE_EN if safety_failures else None,
            )
            asyncio.create_task(_cleanup_results_after_ttl(task_id, result_uris))
            asyncio.create_task(_notify_admin_panel(task_id, model_bytes, garments_bytes, result_uris))

        await _cleanup_model(person_uri)

    except Exception as e:
        logger.exception(f"[{task_id}] Критическая ошибка: {e}")
        await repo.set_failed(task_id, str(e))
