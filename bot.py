import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from handlers import router, admin_router
from database.engine import async_main as create_db
from middlewares import AccessControlMiddleware
from scheduler import init_scheduler, start_scheduler, shutdown_scheduler, add_task_reminder
from database.requests import get_user_tasks
from database.models import Task
from sqlalchemy import select
from database.engine import async_session_maker


async def main():
    """Главная функция запуска бота"""
    # Загружаем переменные окружения из .env файла
    load_dotenv()
    
    # Получаем токен бота
    bot_token = os.getenv("BOT_TOKEN")
    
    if not bot_token:
        raise ValueError("BOT_TOKEN не найден! Проверьте файл .env")
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Создаем таблицы в базе данных
    logging.info("Инициализация базы данных...")
    await create_db()
    logging.info("База данных готова!")
    
    # Создаем объекты бота и диспетчера с хранилищем для FSM
    storage = MemoryStorage()
    bot = Bot(token=bot_token)
    dp = Dispatcher(storage=storage)
    
    # Инициализируем планировщик задач
    logging.info("Инициализация планировщика задач...")
    init_scheduler(bot)
    
    # Загружаем существующие запланированные задачи в планировщик
    logging.info("Загрузка запланированных задач...")
    async with async_session_maker() as session:
        # Получаем все незавершенные задачи с назначенным временем в будущем
        now = datetime.now()
        result = await session.execute(
            select(Task).where(
                Task.scheduled_time >= now,
                Task.is_completed == False
            )
        )
        tasks = result.scalars().all()
        
        # Добавляем каждую задачу в планировщик
        for task in tasks:
            if task.scheduled_time:
                add_task_reminder(
                    bot=bot,
                    user_id=task.user_id,
                    task_id=task.id,
                    text=task.text,
                    scheduled_time=task.scheduled_time
                )
        
        logging.info(f"Загружено {len(tasks)} запланированных задач")
    
    # Запускаем планировщик
    start_scheduler()
    logging.info("Планировщик запущен!")
    
    # Регистрируем middleware для контроля доступа
    # Применяется ко всем сообщениям, проверяет разрешенных пользователей
    dp.message.middleware(AccessControlMiddleware())
    
    # Регистрируем роутеры с обработчиками
    # Важно: admin_router регистрируется первым для приоритета админских команд
    dp.include_router(admin_router)
    dp.include_router(router)
    
    logging.info("Бот запущен!")
    
    try:
        # Запускаем бота (long polling)
        await dp.start_polling(bot)
    finally:
        # Корректное завершение работы
        logging.info("Остановка планировщика...")
        shutdown_scheduler()
        await bot.session.close()


if __name__ == "__main__":
    # Запускаем главную функцию
    asyncio.run(main())
