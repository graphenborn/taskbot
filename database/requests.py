"""Функции для работы с базой данных"""
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.dialects.sqlite import insert

from database.engine import async_session_maker
from database.models import User, Task


async def set_user(tg_id: int, username: str | None = None):
    """
    Добавляет нового пользователя или обновляет существующего (upsert).
    
    Args:
        tg_id: Telegram ID пользователя
        username: Имя пользователя (может быть None)
    """
    async with async_session_maker() as session:
        # SQLite upsert с использованием insert().on_conflict_do_update()
        stmt = insert(User).values(
            tg_id=tg_id,
            username=username
        )
        
        # При конфликте (duplicate tg_id) обновляем username
        stmt = stmt.on_conflict_do_update(
            index_elements=['tg_id'],  # Указываем уникальное поле
            set_=dict(username=username)  # Поля для обновления
        )
        
        await session.execute(stmt)
        await session.commit()


async def get_users_count() -> int:
    """
    Возвращает количество пользователей в базе данных.
    
    Returns:
        int: Количество записей в таблице users
    """
    async with async_session_maker() as session:
        stmt = select(func.count(User.id))
        result = await session.execute(stmt)
        count = result.scalar()
        return count


async def get_users() -> list[int]:
    """
    Возвращает список Telegram ID всех пользователей.
    
    Returns:
        list[int]: Список tg_id всех пользователей
    """
    async with async_session_maker() as session:
        stmt = select(User.tg_id)
        result = await session.execute(stmt)
        # Извлекаем все tg_id
        users = result.scalars().all()
        return list(users)


async def add_task(user_id: int, text: str, scheduled_time: datetime | None = None) -> Task:
    """
    Добавляет новую задачу в базу данных.
    
    Args:
        user_id: Telegram ID пользователя
        text: Описание задачи
        scheduled_time: Время напоминания (None для бэклога)
        
    Returns:
        Task: Созданная задача
    """
    async with async_session_maker() as session:
        task = Task(
            user_id=user_id,
            text=text,
            scheduled_time=scheduled_time,
            is_completed=False
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task


async def get_user_tasks(user_id: int, include_completed: bool = False) -> list[Task]:
    """
    Получает все задачи пользователя.
    
    Args:
        user_id: Telegram ID пользователя
        include_completed: Включать ли завершенные задачи
        
    Returns:
        list[Task]: Список задач пользователя
    """
    async with async_session_maker() as session:
        stmt = select(Task).where(Task.user_id == user_id)
        
        if not include_completed:
            stmt = stmt.where(Task.is_completed == False)
        
        stmt = stmt.order_by(Task.scheduled_time.asc().nulls_last())
        
        result = await session.execute(stmt)
        tasks = result.scalars().all()
        return list(tasks)
