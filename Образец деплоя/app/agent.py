"""Главный агент - роутер для распределения запросов."""

from app.agents.router_agent import router_agent

# Экспортируем роутер агент как главный агент
agent = router_agent
