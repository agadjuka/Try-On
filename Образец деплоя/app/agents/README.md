# Архитектура агентов

## Структура

Проект использует архитектуру с одним **роутер-агентом** (`message_router.py`), который распределяет запросы между специализированными агентами.

## Текущие агенты

- `greeting` - приветствие
- `information_gathering` - сбор информации об услугах
- `booking` - запись на услугу
- `booking_to_master` - запись к конкретному мастеру
- `view_my_booking` - просмотр записей клиента
- `reschedule` - перенос записи
- `cancellation_request` - отмена записи

## Создание нового агента

### 1. Создать файл агента

Создай файл `{route_name}_stage.py` в папке `agents/`:

```python
from langgraph.prebuilt import create_react_agent
from app.config.llm_factory import create_llm
from app.tools.call_manager import call_manager_tool
# ... импорты других инструментов

LOCATION = "global"
LLM = "gemini-2.5-flash"

llm = create_llm(model=LLM, location=LOCATION, temperature=0)

{ROUTE_NAME}_STAGE_INSTRUCTION = """# РОЛЬ
Ты — AI-администратор салона красоты LookTown.
# ... инструкции для агента
"""

{route_name}_agent = create_react_agent(
    model=llm,
    tools=[call_manager_tool, ...],  # список инструментов
    prompt={ROUTE_NAME}_STAGE_INSTRUCTION,
)
```

**Важно:**
- Имя файла: `{route_name}_stage.py` (route_name в нижнем регистре с подчеркиваниями)
- Имя переменной агента: `{route_name}_agent`
- Имя константы инструкции: `{ROUTE_NAME}_STAGE_INSTRUCTION` (верхний регистр)

### 2. Зарегистрировать агента в реестре

**ВАЖНО:** После создания файла агента необходимо зарегистрировать его в реестре.

Открой файл `app/agents/registry.py` и добавь информацию о новом агенте в метод `_load_agents()`:

```python
self._agents = {
    ...
    "{route_name}": {
        "file": "{route_name}_stage.py",
        "name": "Читаемое имя агента",
    },
}
```

**Пример:**
```python
"consultation": {
    "file": "consultation_stage.py",
    "name": "Консультация",
},
```

После регистрации агент автоматически появится в эдиторе промптов.

### 3. Зарегистрировать в message_router.py

#### 3.1. Добавить импорт (строки 25-31)

```python
from app.agents.{route_name}_stage import {route_name}_agent
```

#### 3.2. Добавить маршрут в valid_routes (строка 171)

```python
valid_routes = [..., "{route_name}"]
```

#### 3.3. Добавить в словарь agents (строки 244-252)

```python
agents = {
    ...
    "{route_name}": {route_name}_agent,
}
```

### 4. Обновить ROUTER_INSTRUCTION

В файле `app/config/agent_config.py` (строки 27-34) добавить описание маршрута:

```python
ROUTER_INSTRUCTION = """...
- "{route_name}" — описание назначения агента
...
"""
```

## Удаление агента

### 1. Удалить файл агента

Удали файл `{route_name}_stage.py` из папки `agents/`

### 2. Удалить из реестра

Открой файл `app/agents/registry.py` и удали запись о агенте из метода `_load_agents()`:

```python
# Удали эту запись:
"{route_name}": {
    "file": "{route_name}_stage.py",
    "name": "...",
},
```

### 3. Удалить из message_router.py

#### 3.1. Удалить импорт (строки 25-31)

Удали строку:
```python
from app.agents.{route_name}_stage import {route_name}_agent
```

#### 3.2. Удалить из valid_routes (строка 171)

Удали `"{route_name}"` из списка `valid_routes`

#### 3.3. Удалить из словаря agents (строки 244-252)

Удали запись:
```python
"{route_name}": {route_name}_agent,
```

### 4. Удалить из ROUTER_INSTRUCTION

В файле `app/config/agent_config.py` (строки 27-34) удали строку с описанием маршрута:
```python
- "{route_name}" — описание назначения агента
```

## Важные замечания

- **Именование:** route_name должен быть в нижнем регистре с подчеркиваниями (snake_case)
- **Инструменты:** Все агенты должны иметь `call_manager_tool` в списке инструментов
- **Fallback:** Если роутер не может определить маршрут, используется `greeting` (строка 193)
- **LangGraph:** Агенты создаются через `create_react_agent` из `langgraph.prebuilt`
- **LLM:** Все агенты используют `gemini-2.5-flash` с `temperature=0`

## Файлы для изменения

При создании/удалении агента нужно изменить:

1. `agents/{route_name}_stage.py` - создать/удалить файл
2. `agents/registry.py` - **ОБЯЗАТЕЛЬНО** зарегистрировать/удалить агента в реестре
3. `agents/message_router.py` - импорт, valid_routes, словарь agents
4. `agents/router_stage.py` - обновить ROUTER_STAGE_INSTRUCTION (добавить описание маршрута)


