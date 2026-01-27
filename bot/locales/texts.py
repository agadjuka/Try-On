"""Локализация текстов бота."""

TEXTS = {
    "welcome": {
        "ru": "👋 <b>Добро пожаловать в VYON</b>\n\nЗдесь вы можете примерить любую одежду на своё фото всего за пару кликов ✨\n\n<b>1️⃣ Примерка</b>\nНажмите <b>«ПРИМЕРКА»</b>, загрузите ваше фото (или выберите из сохранённых). Фото сохранится — потом его можно будет использовать для других примерок.\n\n<b>2️⃣ Фото одежды</b>\nОтправьте до 5 фотографий элементов одежды, которую хотите примерить. С каждым элементом одежды будет сгенерировано отдельное изображение в новом образе.",
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
        "ru": "👗 Примерка",
        "en": "👗 Try On",
    },
    "new_try_on": {
        "ru": "🔄 Новая примерка",
        "en": "🔄 New Try On",
    },
    "upload_model_instr": {
        "ru": "📸 Отправьте ваше фото.\n\n<b>Для лучшего результата:</b>\n• Загружайте четкое фото крупным планом.\n• Желательно быть в одежде, похожей по длине на новую (например, длинный рукав на длинный).\n• Избегайте слишком объемных вещей (скрывающих фигуру) и открытого тела (купальников).\n\n<i>На стадии разработки бота, для контроля качества, разработчики имеют доступ к загружаемым вами фото</i>",
        "en": "📸 Send your photo.\n\nFor best results, send a clear, well-lit portrait photo.",
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
        "ru": "✅ Примерка готова!\nВ случае неудовлетворительного результата, попробуйте выбрать другое исходное фото.",
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
        "ru": "👤 Выберите Ваше фото для примерки из сохранённых или пришлите ваше фото",
        "en": "👤 Choose your photo for try-on or send your photo",
    },
    "try_on_send_photo": {
        "ru": "📸 Пришлите ваше фото для примерки\n\n<b>Для лучшего результата:</b>\n• Загружайте четкое фото крупным планом.\n• Желательно быть в одежде, похожей по длине на новую (например, длинный рукав на длинный).\n• Избегайте слишком объемных вещей (скрывающих фигуру) и открытого тела (купальников).\n\n<i>На стадии разработки бота, для контроля качества, разработчики имеют доступ к загружаемым вами фото</i>",
        "en": "📸 Send your photo for try-on",
    },
    "my_photos_title": {
        "ru": "⬆️ Ваши фото",
        "en": "⬆️ Your photos",
    },
    "try_on_garment_instr": {
        "ru": "📸 Пришлите фото одежды (до 5 штук).\n\nМожно отправить одно фото или несколько фото одним сообщением.",
        "en": "📸 Send photos of clothing (up to 5).\n\nYou can send one photo or several photos in one message.",
    },
    "try_on_ready": {
        "ru": "✅ Примерка готова!",
        "en": "✅ Try-on ready!",
    },
    "models_load_error": {
        "ru": "Произошла ошибка при загрузке моделей.",
        "en": "An error occurred while loading models.",
    },
    "model_gallery_error": {
        "ru": "Ошибка при загрузке фото модели.",
        "en": "Error loading model photo.",
    },
    "send_photo_please": {
        "ru": "Пожалуйста, отправьте фото.",
        "en": "Please send a photo.",
    },
    "photo_get_error": {
        "ru": "Не удалось получить фото.",
        "en": "Failed to get photo.",
    },
    "no_photos": {
        "ru": "Нет фото",
        "en": "No photos",
    },
    "unknown_command": {
        "ru": "Неизвестная команда",
        "en": "Unknown command",
    },
    "list_end": {
        "ru": "Достигнут конец списка",
        "en": "End of list reached",
    },
    "navigation_error": {
        "ru": "Ошибка при навигации",
        "en": "Navigation error",
    },
    "invalid_data_format": {
        "ru": "Неверный формат данных",
        "en": "Invalid data format",
    },
    "photo_not_found": {
        "ru": "Фото не найдено",
        "en": "Photo not found",
    },
    "models_album_error": {
        "ru": "❌ Не удалось загрузить фото моделей.",
        "en": "❌ Failed to load model photos.",
    },
    "photo_selected": {
        "ru": "Фото выбрано",
        "en": "Photo selected",
    },
    "error_occurred": {
        "ru": "Произошла ошибка",
        "en": "An error occurred",
    },
    "download_hq": {
        "ru": "⬇️ Скачать в высоком качестве",
        "en": "⬇️ Download in high quality",
    },
    "photo_number": {
        "ru": "Фото {number}",
        "en": "Photo {number}",
    },
    "upscaling": {
        "ru": "⏳ Увеличиваю качество изображения...",
        "en": "⏳ Increasing image quality...",
    },
    "upscale_error": {
        "ru": "❌ Ошибка при увеличении качества изображения.",
        "en": "❌ Error increasing image quality.",
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
