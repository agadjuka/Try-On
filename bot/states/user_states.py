"""FSM состояния для пользовательских действий."""

from aiogram.fsm.state import State, StatesGroup


class ModelStates(StatesGroup):
    """Состояния для работы с моделями."""
    
    waiting_for_model_photo = State()


class TryOnStates(StatesGroup):
    """Состояния для примерки."""
    
    waiting_for_garment_photo = State()
    model_selected = State()  # Состояние после выбора модели
