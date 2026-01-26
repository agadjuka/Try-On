"""Модуль для обработки изображений."""

import base64
from pathlib import Path
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Класс для обработки изображений."""
    
    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    
    @classmethod
    def is_image_file(cls, file_path: Path) -> bool:
        """Проверяет, является ли файл изображением."""
        return file_path.suffix.lower() in cls.SUPPORTED_FORMATS
    
    @classmethod
    def load_images_from_folder(cls, folder_path: Path) -> List[Path]:
        """
        Загружает список путей к изображениям из папки.
        
        Args:
            folder_path: Путь к папке с изображениями
            
        Returns:
            Список путей к изображениям
        """
        if not folder_path.exists():
            logger.warning(f"Папка {folder_path} не существует")
            return []
        
        images = [
            img_path
            for img_path in folder_path.iterdir()
            if img_path.is_file() and cls.is_image_file(img_path)
        ]
        
        return sorted(images)
    
    @classmethod
    def encode_image_to_base64(cls, image_path: Path) -> str:
        """
        Кодирует изображение в base64.
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            Base64-encoded строка изображения
        """
        try:
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                encoded = base64.b64encode(image_data).decode("utf-8")
                logger.debug(f"Изображение {image_path.name} закодировано ({len(encoded)} символов)")
                return encoded
        except Exception as e:
            logger.error(f"Ошибка при кодировании {image_path}: {e}")
            raise
    
    @classmethod
    def decode_base64_to_image(cls, base64_string: str, output_path: Path) -> None:
        """
        Декодирует base64 строку в изображение и сохраняет.
        
        Args:
            base64_string: Base64-encoded строка
            output_path: Путь для сохранения изображения
        """
        try:
            image_data = base64.b64decode(base64_string)
            with open(output_path, "wb") as image_file:
                image_file.write(image_data)
            logger.debug(f"Изображение сохранено: {output_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении изображения {output_path}: {e}")
            raise
    
    @classmethod
    def create_image_pairs(
        cls,
        person_images: List[Path],
        product_images: List[Path]
    ) -> List[Tuple[Path, Path]]:
        """
        Создает пары изображений (модель + одежда).
        
        Args:
            person_images: Список изображений моделей
            product_images: Список изображений одежды
            
        Returns:
            Список кортежей (person_image, product_image)
        """
        pairs = []
        
        if not person_images:
            logger.warning("Не найдено изображений моделей")
            return pairs
        
        if not product_images:
            logger.warning("Не найдено изображений одежды")
            return pairs
        
        # Если по одному изображению каждого типа - создаем одну пару
        if len(person_images) == 1 and len(product_images) == 1:
            pairs.append((person_images[0], product_images[0]))
        else:
            # Создаем все возможные комбинации
            for person_img in person_images:
                for product_img in product_images:
                    pairs.append((person_img, product_img))
        
        logger.info(f"Создано {len(pairs)} пар изображений")
        return pairs
