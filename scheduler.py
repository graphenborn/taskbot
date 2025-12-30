"""Task scheduler for managing reminders and daily digests."""
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Task
from database.engine import async_session_maker


# Global scheduler instance
scheduler: AsyncIOScheduler | None = None


async def send_reminder(bot: Bot, user_id: int, text: str, task_id: int) -> None:
    """
    Send reminder message to user and mark task as completed.
    
    Args:
        bot: Telegram bot instance
        user_id: Telegram user ID
        text: Task text to remind about
        task_id: Task ID in database
    """
    try:
        # Send reminder message
        await bot.send_message(
            chat_id=user_id,
            text=f"⏰ Напоминание!\n\n{text}"
        )
        
        # Mark task as completed in database
        async with async_session_maker() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task:
                task.is_completed = True
                await session.commit()
                
    except Exception as e:
        print(f"Error sending reminder: {e}")


async def daily_digest(bot: Bot) -> None:
    """
    Send daily digest with today's scheduled tasks to all users.
    This function runs every day at 8:00 AM UTC+3.
    """
    try:
        async with async_session_maker() as session:
            # Get all tasks scheduled for today that are not completed
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            result = await session.execute(
                select(Task).where(
                    Task.scheduled_time >= today_start,
                    Task.scheduled_time < today_end,
                    Task.is_completed == False
                )
            )
            tasks = result.scalars().all()
            
            # Group tasks by user
            user_tasks: dict[int, list[Task]] = {}
            for task in tasks:
                if task.user_id not in user_tasks:
                    user_tasks[task.user_id] = []
                user_tasks[task.user_id].append(task)
            
            # Send digest to each user
            for user_id, user_task_list in user_tasks.items():
                message = "📋 План на сегодня:\n\n"
                for task in sorted(user_task_list, key=lambda t: t.scheduled_time or datetime.max):
                    time_str = task.scheduled_time.strftime("%H:%M") if task.scheduled_time else "—"
                    message += f"• {time_str} — {task.text}\n"
                
                try:
                    await bot.send_message(chat_id=user_id, text=message)
                except Exception as e:
                    print(f"Error sending digest to user {user_id}: {e}")
                    
    except Exception as e:
        print(f"Error in daily_digest: {e}")


def init_scheduler(bot: Bot) -> AsyncIOScheduler:
    """
    Initialize and configure the scheduler.
    
    Args:
        bot: Telegram bot instance
        
    Returns:
        Configured AsyncIOScheduler instance
    """
    global scheduler
    
    if scheduler is None:
        scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
        
        # Schedule daily digest at 8:00 AM UTC+3
        scheduler.add_job(
            daily_digest,
            trigger='cron',
            hour=8,
            minute=0,
            args=[bot],
            id='daily_digest',
            replace_existing=True
        )
    
    return scheduler


def add_task_reminder(bot: Bot, user_id: int, task_id: int, text: str, scheduled_time: datetime) -> None:
    """
    Add a new task reminder to the scheduler.
    
    Args:
        bot: Telegram bot instance
        user_id: Telegram user ID
        task_id: Task ID in database
        text: Task text
        scheduled_time: When to send the reminder
    """
    global scheduler
    
    if scheduler is None:
        raise RuntimeError("Scheduler not initialized")
    
    # Create unique job ID
    job_id = f"task_reminder_{task_id}"
    
    # Add job to scheduler
    scheduler.add_job(
        send_reminder,
        trigger=DateTrigger(run_date=scheduled_time),
        args=[bot, user_id, text, task_id],
        id=job_id,
        replace_existing=True
    )


def start_scheduler() -> None:
    """Start the scheduler."""
    global scheduler
    
    if scheduler and not scheduler.running:
        scheduler.start()


def shutdown_scheduler() -> None:
    """Shutdown the scheduler gracefully."""
    global scheduler
    
    if scheduler and scheduler.running:
        scheduler.shutdown()
