"""FSM состояния для пользовательских действий."""

from aiogram.fsm.state import State, StatesGroup


class ModelStates(StatesGroup):
    """Состояния для работы с моделями."""
    
    waiting_for_model_photo = State()


class TryOnStates(StatesGroup):
    """Состояния для примерки."""
    
    waiting_for_model_photo = State()  # Ожидание фото модели (если пользователь присылает фото вместо выбора готовой модели)
    waiting_for_garment_photo = State()


class FeedbackStates(StatesGroup):
    """Состояния для отправки отзыва."""

    waiting_for_feedback = State()
