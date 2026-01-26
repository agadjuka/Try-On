"""Клавиатуры для пользовательского интерфейса."""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

from bot.locales.texts import get_text


def get_main_menu_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Получить главное меню.

    Args:
        lang: Язык интерфейса

    Returns:
        Inline клавиатура с главным меню
    """
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text=get_text("menu_add_model", lang),
        callback_data="add_model"
    )
    builder.button(
        text=get_text("menu_my_models", lang),
        callback_data="my_models"
    )
    builder.button(
        text=get_text("menu_try_on", lang),
        callback_data="try_on"
    )
    builder.button(
        text=get_text("menu_settings", lang),
        callback_data="settings"
    )
    
    builder.adjust(1)  # По одной кнопке в ряд
    return builder.as_markup()


def get_gallery_keyboard(
    current_index: int,
    total_count: int,
    model_id: str,
    is_active: bool,
    lang: str = "ru"
) -> InlineKeyboardMarkup:
    """
    Получить клавиатуру для галереи моделей.

    Args:
        current_index: Текущий индекс (0-based)
        total_count: Общее количество моделей
        model_id: ID текущей модели
        is_active: Активна ли текущая модель
        lang: Язык интерфейса

    Returns:
        Inline клавиатура для галереи
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопки навигации
    nav_row = []
    if total_count > 1:
        if current_index > 0:
            nav_row.append(("◀️", f"model_prev_{current_index}"))
        if current_index < total_count - 1:
            nav_row.append(("▶️", f"model_next_{current_index}"))
    
    for text, callback_data in nav_row:
        builder.button(text=text, callback_data=callback_data)
    
    # Кнопки управления
    if nav_row:
        builder.adjust(len(nav_row))
    
    builder.button(
        text=get_text("select", lang) if not is_active else "✅ Активна",
        callback_data=f"model_select_{model_id}",
    )
    builder.button(
        text=get_text("delete", lang),
        callback_data=f"model_delete_{model_id}",
    )
    builder.button(
        text=get_text("back", lang),
        callback_data="back_to_menu",
    )
    
    builder.adjust(1)  # По одной кнопке в ряд
    return builder.as_markup()


def get_back_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Получить клавиатуру только с кнопкой "Назад".

    Args:
        lang: Язык интерфейса

    Returns:
        Inline клавиатура с кнопкой "Назад"
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("back", lang),
        callback_data="back_to_menu",
    )
    return builder.as_markup()
