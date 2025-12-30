"""Модели базы данных"""
from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    # Первичный ключ
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Telegram ID пользователя (уникальный)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    
    # Имя пользователя (может быть None)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    
    def __repr__(self) -> str:
        return f"User(id={self.id}, tg_id={self.tg_id}, username={self.username})"


class Task(Base):
    """Модель задачи"""
    __tablename__ = 'tasks'
    
    # Первичный ключ
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # ID пользователя (связь с таблицей users)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.tg_id'))
    
    # Текст задачи
    text: Mapped[str] = mapped_column(String)
    
    # Время напоминания (может быть None для задач в бэклоге)
    scheduled_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Статус выполнения
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def __repr__(self) -> str:
        return f"Task(id={self.id}, user_id={self.user_id}, text={self.text}, scheduled_time={self.scheduled_time}, is_completed={self.is_completed})"
