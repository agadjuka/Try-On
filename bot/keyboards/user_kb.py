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
        text=get_text("menu_try_on", lang),
        callback_data="try_on"
    )
    builder.button(
        text=get_text("menu_add_model", lang),
        callback_data="add_model"
    )
    builder.button(
        text=get_text("menu_my_models", lang),
        callback_data="my_models"
    )
    
    builder.adjust(1)  # По одной кнопке в ряд
    return builder.as_markup()


def get_gallery_keyboard(
    current_index: int,
    total_count: int,
    model_id: str,
    lang: str = "ru"
) -> InlineKeyboardMarkup:
    """
    Получить клавиатуру для галереи моделей.

    Args:
        current_index: Текущий индекс (0-based)
        total_count: Общее количество моделей
        model_id: ID текущей модели
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
        text=get_text("delete", lang),
        callback_data=f"model_delete_{model_id}",
    )
    builder.button(
        text=get_text("back", lang),
        callback_data="back_to_menu",
    )
    
    builder.adjust(1)  # По одной кнопке в ряд
    return builder.as_markup()


def get_model_selection_keyboard(
    models: list,
    lang: str = "ru",
) -> InlineKeyboardMarkup:
    """
    Получить клавиатуру для выбора модели при примерке.

    Args:
        models: Список моделей
        lang: Язык интерфейса

    Returns:
        Inline клавиатура с кнопками выбора модели
    """
    builder = InlineKeyboardBuilder()
    
    for idx, model in enumerate(models):
        builder.button(
            text=f"Фото {idx + 1}",
            callback_data=f"try_on_select_model_{model.id}",
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


def get_models_list_keyboard(
    models: list,
    lang: str = "ru"
) -> InlineKeyboardMarkup:
    """
    Получить клавиатуру для списка моделей.

    Args:
        models: Список моделей
        lang: Язык интерфейса

    Returns:
        Inline клавиатура с кнопками управления моделями
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопка "Добавить новое фото"
    builder.button(
        text="➕ Добавить новое фото",
        callback_data="add_new_model_from_list",
    )
    
    # Кнопки удаления для каждого фото
    for idx, model in enumerate(models):
        builder.button(
            text=f"🗑 Удалить фото {idx + 1}",
            callback_data=f"model_delete_{model.id}",
        )
    
    # Кнопка "Назад"
    builder.button(
        text=get_text("back", lang),
        callback_data="back_to_menu",
    )
    
    builder.adjust(1)  # По одной кнопке в ряд
    return builder.as_markup()


def get_try_on_result_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Получить клавиатуру для результата примерки.
    Кнопка "Новая примерка" сверху, остальные кнопки главного меню ниже.

    Args:
        lang: Язык интерфейса

    Returns:
        Inline клавиатура с результатом примерки
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопка "Новая примерка" сверху
    builder.button(
        text=get_text("new_try_on", lang),
        callback_data="new_try_on",
    )
    
    # Остальные кнопки главного меню
    builder.button(
        text=get_text("menu_add_model", lang),
        callback_data="add_model"
    )
    builder.button(
        text=get_text("menu_my_models", lang),
        callback_data="my_models"
    )
    
    builder.adjust(1)  # По одной кнопке в ряд
    return builder.as_markup()
