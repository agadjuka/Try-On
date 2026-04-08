"""Клавиатуры для пользовательского интерфейса."""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
    builder.button(
        text=get_text("menu_feedback", lang),
        callback_data="open_feedback",
    )
    builder.button(
        text=get_text("switch_language", lang),
        callback_data="switch_language"
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
            nav_row.append((get_text("nav_prev", lang), f"model_prev_{current_index}"))
        if current_index < total_count - 1:
            nav_row.append((get_text("nav_next", lang), f"model_next_{current_index}"))
    
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
            text=get_text("photo_number", lang).format(number=idx + 1),
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
        text=get_text("add_new_photo", lang),
        callback_data="add_new_model_from_list",
    )
    
    # Кнопки удаления для каждого фото
    for idx, model in enumerate(models):
        builder.button(
            text=get_text("delete_photo_number", lang).format(number=idx + 1),
            callback_data=f"model_delete_{model.id}",
        )
    
    # Кнопка "Назад"
    builder.button(
        text=get_text("back", lang),
        callback_data="back_to_menu",
    )
    
    builder.adjust(1)  # По одной кнопке в ряд
    return builder.as_markup()


def get_try_on_result_keyboard(
    lang: str = "ru",
    photo_count: int = 1,
    download_menu_open: bool = False,
) -> InlineKeyboardMarkup:
    """
    Получить клавиатуру для результата примерки.
    Кнопка "Новая примерка" сверху, кнопка "Скачать в высоком качестве" на втором месте,
    остальные кнопки главного меню ниже.

    Args:
        lang: Язык интерфейса
        photo_count: Количество обработанных фото (1-5)
        download_menu_open: Открыто ли меню скачивания

    Returns:
        Inline клавиатура с результатом примерки
    """
    # Создаем клавиатуру через явные ряды для правильного расположения
    keyboard = []
    
    # Ряд 1: Кнопка "Новая примерка"
    keyboard.append([
        InlineKeyboardButton(
            text=get_text("new_try_on", lang),
            callback_data="new_try_on",
        )
    ])
    
    # Ряд 2: Кнопка "Скачать в высоком качестве"
    if photo_count > 1:
        keyboard.append([
            InlineKeyboardButton(
                text=get_text("download_hq", lang),
                callback_data="toggle_download_menu",
            )
        ])
        
        # Если меню открыто, добавляем кнопки для каждого фото
        if download_menu_open:
            if photo_count == 2:
                # 2 фото - по одной в ряду
                keyboard.append([
                    InlineKeyboardButton(
                        text=get_text("photo_number", lang).format(number=1),
                        callback_data="download_photo_1",
                    )
                ])
                keyboard.append([
                    InlineKeyboardButton(
                        text=get_text("photo_number", lang).format(number=2),
                        callback_data="download_photo_2",
                    )
                ])
            elif photo_count == 3:
                # 3 фото - в одном ряду
                keyboard.append([
                    InlineKeyboardButton(
                        text=get_text("photo_number", lang).format(number=1),
                        callback_data="download_photo_1",
                    ),
                    InlineKeyboardButton(
                        text=get_text("photo_number", lang).format(number=2),
                        callback_data="download_photo_2",
                    ),
                    InlineKeyboardButton(
                        text=get_text("photo_number", lang).format(number=3),
                        callback_data="download_photo_3",
                    ),
                ])
            elif photo_count == 4:
                # 4 фото - 2 ряда по 2 кнопки
                keyboard.append([
                    InlineKeyboardButton(
                        text=get_text("photo_number", lang).format(number=1),
                        callback_data="download_photo_1",
                    ),
                    InlineKeyboardButton(
                        text=get_text("photo_number", lang).format(number=2),
                        callback_data="download_photo_2",
                    ),
                ])
                keyboard.append([
                    InlineKeyboardButton(
                        text=get_text("photo_number", lang).format(number=3),
                        callback_data="download_photo_3",
                    ),
                    InlineKeyboardButton(
                        text=get_text("photo_number", lang).format(number=4),
                        callback_data="download_photo_4",
                    ),
                ])
            elif photo_count == 5:
                # 5 фото - 2 ряда (3 + 2)
                keyboard.append([
                    InlineKeyboardButton(
                        text=get_text("photo_number", lang).format(number=1),
                        callback_data="download_photo_1",
                    ),
                    InlineKeyboardButton(
                        text=get_text("photo_number", lang).format(number=2),
                        callback_data="download_photo_2",
                    ),
                    InlineKeyboardButton(
                        text=get_text("photo_number", lang).format(number=3),
                        callback_data="download_photo_3",
                    ),
                ])
                keyboard.append([
                    InlineKeyboardButton(
                        text=get_text("photo_number", lang).format(number=4),
                        callback_data="download_photo_4",
                    ),
                    InlineKeyboardButton(
                        text=get_text("photo_number", lang).format(number=5),
                        callback_data="download_photo_5",
                    ),
                ])
    else:
        # Для одного фото - просто кнопка (пока не рабочая)
        keyboard.append([
            InlineKeyboardButton(
                text=get_text("download_hq", lang),
                callback_data="download_photo_single",
            )
        ])
    
    # Остальные кнопки главного меню - каждая в отдельном ряду
    keyboard.append([
        InlineKeyboardButton(
            text=get_text("menu_add_model", lang),
            callback_data="add_model"
        )
    ])
    keyboard.append([
        InlineKeyboardButton(
            text=get_text("menu_my_models", lang),
            callback_data="my_models"
        )
    ])
    keyboard.append([
        InlineKeyboardButton(
            text=get_text("menu_feedback", lang),
            callback_data="open_feedback",
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_feedback_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура меню отзыва."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("feedback_cancel", lang),
        callback_data="cancel_feedback",
    )
    return builder.as_markup()


def get_privacy_consent_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Клавиатура: согласие с условиями и ссылка на политику конфиденциальности.

    Args:
        lang: Язык интерфейса ('ru' или 'en')

    Returns:
        Inline-клавиатура
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("privacy_consent_agree", lang),
        callback_data="privacy_consent_accept",
    )
    builder.button(
        text=get_text("privacy_policy_button", lang),
        url=get_text("privacy_policy_url", lang),
    )
    builder.adjust(1)
    return builder.as_markup()


def get_language_selection_keyboard() -> InlineKeyboardMarkup:
    """
    Получить клавиатуру для выбора языка.

    Returns:
        Inline клавиатура с кнопками выбора языка
    """
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="🇬🇧 English",
        callback_data="select_language_en"
    )
    builder.button(
        text="🇷🇺 Русский",
        callback_data="select_language_ru"
    )
    
    builder.adjust(1)  # По одной кнопке в ряд
    return builder.as_markup()