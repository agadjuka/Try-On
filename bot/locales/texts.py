"""Локализация текстов бота."""

TEXTS = {
    "welcome": {
        "ru": "👋 Привет! Я бот для виртуальной примерки одежды.\n\nВыбери действие:",
        "en": "👋 Hello! I'm a virtual try-on bot.\n\nChoose an action:",
    },
    "menu_add_model": {
        "ru": "➕ Добавить ваше фото",
        "en": "➕ Add Model",
    },
    "menu_my_models": {
        "ru": "👤 Мои фото",
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
    "upload_model_instr": {
        "ru": "📸 Отправьте ваше фото (человека).\n\nФото должно быть четким, с хорошим освещением.",
        "en": "📸 Send a photo of the model (person).\n\nThe photo should be clear with good lighting.",
    },
    "model_saved": {
        "ru": "✅ Фото успешно сохранено!",
        "en": "✅ Model saved successfully!",
    },
    "model_upload_error": {
        "ru": "❌ Ошибка при загрузке фото. Попробуйте еще раз.",
        "en": "❌ Error uploading model. Please try again.",
    },
    "models_list_empty": {
        "ru": "📭 У вас нет сохраненных фото.\n\nДобавьте первое фото через меню.",
        "en": "📭 Models list is empty.\n\nAdd your first model from the menu.",
    },
    "model_deleted": {
        "ru": "🗑 Фото удалено.",
        "en": "🗑 Model deleted.",
    },
    "delete_error": {
        "ru": "❌ Ошибка при удалении фото.",
        "en": "❌ Error deleting model.",
    },
    "back": {
        "ru": "🔙 Назад",
        "en": "🔙 Back",
    },
    "delete": {
        "ru": "🗑 Удалить",
        "en": "🗑 Delete",
    },
    "try_on_instr": {
        "ru": "📸 Отправьте фото одежды для примерки.",
        "en": "📸 Send a photo of clothing for try-on.",
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
    "unknown_message": {
        "ru": "Не понимаю. Используйте кнопки меню.",
        "en": "I don't understand. Use menu buttons.",
    },
    "try_on_select_model_or_photo": {
        "ru": "👤 Выберите фото для примерки или пришлите ваше фото:",
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
