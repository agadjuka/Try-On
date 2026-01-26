"""Агент для вечернего приветствия."""

from langgraph.prebuilt import create_react_agent
from app.config.llm_factory import create_llm
from app.tools.call_manager import call_manager_tool

LOCATION = "global"
LLM = "gemini-2.5-flash"

llm = create_llm(model=LLM, location=LOCATION, temperature=0)

EVENING_STAGE_INSTRUCTION = """Что бы тебе не написали, скажи клиенту добрый вечер."""

evening_agent = create_react_agent(
    model=llm,
    tools=[call_manager_tool],
    prompt=EVENING_STAGE_INSTRUCTION,
)

