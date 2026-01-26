import json
import uuid
from typing import (
    Annotated,
    Any,
    Literal,
)

from langchain_core.load.serializable import Serializable
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from pydantic import (
    BaseModel,
    Field,
)


class InputChat(BaseModel):
    """Represents the input for a chat session."""

    messages: list[
        Annotated[HumanMessage | AIMessage | ToolMessage, Field(discriminator="type")]
    ] = Field(
        ..., description="The chat messages representing the current conversation."
    )


class Request(BaseModel):
    """Represents the input for a chat request with optional configuration.

    Attributes:
        input: The chat input containing messages and other chat-related data
        config: Optional configuration for the runnable, including tags, callbacks, etc.
    """

    input: InputChat
    config: RunnableConfig | None = None


class Feedback(BaseModel):
    """Represents feedback for a conversation."""

    score: int | float
    text: str | None = ""
    run_id: str
    log_type: Literal["feedback"] = "feedback"
    service_name: Literal["tester"] = "tester"
    user_id: str = ""


def ensure_valid_config(config: RunnableConfig | None) -> RunnableConfig:
    """Ensures a valid RunnableConfig by setting defaults for missing fields.
    
    Для LangGraph с checkpoint необходимо указать thread_id для изоляции сессий.
    Если thread_id не указан, используется session_id из metadata или генерируется новый.
    """
    if config is None:
        config = RunnableConfig()
    if config.get("run_id") is None:
        config["run_id"] = uuid.uuid4()
    if config.get("metadata") is None:
        config["metadata"] = {}
    
    # Устанавливаем thread_id для checkpoint, если он не указан
    # thread_id используется LangGraph для изоляции сессий и сохранения состояния
    if config.get("configurable", {}).get("thread_id") is None:
        # Используем session_id из metadata, если он есть, иначе генерируем новый
        session_id = config.get("metadata", {}).get("session_id")
        if session_id is None:
            session_id = str(uuid.uuid4())
            config["metadata"]["session_id"] = session_id
        
        # Устанавливаем thread_id в configurable для LangGraph checkpoint
        if config.get("configurable") is None:
            config["configurable"] = {}
        config["configurable"]["thread_id"] = session_id
    
    return config


def default_serialization(obj: Any) -> Any:
    """
    Default serialization for LangChain objects.
    Converts BaseModel instances to JSON strings.
    """
    if isinstance(obj, Serializable):
        return obj.to_json()


def dumps(obj: Any) -> str:
    """
    Serialize an object to a JSON string.

    For LangChain objects (BaseModel instances), it converts them to
    dictionaries before serialization.

    Args:
        obj: The object to serialize

    Returns:
        JSON string representation of the object
    """
    return json.dumps(obj, default=default_serialization)
