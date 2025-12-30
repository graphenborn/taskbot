"""FSM состояния для бота"""
from aiogram.fsm.state import State, StatesGroup


class Newsletter(StatesGroup):
    """Состояния для рассылки сообщений"""
    message = State()  # Ожидание сообщения для рассылки


class VoiceConfirmation(StatesGroup):
    """Состояния для подтверждения голосового сообщения"""
    waiting_correction = State()  # Ожидание исправления распознанного текста
