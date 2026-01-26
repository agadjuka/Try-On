FROM python:3.11-slim

WORKDIR /code

# Копируем requirements.txt
COPY ./requirements.txt ./

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY ./bot ./bot
COPY ./main.py ./main.py

# Переменные окружения для версионирования
ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

ARG BOT_VERSION=0.0.0
ENV BOT_VERSION=${BOT_VERSION}

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
