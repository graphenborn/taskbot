"""Настройка подключения к базе данных"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from database.models import Base


# Путь к файлу базы данных
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot.db')
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# Создаем асинхронный движок
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Установите True для отладки SQL-запросов
)

# Создаем фабрику сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def async_main():
    """Создает все таблицы в базе данных"""
    async with engine.begin() as conn:
        # Создаем все таблицы, определенные в Base
        await conn.run_sync(Base.metadata.create_all)
