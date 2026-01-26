"""Основной скрипт для Virtual Try-On."""

import logging
from pathlib import Path
from typing import List, Tuple
from datetime import datetime

from config import Config
from image_processor import ImageProcessor
from api_client import APIClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class VirtualTryOnProcessor:
    """Основной класс для обработки примерки."""
    
    def __init__(self):
        """Инициализация процессора."""
        Config.validate()
        self.image_processor = ImageProcessor()
        self.api_client = APIClient()
    
    def process_all_images(self) -> None:
        """Обрабатывает все изображения из папок."""
        logger.info("=" * 60)
        logger.info("🎨 VIRTUAL TRY-ON - ОБРАБОТКА ИЗОБРАЖЕНИЙ")
        logger.info("=" * 60)
        logger.info("")
        
        # Загружаем изображения
        person_images = self.image_processor.load_images_from_folder(
            Config.INPUT_PERSON_DIR
        )
        product_images = self.image_processor.load_images_from_folder(
            Config.INPUT_PRODUCT_DIR
        )
        
        if not person_images:
            logger.error(f"❌ Не найдено изображений моделей в {Config.INPUT_PERSON_DIR}")
            return
        
        if not product_images:
            logger.error(f"❌ Не найдено изображений одежды в {Config.INPUT_PRODUCT_DIR}")
            return
        
        logger.info(f"✅ Найдено изображений моделей: {len(person_images)}")
        logger.info(f"✅ Найдено изображений одежды: {len(product_images)}")
        logger.info("")
        
        # Создаем пары
        pairs = self.image_processor.create_image_pairs(person_images, product_images)
        
        if not pairs:
            logger.error("❌ Не удалось создать пары изображений")
            return
        
        # Обрабатываем каждую пару
        total_pairs = len(pairs)
        successful = 0
        failed = 0
        
        for idx, (person_img, product_img) in enumerate(pairs, 1):
            logger.info("")
            logger.info("-" * 60)
            logger.info(f"Обработка пары {idx}/{total_pairs}")
            logger.info(f"Модель: {person_img.name}")
            logger.info(f"Одежда: {product_img.name}")
            logger.info("-" * 60)
            
            try:
                self._process_pair(person_img, product_img, idx)
                successful += 1
                logger.info(f"✅ Пара {idx} обработана успешно")
            except Exception as e:
                failed += 1
                logger.error(f"❌ Ошибка при обработке пары {idx}: {e}")
        
        # Итоги
        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 ИТОГИ ОБРАБОТКИ")
        logger.info("=" * 60)
        logger.info(f"Всего пар: {total_pairs}")
        logger.info(f"Успешно: {successful}")
        logger.info(f"Ошибок: {failed}")
        logger.info(f"Результаты сохранены в: {Config.OUTPUT_DIR}")
        logger.info("=" * 60)
    
    def _process_pair(
        self,
        person_img: Path,
        product_img: Path,
        pair_index: int
    ) -> None:
        """
        Обрабатывает одну пару изображений.
        
        Args:
            person_img: Путь к изображению модели
            product_img: Путь к изображению одежды
            pair_index: Индекс пары
        """
        # Кодируем изображения
        logger.info("Кодирование изображений...")
        person_base64 = self.image_processor.encode_image_to_base64(person_img)
        product_base64 = self.image_processor.encode_image_to_base64(product_img)
        
        # Генерируем примерку
        predictions = self.api_client.generate_try_on(person_base64, product_base64)
        
        # Сохраняем результаты
        logger.info("Сохранение результатов...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        person_name = person_img.stem
        product_name = product_img.stem
        
        for pred_idx, prediction in enumerate(predictions, 1):
            if "bytesBase64Encoded" not in prediction:
                logger.warning(f"Пропущен результат {pred_idx}: нет данных изображения")
                continue
            
            mime_type = prediction.get("mimeType", "image/png")
            extension = ".png" if mime_type == "image/png" else ".jpg"
            
            output_filename = (
                f"{pair_index:03d}_"
                f"{person_name}_"
                f"{product_name}_"
                f"{pred_idx:02d}_"
                f"{timestamp}{extension}"
            )
            output_path = Config.OUTPUT_DIR / output_filename
            
            self.image_processor.decode_base64_to_image(
                prediction["bytesBase64Encoded"],
                output_path
            )
            logger.info(f"✅ Сохранено: {output_filename}")


def main():
    """Главная функция."""
    try:
        processor = VirtualTryOnProcessor()
        processor.process_all_images()
    except ValueError as e:
        logger.error(f"❌ Ошибка конфигурации: {e}")
        logger.info("")
        logger.info("Проверьте файл .env и убедитесь, что все необходимые")
        logger.info("переменные окружения установлены.")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)


if __name__ == "__main__":
    main()
