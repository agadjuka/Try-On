"""Локализация текстов бота."""

TEXTS = {
    "welcome": {
        "ru": "👋 <b>Добро пожаловать в Виртуальную Примерочную!</b>\n\nЗдесь вы можете примерить любую одежду на своё фото всего за пару кликов ✨\n\n<b>1️⃣ Добавить фото</b>\nНажмите <b>«ДОБАВИТЬ ВАШЕ ФОТО»</b> и пришлите изображение.\nФото сохранится — потом его можно будет использовать для других примерок.\n\n<b>2️⃣ Примерка</b>\nНажмите <b>«ПРИМЕРКА»</b>, выберите сохранённое фото (или загрузите новое) и отправьте до 5 фотографий одежды, которую хотите примерить.",
        "en": "👋 Hello! I'm a virtual try-on bot.\n\nChoose an action:",
    },
    "menu_add_model": {
        "ru": "➕ Добавить ваше фото",
        "en": "➕ Add My Photo",
    },
    "menu_my_models": {
        "ru": "👤 Мои фото",
        "en": "👤 My Photos",
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
        "ru": "📸 Отправьте ваше фото.\n\nФото должно быть четким, с хорошим освещением.",
        "en": "📸 Send your photo.\n\nThe photo should be clear with good lighting.",
    },
    "model_saved": {
        "ru": "✅ Фото успешно сохранено!",
        "en": "✅ Photo saved successfully!",
    },
    "model_upload_error": {
        "ru": "❌ Ошибка при загрузке фото. Попробуйте еще раз.",
        "en": "❌ Error uploading photo. Please try again.",
    },
    "models_list_empty": {
        "ru": "📭 У вас нет сохраненных фото.\n\nДобавьте первое фото через меню.",
        "en": "📭 You have no saved photos.\n\nAdd your first photo from the menu.",
    },
    "model_deleted": {
        "ru": "🗑 Фото удалено.",
        "en": "🗑 Photo deleted.",
    },
    "delete_error": {
        "ru": "❌ Ошибка при удалении фото.",
        "en": "❌ Error deleting photo.",
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
        "ru": "👤 Выберите фото для примерки из сохранённых или пришлите ваше фото:",
        "en": "👤 Choose your photo for try-on or send your photo:",
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
