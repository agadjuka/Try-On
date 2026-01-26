"""Утилиты для работы с фотографиями."""

from typing import Optional

from aiogram import Bot
from aiogram.types import PhotoSize


async def get_largest_photo(photos: list[PhotoSize]) -> Optional[PhotoSize]:
    """
    Получить фото с максимальным размером.

    Args:
        photos: Список размеров фото

    Returns:
        Фото с максимальным размером или None
    """
    if not photos:
        return None
    return photos[-1]


async def download_photo_to_bytes(bot: Bot, photo: PhotoSize) -> bytes:
    """
    Скачать фото в байты.

    Args:
        bot: Экземпляр бота
        photo: Объект фото

    Returns:
        Байты фото

    Raises:
        Exception: Если не удалось получить file_path или скачать файл
    """
    file = await bot.get_file(photo.file_id)
    
    if not file.file_path:
        raise Exception(f"Не удалось получить file_path для файла {photo.file_id}")
    
    file_io = await bot.download_file(file.file_path)
    file_bytes = file_io.read()
    file_io.close()
    
    return file_bytes
