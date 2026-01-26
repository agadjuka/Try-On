"""Локализация текстов бота."""

TEXTS = {
    "welcome": {
        "ru": "👋 Привет! Я бот для виртуальной примерки одежды.\n\nВыбери действие:",
        "en": "👋 Hello! I'm a virtual try-on bot.\n\nChoose an action:",
    },
    "menu_add_model": {
        "ru": "➕ Добавить модель",
        "en": "➕ Add Model",
    },
    "menu_my_models": {
        "ru": "👤 Мои модели",
        "en": "👤 My Models",
    },
    "menu_try_on": {
        "ru": "👔 Примерка",
        "en": "👔 Try On",
    },
    "new_try_on": {
        "ru": "🔄 Новая примерка",
        "en": "🔄 New Try On",
    },
    "menu_settings": {
        "ru": "⚙️ Настройки",
        "en": "⚙️ Settings",
    },
    "upload_model_instr": {
        "ru": "📸 Отправь фото модели (человека).\n\nФото должно быть четким, с хорошим освещением.",
        "en": "📸 Send a photo of the model (person).\n\nThe photo should be clear with good lighting.",
    },
    "model_saved": {
        "ru": "✅ Модель успешно сохранена!",
        "en": "✅ Model saved successfully!",
    },
    "model_upload_error": {
        "ru": "❌ Ошибка при загрузке модели. Попробуй еще раз.",
        "en": "❌ Error uploading model. Please try again.",
    },
    "models_list_empty": {
        "ru": "📭 Список моделей пуст.\n\nДобавь первую модель через меню.",
        "en": "📭 Models list is empty.\n\nAdd your first model from the menu.",
    },
    "model_deleted": {
        "ru": "🗑 Модель удалена.",
        "en": "🗑 Model deleted.",
    },
    "model_set_active": {
        "ru": "✅ Модель выбрана как активная.",
        "en": "✅ Model set as active.",
    },
    "delete_error": {
        "ru": "❌ Ошибка при удалении модели.",
        "en": "❌ Error deleting model.",
    },
    "set_active_error": {
        "ru": "❌ Ошибка при выборе модели.",
        "en": "❌ Error setting active model.",
    },
    "back": {
        "ru": "🔙 Назад",
        "en": "🔙 Back",
    },
    "delete": {
        "ru": "🗑 Удалить",
        "en": "🗑 Delete",
    },
    "select": {
        "ru": "✅ Выбрать",
        "en": "✅ Select",
    },
    "try_on_instr": {
        "ru": "📸 Отправь фото одежды для примерки.\n\nИспользуется активная модель.",
        "en": "📸 Send a photo of clothing for try-on.\n\nUsing active model.",
    },
    "processing": {
        "ru": "⏳ Сохраняю...",
        "en": "⏳ Saving...",
    },
    "try_on_success": {
        "ru": "✅ Примерка готова!",
        "en": "✅ Try-on ready!",
    },
    "try_on_error": {
        "ru": "❌ Ошибка при генерации примерки.",
        "en": "❌ Error generating try-on.",
    },
    "no_active_model": {
        "ru": "⚠️ У тебя нет активной модели.\n\nДобавь модель через меню.",
        "en": "⚠️ You don't have an active model.\n\nAdd a model from the menu.",
    },
    "unknown_message": {
        "ru": "Не понимаю. Используй кнопки меню.",
        "en": "I don't understand. Use menu buttons.",
    },
    "try_on_select_model_or_photo": {
        "ru": "👤 Выберите модель для примерки или пришлите ваше фото:",
        "en": "👤 Choose a model for try-on or send your photo:",
    },
    "try_on_send_photo": {
        "ru": "📸 Пришлите ваше фото для примерки:",
        "en": "📸 Send your photo for try-on:",
    },
}


def get_text(key: str, lang: str = "ru") -> str:
    """
    Получить текст по ключу и языку.

    Args:
        key: Ключ текста
        lang: Язык ('ru' или 'en')

    Returns:
        Текст на указанном языке или на русском, если язык не найден
    """
    if key not in TEXTS:
        return f"[{key}]"
    
    text_dict = TEXTS[key]
    return text_dict.get(lang, text_dict.get("ru", f"[{key}]"))
