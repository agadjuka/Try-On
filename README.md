# Virtual Try-On Script

Автономный скрипт для генерации примерки одежды с помощью Google Cloud Vertex AI Virtual Try-On API.

## Структура папок

```
virtual_try_on/
├── input/
│   ├── person/      # Фотографии моделей
│   └── product/     # Фотографии одежды
├── output/          # Результаты примерки
├── config.py        # Конфигурация
├── image_processor.py  # Обработка изображений
├── api_client.py    # Клиент для API
├── main.py          # Основной скрипт
└── .env             # Переменные окружения
```

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Установите Google Cloud SDK:
   - Скачайте с https://cloud.google.com/sdk/docs/install
   - Авторизуйтесь: `gcloud auth login`

3. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

4. Заполните `.env` файл:
   - `GOOGLE_CLOUD_PROJECT_ID` - ID вашего проекта в Google Cloud
   - `GOOGLE_CLOUD_REGION` - регион (по умолчанию: us-central1)

## Использование

1. Поместите фотографии моделей в папку `input/person/`
2. Поместите фотографии одежды в папку `input/product/`
3. Запустите скрипт:
```bash
python main.py
```

4. Результаты будут сохранены в папку `output/`

## Переменные окружения

### Обязательные:
- `GOOGLE_CLOUD_PROJECT_ID` - ID проекта Google Cloud

### Опциональные:
- `GOOGLE_CLOUD_REGION` - регион (по умолчанию: us-central1)
- `BASE_STEPS` - качество генерации (по умолчанию: 32)
- `SAMPLE_COUNT` - количество изображений на пару (1-4, по умолчанию: 1)
- `ADD_WATERMARK` - добавлять водяной знак (true/false, по умолчанию: true)
- `PERSON_GENERATION` - разрешение генерации людей (dont_allow/allow_adult/allow_all, по умолчанию: allow_adult)
- `SAFETY_SETTING` - уровень фильтрации безопасности (по умолчанию: block_medium_and_above)
- `OUTPUT_MIME_TYPE` - формат вывода (image/png или image/jpeg, по умолчанию: image/png)
- `COMPRESSION_QUALITY` - качество сжатия для JPEG (0-100, по умолчанию: 75)
- `STORAGE_URI` - путь в Cloud Storage для сохранения (опционально)
- `SEED` - случайное зерно для генерации (только если ADD_WATERMARK=false)

## Форматы изображений

Поддерживаемые форматы: JPG, JPEG, PNG, BMP, WEBP

## Примечания

- Скрипт автоматически создаст все комбинации моделей и одежды
- Если в папках по одному файлу - будет создана одна пара
- Результаты сохраняются с уникальными именами, включающими timestamp
- Для работы требуется авторизация через `gcloud auth login`
