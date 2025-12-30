"""Админские команды бота"""
import os
from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramForbiddenError

from database.requests import get_users_count, get_users
from handlers.fsm import Newsletter


# Создаем роутер для админских хендлеров
admin_router = Router()


def is_admin(message: Message) -> bool:
    """
    Фильтр для проверки, является ли пользователь администратором.
    
    Args:
        message: Сообщение от пользователя
        
    Returns:
        bool: True, если пользователь в списке админов
    """
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    
    if not admin_ids_str:
        return False
    
    # Парсим список ID из строки
    admin_ids = [int(admin_id.strip()) for admin_id in admin_ids_str.split(",") if admin_id.strip()]
    
    return message.from_user.id in admin_ids


@admin_router.message(Command("stats"), lambda message: is_admin(message))
async def cmd_stats(message: Message):
    """
    Команда /stats - показывает статистику бота (только для админов).
    
    Возвращает количество зарегистрированных пользователей.
    """
    users_count = await get_users_count()
    await message.answer(f"📊 Всего пользователей: {users_count}")


@admin_router.message(Command("stats"))
async def cmd_stats_not_admin(message: Message):
    """Обработчик для неадминов, пытающихся использовать /stats"""
    await message.answer("⛔ Эта команда доступна только администраторам.")


@admin_router.message(Command("newsletter"), lambda message: is_admin(message))
async def cmd_newsletter(message: Message, state: FSMContext):
    """
    Команда /newsletter - начало процесса рассылки (только для админов).
    
    Устанавливает состояние ожидания сообщения для рассылки.
    """
    await state.set_state(Newsletter.message)
    await message.answer(
        "📨 Отправьте сообщение, которое хотите разослать всем пользователям.\n"
        "Это может быть текст, фото, видео или другой контент."
    )


@admin_router.message(Command("newsletter"))
async def cmd_newsletter_not_admin(message: Message):
    """Обработчик для неадминов, пытающихся использовать /newsletter"""
    await message.answer("⛔ Эта команда доступна только администраторам.")


@admin_router.message(Newsletter.message)
async def newsletter_message_received(message: Message, state: FSMContext):
    """
    Обработчик получения сообщения для рассылки.
    
    Сохраняет данные сообщения и предлагает кнопки для подтверждения или отмены.
    """
    # Сохраняем message_id и chat_id для последующего копирования
    await state.update_data(
        message_id=message.message_id,
        chat_id=message.chat.id
    )
    
    # Создаем клавиатуру с кнопками
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить", callback_data="newsletter_send")
    builder.button(text="❌ Отмена", callback_data="newsletter_cancel")
    builder.adjust(2)  # 2 кнопки в ряд
    
    await message.answer(
        "📋 Сообщение получено!\n\n"
        "Выберите действие:",
        reply_markup=builder.as_markup()
    )


@admin_router.callback_query(lambda c: c.data == "newsletter_send")
async def newsletter_send(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обработчик кнопки "Отправить".
    
    Рассылает сообщение всем пользователям с обработкой ошибок.
    """
    # Проверяем, что это админ
    if not is_admin_by_id(callback.from_user.id):
        await callback.answer("⛔ Эта функция доступна только администраторам.", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.edit_text("⏳ Начинаю рассылку...")
    
    # Получаем данные сохраненного сообщения
    data = await state.get_data()
    message_id = data.get("message_id")
    from_chat_id = data.get("chat_id")
    
    # Получаем список всех пользователей
    users = await get_users()
    
    # Счетчики
    success_count = 0
    blocked_count = 0
    error_count = 0
    
    # Рассылка
    for user_id in users:
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=from_chat_id,
                message_id=message_id
            )
            success_count += 1
        except TelegramForbiddenError:
            # Пользователь заблокировал бота
            blocked_count += 1
        except Exception as e:
            # Другие ошибки (например, пользователь удалил аккаунт)
            error_count += 1
            print(f"Ошибка при отправке пользователю {user_id}: {e}")
    
    # Отправляем отчет админу
    report = (
        f"✅ Рассылка завершена!\n\n"
        f"📊 Статистика:\n"
        f"✅ Успешно: {success_count}\n"
        f"🚫 Заблокировали бота: {blocked_count}\n"
        f"❌ Другие ошибки: {error_count}\n"
        f"👥 Всего пользователей: {len(users)}"
    )
    
    await callback.message.answer(report)
    
    # Сбрасываем состояние
    await state.clear()


@admin_router.callback_query(lambda c: c.data == "newsletter_cancel")
async def newsletter_cancel(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Отмена".
    
    Отменяет рассылку и сбрасывает состояние.
    """
    await callback.answer()
    await callback.message.edit_text("❌ Рассылка отменена.")
    await state.clear()


def is_admin_by_id(user_id: int) -> bool:
    """
    Проверка, является ли пользователь администратором по ID.
    
    Args:
        user_id: Telegram ID пользователя
        
    Returns:
        bool: True, если пользователь в списке админов
    """
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    
    if not admin_ids_str:
        return False
    
    admin_ids = [int(admin_id.strip()) for admin_id in admin_ids_str.split(",") if admin_id.strip()]
    
    return user_id in admin_ids
