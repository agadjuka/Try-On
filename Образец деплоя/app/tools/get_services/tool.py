"""
Инструмент GetServices для получения списка услуг категории
"""
import json
import logging
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from app.tools.shared.services_data_loader import _data_loader

logger = logging.getLogger(__name__)


class GetServicesInput(BaseModel):
    """Входные параметры для GetServices"""
    category_id: str = Field(
        description="ID категории (строка). Доступные категории: '1' - Маникюр, '2' - Педикюр, '3' - Услуги для мужчин, '4' - Брови, '5' - Ресницы, '6' - Макияж, '7' - Парикмахерские услуги, '8' - Пирсинг, '9' - Лазерная эпиляция, '10' - Косметология, '11' - Депиляция, '12' - Массаж, '13' - LOOKTOWN SPA."
    )


@tool(args_schema=GetServicesInput)
def get_services_tool(category_id: str) -> str:
    """
    Получить список услуг указанной категории с ценами и ID услуг.
    Используй когда клиент спрашивает "какие виды маникюра?" или "что есть в категории массаж?"
    """
    try:
        data = _data_loader.load_data()
        
        if not data:
            return "Данные об услугах не найдены"
        
        # Получаем категорию по ID
        category = data.get(category_id)
        if not category:
            available_ids = ", ".join(sorted(data.keys(), key=int))
            return (
                f"Категория с ID '{category_id}' не найдена.\n"
                f"Доступные ID категорий: {available_ids}\n"
                f"Используйте GetCategories для получения полного списка категорий."
            )
        
        category_name = category.get('category_name', 'Неизвестно')
        services = category.get('services', [])
        
        if not services:
            return f"В категории '{category_name}' нет доступных услуг"
        
        # Форматируем услуги
        result_lines = [f"Услуги категории '{category_name}':\n"]
        
        for service in services:
            name = service.get('name', 'Неизвестно')
            price = service.get('prices', 'Не указана')
            master_level = service.get('master_level')
            service_id = service.get('id', 'Не указан')
            
            service_line = f"  • {name} (ID: {service_id}) - {price} руб."
            if master_level:
                service_line += f" ({master_level})"
            
            result_lines.append(service_line)
        
        result_lines.append("\nНЕ ВСТАВЛЯЙ НИКАКИЕ ID В СООБЩЕНИЯ КЛИЕНТУ")
        return "\n".join(result_lines)
        
    except FileNotFoundError as e:
        logger.error(f"Файл с услугами не найден: {e}")
        return "Файл с данными об услугах не найден"
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}")
        return "Ошибка при чтении данных об услугах"
    except Exception as e:
        logger.error(f"Ошибка при получении услуг: {e}")
        return f"Ошибка при получении услуг: {str(e)}"

