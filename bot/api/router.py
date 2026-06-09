"""FastAPI роутер REST API виртуальной примерки.

Эндпоинты:
  POST /api/v1/try-on              — принять задачу, вернуть task_id
  GET  /api/v1/try-on/{task_id}   — проверить статус, получить публичные ссылки
  GET  /api/v1/results/{task_id}/{index} — скачать результат (без авторизации)
"""
import asyncio
from datetime import datetime
from typing import Optional

import requests as http_client
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from loguru import logger

from bot.api.auth import get_api_task_repo, verify_api_key
from bot.api.schemas import TaskStatus, TryOnStatusResponse, TryOnSubmitResponse
from bot.api.task_service import process_try_on_task
from bot.database.repo_factory import ApiTaskRepository
from bot.services.container import ServiceContainer

router = APIRouter(prefix="/api/v1", tags=["Virtual Try-On API"])

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 МБ


# ─── Вспомогательные функции ─────────────────────────────────────────────────

def _check_not_expired(task: dict) -> None:
    expires_at = task.get("expires_at")
    if expires_at is None:
        return
    expiry = expires_at.replace(tzinfo=None) if hasattr(expires_at, "tzinfo") and expires_at.tzinfo else expires_at
    if datetime.utcnow() > expiry:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Результаты удалены (срок хранения 1 час истёк)",
        )


async def _read_upload(file: UploadFile, label: str) -> bytes:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Файл '{label}' пустой")
    if len(data) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"Файл '{label}' превышает 10 МБ")
    return data


async def _fetch_url(url: str, label: str) -> bytes:
    """Скачать изображение одежды по URL (выполняется в отдельном потоке)."""
    def _download() -> bytes:
        resp = http_client.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content

    try:
        return await asyncio.to_thread(_download)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Не удалось скачать '{label}' по URL ({url}): {e}",
        )


async def _resolve_garment(
    file: Optional[UploadFile],
    url: Optional[str],
    label: str,
    required: bool = False,
) -> Optional[bytes]:
    """Вернуть байты гармента: из файла, из URL или None."""
    if file is not None:
        return await _read_upload(file, label)
    if url:
        return await _fetch_url(url, label)
    if required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Укажи файл или URL для {label}",
        )
    return None


# ─── Эндпоинты ───────────────────────────────────────────────────────────────

@router.post(
    "/try-on",
    response_model=TryOnSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Создать задачу примерки",
)
async def submit_try_on(
    background_tasks: BackgroundTasks,
    # Фото модели — всегда файл (грузит пользователь с телефона)
    model: UploadFile = File(..., description="Фото модели (человека)"),
    # Одежда #1 — файл или URL (обязательно хотя бы одно)
    garment_1: Optional[UploadFile] = File(default=None, description="Фото одежды #1 (файл)"),
    garment_url_1: Optional[str] = Form(default=None, description="Фото одежды #1 (URL)"),
    # Одежда #2-5 — файл или URL (опционально)
    garment_2: Optional[UploadFile] = File(default=None, description="Фото одежды #2 (файл)"),
    garment_url_2: Optional[str] = Form(default=None, description="Фото одежды #2 (URL)"),
    garment_3: Optional[UploadFile] = File(default=None, description="Фото одежды #3 (файл)"),
    garment_url_3: Optional[str] = Form(default=None, description="Фото одежды #3 (URL)"),
    garment_4: Optional[UploadFile] = File(default=None, description="Фото одежды #4 (файл)"),
    garment_url_4: Optional[str] = Form(default=None, description="Фото одежды #4 (URL)"),
    garment_5: Optional[UploadFile] = File(default=None, description="Фото одежды #5 (файл)"),
    garment_url_5: Optional[str] = Form(default=None, description="Фото одежды #5 (URL)"),
    _key: str = Depends(verify_api_key),
    repo: ApiTaskRepository = Depends(get_api_task_repo),
) -> TryOnSubmitResponse:
    """Принять фото модели и одежды, запустить обработку в фоне.

    Одежду можно передать файлом (`garment_N`) **или** ссылкой (`garment_url_N`).
    Если переданы оба — используется файл.
    """
    model_bytes = await _read_upload(model, "model")

    slots = [
        (garment_1, garment_url_1, "garment_1", True),
        (garment_2, garment_url_2, "garment_2", False),
        (garment_3, garment_url_3, "garment_3", False),
        (garment_4, garment_url_4, "garment_4", False),
        (garment_5, garment_url_5, "garment_5", False),
    ]
    garments_bytes = [
        b for b in [
            await _resolve_garment(f, u, label, required)
            for f, u, label, required in slots
        ]
        if b is not None
    ]

    task_id = await repo.create_task(len(garments_bytes))

    background_tasks.add_task(
        process_try_on_task,
        task_id=task_id,
        model_bytes=model_bytes,
        garments_bytes=garments_bytes,
        repo=repo,
    )

    logger.info(f"Принята задача {task_id}: {len(garments_bytes)} гарментов")
    task = await repo.get_task(task_id)
    return TryOnSubmitResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        created_at=task["created_at"],
    )


@router.get(
    "/try-on/{task_id}",
    response_model=TryOnStatusResponse,
    summary="Проверить статус задачи",
)
async def get_try_on_status(
    task_id: str,
    request: Request,
    _key: str = Depends(verify_api_key),
    repo: ApiTaskRepository = Depends(get_api_task_repo),
) -> TryOnStatusResponse:
    """Опросить статус задачи примерки.

    Когда `status=completed`, поле `results` содержит **публичные** URL —
    их можно сразу вставлять в `<img src="...">` без авторизации.
    Рекомендуемый интервал опроса — 3–5 секунд.
    """
    task = await repo.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")

    _check_not_expired(task)

    results: list[str] = []
    if task.get("status") == TaskStatus.COMPLETED.value:
        base = str(request.base_url).rstrip("/")
        result_uris: list[str] = task.get("result_uris", [])
        # Публичные URL — авторизация не нужна (task_id — UUID, неугадываемый)
        results = [f"{base}/api/v1/results/{task_id}/{i}" for i in range(len(result_uris))]

    return TryOnStatusResponse(
        task_id=task_id,
        status=TaskStatus(task["status"]),
        created_at=task["created_at"],
        completed_at=task.get("completed_at"),
        results=results,
        error=task.get("error"),
    )


@router.get(
    "/results/{task_id}/{index}",
    summary="Скачать результат примерки (публичный, без авторизации)",
    response_class=Response,
)
async def download_result(
    task_id: str,
    index: int,
    repo: ApiTaskRepository = Depends(get_api_task_repo),
) -> Response:
    """Вернуть PNG-файл результата.

    Авторизация не требуется — task_id является UUID и служит одноразовым токеном.
    Файл доступен 1 час после завершения задачи.
    """
    task = await repo.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")

    _check_not_expired(task)

    if task.get("status") != TaskStatus.COMPLETED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Результаты ещё не готовы")

    result_uris: list[str] = task.get("result_uris", [])
    if index < 0 or index >= len(result_uris):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Нет результата с индексом {index}")

    container = ServiceContainer.get()
    image_bytes = await container.storage_service.download_file(result_uris[index])

    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="result_{task_id}_{index}.png"',
            "Cache-Control": "public, max-age=3600",
        },
    )
