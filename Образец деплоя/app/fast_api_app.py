import logging
import os
import sys
import traceback
from collections.abc import Generator

from fastapi import FastAPI
from fastapi.responses import RedirectResponse, StreamingResponse
from google.cloud import logging as google_cloud_logging
from langchain_core.runnables import RunnableConfig
from traceloop.sdk import Instruments, Traceloop

from app.agent import agent
from app.app_utils.message_time_injector import ensure_time_context
from app.app_utils.simple_chat import SimpleChatRequest, SimpleChatResponse
from app.app_utils.tracing import CloudTraceLoggingSpanExporter
from app.app_utils.typing import (
    Feedback,
    InputChat,
    Request,
    dumps,
    ensure_valid_config,
)

# Настройка детального логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    force=True  # Перезаписываем существующую конфигурацию
)

# Устанавливаем уровень логирования для всех модулей
logging.getLogger("app").setLevel(logging.INFO)
logging.getLogger("app.agents").setLevel(logging.INFO)
logging.getLogger("uvicorn").setLevel(logging.INFO)

# Initialize FastAPI app and logging
app = FastAPI(
    title="tester",
    description="API for interacting with the Agent tester",
)
logging_client = google_cloud_logging.Client()
cloud_logger = logging_client.logger(__name__)
# Стандартный Python logger для ошибок
logger = logging.getLogger(__name__)

# Initialize Telemetry
try:
    Traceloop.init(
        app_name=app.title,
        disable_batch=False,
        exporter=CloudTraceLoggingSpanExporter(),
        instruments={Instruments.LANGCHAIN, Instruments.CREW},
    )
except Exception as e:
    logging.error("Failed to initialize Telemetry: %s", str(e))


def set_tracing_properties(config: RunnableConfig) -> None:
    """Sets tracing association properties for the current request.

    Args:
        config: Optional RunnableConfig containing request metadata
    """
    Traceloop.set_association_properties(
        {
            "log_type": "tracing",
            "run_id": str(config.get("run_id", "None")),
            "user_id": config["metadata"].pop("user_id", "None"),
            "session_id": config["metadata"].pop("session_id", "None"),
            "commit_sha": os.environ.get("COMMIT_SHA", "None"),
        }
    )


def stream_messages(
    input: InputChat,
    config: RunnableConfig | None = None,
) -> Generator[str, None, None]:
    """Stream events in response to an input chat.

    Args:
        input: The input chat messages
        config: Optional configuration for the runnable

    Yields:
        JSON serialized event data
    """
    try:
        config = ensure_valid_config(config=config)
        set_tracing_properties(config)
        messages_with_time = ensure_time_context(input.messages)
        payload = {"messages": messages_with_time}
        input_dict = InputChat(messages=messages_with_time).model_dump()
        
        print("=" * 80, file=sys.stderr, flush=True)
        print("FastAPI: Получен запрос на /stream_messages", file=sys.stderr, flush=True)
        print(f"FastAPI: Входные данные: {input_dict}", file=sys.stderr, flush=True)
        print(f"FastAPI: Конфигурация: {config}", file=sys.stderr, flush=True)
        logger.info("=" * 80)
        logger.info("FastAPI: Получен запрос на /stream_messages")
        logger.info("FastAPI: Входные данные: %s", input_dict)
        logger.info("FastAPI: Конфигурация: %s", config)
        cloud_logger.log_struct({"message": "Starting stream", "input": str(input_dict)}, severity="INFO")
        
        try:
            print("FastAPI: Начинаю streaming от агента...", file=sys.stderr, flush=True)
            logger.info("FastAPI: Начинаю streaming от агента...")
            # С checkpoint LangGraph автоматически восстанавливает историю из checkpoint
            # Передаем только новые сообщения - LangGraph объединит их с сохраненными
            # Логирование уже настроено в агентах через create_llm
            stream = agent.stream(payload, config=config, stream_mode="messages")
            message_count = 0
            for data in stream:
                message_count += 1
                print(f"FastAPI: Получено сообщение #{message_count} из stream", file=sys.stderr, flush=True)
                logger.info("FastAPI: Получено сообщение #%d из stream", message_count)
                try:
                    # data может быть кортежем (message, metadata) или просто message
                    if isinstance(data, tuple):
                        message, metadata = data
                    else:
                        message = data
                        metadata = {}
                    
                    # Сериализуем только сообщение
                    serialized = dumps(message)
                    message_type = type(message).__name__
                    message_content = getattr(message, "content", "N/A")
                    if isinstance(message_content, str) and len(message_content) > 100:
                        message_preview = message_content[:100] + "..."
                    else:
                        message_preview = str(message_content)
                    print(f"FastAPI: Отправляю сообщение типа '{message_type}' с содержимым: '{message_preview}'", file=sys.stderr, flush=True)
                    logger.info("FastAPI: Отправляю сообщение типа '%s' с содержимым: '%s'", message_type, message_preview)
                    logger.debug("FastAPI: Полный JSON сообщения: %s", serialized[:200] if len(serialized) > 200 else serialized)
                    yield serialized + "\n"
                except Exception as e:
                    logger.error("FastAPI: ОШИБКА при сериализации данных #%d: %s", message_count, str(e), exc_info=True)
                    error_message = {
                        "type": "AIMessage",
                        "content": f"Ошибка при сериализации данных: {str(e)}"
                    }
                    yield dumps(error_message) + "\n"
            print(f"FastAPI: Streaming завершен. Всего отправлено сообщений: {message_count}", file=sys.stderr, flush=True)
            logger.info("FastAPI: Streaming завершен. Всего отправлено сообщений: %d", message_count)
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"FastAPI: ОШИБКА в agent.stream: {str(e)}", file=sys.stderr, flush=True)
            print(f"FastAPI: Traceback:\n{error_trace}", file=sys.stderr, flush=True)
            logger.error("FastAPI: ОШИБКА в agent.stream: %s", str(e), exc_info=True)
            error_message = {
                "type": "AIMessage",
                "content": f"Ошибка при вызове агента: {str(e)}. Убедитесь, что вы авторизованы в Google Cloud: 'gcloud auth application-default login'"
            }
            yield dumps(error_message) + "\n"
    except Exception as e:
        # Логируем ошибку и отправляем сообщение об ошибке клиенту
        error_trace = traceback.format_exc()
        print(f"FastAPI: КРИТИЧЕСКАЯ ОШИБКА в stream_messages: {str(e)}", file=sys.stderr, flush=True)
        print(f"FastAPI: Traceback:\n{error_trace}", file=sys.stderr, flush=True)
        logger.error("Error in stream_messages: %s", str(e), exc_info=True)
        error_message = {
            "type": "AIMessage",
            "content": f"Произошла ошибка при обработке запроса: {str(e)}"
        }
        yield dumps(error_message) + "\n"


