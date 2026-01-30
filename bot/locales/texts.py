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
        "ru": "✅ Примерка готова!\nВ случае неудовлетворительного результата, попробуйте выбрать другое исходное (Ваше) фото.",
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
        "ru": "✅ Примерка готова!\n\n🔄В случае неудовлетворительного результата, попробуйте выбрать другое исходное (Ваше) фото.",
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
    "models_limit_reached": {
        "ru": "Сейчас доступна загрузка не более 7 ваших фото.\n\nПожалуйста, удалите старые фото для того чтобы загрузить новые.",
        "en": "You can upload no more than 7 of your photos at the moment.\n\nPlease delete old photos in the \"Your photos\" section.",
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
    "start_error": {
        "ru": "Произошла ошибка. Попробуй позже.",
        "en": "An error occurred. Please try again later.",
    },
    "nav_prev": {
        "ru": "◀️",
        "en": "◀️",
    },
    "nav_next": {
        "ru": "▶️",
        "en": "▶️",
    },
    "add_new_photo": {
        "ru": "➕ Добавить новое фото",
        "en": "➕ Add New Photo",
    },
    "delete_photo_number": {
        "ru": "🗑 Удалить фото {number}",
        "en": "🗑 Delete Photo {number}",
    },
    "admin_model_added": {
        "ru": "Добавлено новое фото модели",
        "en": "New model photo added",
    },
    "photo_counter": {
        "ru": "Фото {current} из {total}",
        "en": "Photo {current} of {total}",
    },
    "try_on_error_general": {
        "ru": "❌ Произошла ошибка. Попробуйте позже.",
        "en": "❌ An error occurred. Please try again later.",
    },
    "model_not_selected": {
        "ru": "⚠️ Фото не выбрано. Начните заново через меню 'Примерка'.",
        "en": "⚠️ Photo not selected. Start over through the 'Try On' menu.",
    },
    "admin_generation_done": {
        "ru": "Проведена генерация",
        "en": "Generation completed",
    },
    "try_on_results_multiple": {
        "ru": "✅ Готово! Успешно обработано {success} из {total} фото.\n\n🔄В случае неудовлетворительного результата, попробуйте выбрать другое исходное (Ваше) фото.",
        "en": "✅ Done! Successfully processed {success} of {total} photos.\n\n🔄If the result is unsatisfactory, try selecting another original (your) photo.",
    },
    "try_on_partial_failure": {
        "ru": "⚠️ Не удалось обработать {failed} фото из {total}.",
        "en": "⚠️ Failed to process {failed} of {total} photos.",
    },
    "send_garment_photo_please": {
        "ru": "Пожалуйста, отправьте фото одежды.",
        "en": "Please send a photo of clothing.",
    },
    "try_on_started": {
        "ru": "📸 Получено {count} фото. Начинаю примерку...\n⏳ Это займет 15-20 секунд.",
        "en": "📸 Received {count} photos. Starting try-on...\n⏳ This will take 15-20 seconds.",
    },
    "admin_generation_started": {
        "ru": "Начата генерация для {count} элемента(ов) одежды",
        "en": "Generation started for {count} clothing item(s)",
    },
    "admin_garment_added": {
        "ru": "Добавлено новое фото одежды",
        "en": "New clothing photo added",
    },
    "try_on_all_failed": {
        "ru": "❌ Не удалось сгенерировать примерку для ни одного фото.\nПопробуйте еще раз или выберите другие фото.",
        "en": "❌ Failed to generate try-on for any photo.\nPlease try again or select other photos.",
    },
    "try_on_send_error": {
        "ru": "❌ Произошла ошибка при отправке результатов.\nПопробуйте еще раз или нажмите /start.",
        "en": "❌ An error occurred while sending results.\nPlease try again or press /start.",
    },
    "try_on_generation_error": {
        "ru": "❌ Произошла ошибка при генерации примерки.\nПопробуйте еще раз или нажмите /start.",
        "en": "❌ An error occurred while generating try-on.\nPlease try again or press /start.",
    },
    "download_error": {
        "ru": "Произошла ошибка",
        "en": "An error occurred",
    },
    "results_not_found": {
        "ru": "Результаты не найдены",
        "en": "Results not found",
    },
    "result_not_found": {
        "ru": "Результат не найден",
        "en": "Result not found",
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
