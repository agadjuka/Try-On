FROM python:3.11-slim

WORKDIR /code

COPY ./requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY ./bot ./bot
COPY ./main.py ./main.py
COPY ./run_bot.py ./run_bot.py

ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

ARG BOT_VERSION=0.0.0
ENV BOT_VERSION=${BOT_VERSION}

# Прод: long polling (токен и GCP — из env / secrets)
CMD ["python", "run_bot.py"]