# Routes
@app.get("/", response_class=RedirectResponse)
def redirect_root_to_docs() -> RedirectResponse:
    """Redirect the root URL to the API documentation."""
    return RedirectResponse(url="/docs")


@app.post("/stream_messages")
def stream_chat_events(request: Request) -> StreamingResponse:
    """Stream chat events in response to an input request.

    Args:
        request: The chat request containing input and config

    Returns:
        Streaming response of chat events
    """
    print("=" * 80, file=sys.stderr, flush=True)
    print("!!! ЗАПРОС ПОЛУЧЕН НА /stream_messages !!!", file=sys.stderr, flush=True)
    print("=" * 80, file=sys.stderr, flush=True)
    return StreamingResponse(
        stream_messages(input=request.input, config=request.config),
        media_type="text/event-stream",
    )


@app.post("/chat", response_model=SimpleChatResponse)
def simple_chat(request: SimpleChatRequest) -> SimpleChatResponse:
    """Простой endpoint для отправки сообщения и получения ответа.

    Args:
        request: Запрос с текстом сообщения

    Returns:
        Ответ от агента в виде текста
    """
    try:
        logger.info("Получен запрос на /chat: %s", request.message)
        
        # Преобразуем простое сообщение в формат InputChat
        from langchain_core.messages import HumanMessage
        
        messages_with_time = ensure_time_context([HumanMessage(content=request.message)])
        payload = {"messages": messages_with_time}
        
        # Создаем конфигурацию
        config = ensure_valid_config(None)
        set_tracing_properties(config)
        
        # Вызываем агента (не стриминг, а обычный invoke)
        # С checkpoint LangGraph автоматически восстанавливает историю из checkpoint
        # Передаем только новые сообщения - LangGraph объединит их с сохраненными
        # Логирование уже настроено в агентах через create_llm
        result = agent.invoke(payload, config=config)
        
        # Извлекаем ответ из результата
        # Router agent возвращает словарь с ключом "messages"
        if isinstance(result, dict) and "messages" in result:
            messages = result["messages"]
        elif isinstance(result, list):
            messages = result
        else:
            messages = [result]
        
        # Находим последнее AI сообщение
        from langchain_core.messages import AIMessage
        ai_response = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                ai_response = msg
                break
        
        if ai_response:
            response_text = ai_response.content
            if isinstance(response_text, list):
                # Если content - список (например, мультимодальный контент)
                response_text = " ".join(str(item) for item in response_text)
            else:
                response_text = str(response_text)
        else:
            response_text = "Не удалось получить ответ от агента"
        
        logger.info("Отправлен ответ на /chat: %s", response_text[:100])
        return SimpleChatResponse(response=response_text)
        
    except Exception as e:
        logger.error("Ошибка в /chat: %s", str(e), exc_info=True)
        error_message = f"Произошла ошибка при обработке запроса: {str(e)}"
        return SimpleChatResponse(response=error_message)


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    cloud_logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
