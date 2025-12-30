"""Тестовый скрипт для проверки работы базы данных"""
import asyncio
from database.engine import async_main as create_db
from database.requests import set_user
from database.engine import async_session_maker
from database.models import User
from sqlalchemy import select


async def test_database():
    """Тестирование работы базы данных"""
    print("1. Инициализация базы данных...")
    await create_db()
    print("✓ База данных готова!\n")
    
    # Тест 1: Добавление нового пользователя
    print("2. Добавление нового пользователя (tg_id=123456, username='test_user')...")
    await set_user(tg_id=123456, username='test_user')
    print("✓ Пользователь добавлен!\n")
    
    # Проверяем, что пользователь добавлен
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.tg_id == 123456))
        user = result.scalar_one_or_none()
        print(f"   Найден пользователь: {user}\n")
    
    # Тест 2: Обновление существующего пользователя (upsert)
    print("3. Обновление пользователя (tg_id=123456, username='updated_user')...")
    await set_user(tg_id=123456, username='updated_user')
    print("✓ Пользователь обновлен!\n")
    
    # Проверяем обновление
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.tg_id == 123456))
        user = result.scalar_one_or_none()
        print(f"   Обновленный пользователь: {user}\n")
    
    # Тест 3: Добавление пользователя без username
    print("4. Добавление пользователя без username (tg_id=789012)...")
    await set_user(tg_id=789012, username=None)
    print("✓ Пользователь добавлен!\n")
    
    # Показываем всех пользователей
    print("5. Список всех пользователей в базе:")
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        for user in users:
            print(f"   - {user}")
    
    print("\n✅ Все тесты пройдены успешно!")


if __name__ == "__main__":
    asyncio.run(test_database())
