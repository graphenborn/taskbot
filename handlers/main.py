from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
import os
import tempfile

from database.requests import set_user, add_task, get_user_tasks
from ai import AIService
from scheduler import add_task_reminder
from handlers.fsm import VoiceConfirmation

# Создаем роутер для обработчиков
router = Router()

# AI сервис будет создан при первом обращении (lazy initialization)
ai_service = None


def get_ai_service() -> AIService:
    """Get or initialize AI service (lazy initialization)."""
    global ai_service
    if ai_service is None:
        ai_service = AIService()
    return ai_service


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    # Сохраняем пользователя в базу данных
    await set_user(
        tg_id=message.from_user.id,
        username=message.from_user.username
    )
    
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        f"Я — Умный Таск-менеджер с искусственным интеллектом.\n\n"
        f"Просто напиши мне задачу, и я:\n"
        f"• Пойму, что нужно сделать\n"
        f"• Распознаю дату и время (если указаны)\n"
        f"• Напомню тебе вовремя ⏰\n\n"
        f"Примеры:\n"
        f"• \"Напомни купить хлеба завтра в 9 утра\"\n"
        f"• \"Через час позвонить маме\"\n"
        f"• \"Сходить в спортзал\" (добавится в бэклог)\n\n"
        f"Команды:\n"
        f"/mytasks — посмотреть свои задачи\n"
        f"/addtask — добавить задачу вручную (без AI)"
    )


@router.message(Command("mytasks"))
async def cmd_my_tasks(message: Message):
    """Показать список задач пользователя"""
    try:
        tasks = await get_user_tasks(message.from_user.id, include_completed=False)
        
        if not tasks:
            await message.answer("У тебя пока нет задач. Добавь первую! 📝")
            return
        
        # Разделяем задачи на запланированные и бэклог
        scheduled_tasks = [t for t in tasks if t.scheduled_time]
        backlog_tasks = [t for t in tasks if not t.scheduled_time]
        
        response = "📋 Твои задачи:\n\n"
        
        if scheduled_tasks:
            response += "⏰ Запланированные:\n"
            for task in scheduled_tasks:
                time_str = task.scheduled_time.strftime("%d.%m.%Y %H:%M")
                response += f"• {time_str} — {task.text}\n"
            response += "\n"
        
        if backlog_tasks:
            response += "📝 Бэклог:\n"
            for task in backlog_tasks:
                response += f"• {task.text}\n"
        
        await message.answer(response)
        
    except Exception as e:
        await message.answer("❌ Ошибка при получении задач")
        print(f"Error in cmd_my_tasks: {e}")


@router.message(F.voice)
async def voice_message_handler(message: Message, state: FSMContext):
    """Обработчик голосовых сообщений для создания задач"""
    try:
        # Показываем индикатор "печатает..."
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING
        )
        
        # Получаем AI сервис
        service = get_ai_service()
        
        # Создаем временную директорию для аудиофайла
        with tempfile.TemporaryDirectory() as temp_dir:
            # Скачиваем голосовое сообщение
            voice_file = await message.bot.get_file(message.voice.file_id)
            file_path = os.path.join(temp_dir, f"{message.voice.file_id}.ogg")
            await message.bot.download_file(voice_file.file_path, file_path)
            
            # Отправляем уведомление о начале распознавания
            status_msg = await message.answer("🎤 Распознаю голосовое сообщение...")
            
            # Распознаем голос с помощью Whisper
            transcribed_text = await service.transcribe_voice(file_path)
            
            # Удаляем сообщение о статусе
            await status_msg.delete()
            
            # Если распознавание прошло успешно
            if transcribed_text:
                # Сохраняем распознанный текст в FSM
                await state.update_data(transcribed_text=transcribed_text)
                
                # Создаем inline-кнопки для подтверждения
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Верно", callback_data="voice_confirm"),
                        InlineKeyboardButton(text="✏️ Исправить", callback_data="voice_correct")
                    ]
                ])
                
                await message.answer(
                    f"📝 Распознал: \"{transcribed_text}\"\n\n"
                    f"Всё верно?",
                    reply_markup=keyboard
                )
            else:
                await message.answer("❌ Не удалось распознать голосовое сообщение. Попробуй ещё раз!")
                
    except Exception as e:
        # Обработка ошибок
        error_message = str(e)
        
        # Специальная обработка для rate limit
        if "429" in error_message or "rate" in error_message.lower():
            await message.answer(
                "⏳ AI сервис временно перегружен.\n"
                "Пожалуйста, попробуй через несколько секунд.\n\n"
                "💡 Это временная проблема бесплатного API."
            )
        else:
            await message.answer(
                "❌ Не получилось обработать голосовое сообщение.\n"
                "Попробуй ещё раз или напиши текстом."
            )
        
        # Логируем ошибку для отладки
        print(f"Error in voice_message_handler: {e}")


@router.callback_query(F.data == "voice_confirm")
async def voice_confirm_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик подтверждения распознанного текста"""
    try:
        # Получаем сохраненный текст
        data = await state.get_data()
        transcribed_text = data.get("transcribed_text")
        
        if not transcribed_text:
            await callback.answer("❌ Ошибка: текст не найден")
            return
        
        # Удаляем кнопки
        await callback.message.edit_reply_markup(reply_markup=None)
        
        # Показываем индикатор
        await callback.message.answer("⏳ Обрабатываю...")
        
        # Получаем AI сервис
        service = get_ai_service()
        
        # Парсим задачу с помощью AI
        parsed = await service.parse_task_message(transcribed_text)
        
        task_text = parsed["task"]
        datetime_str = parsed["datetime"]
        
        # Конвертируем строку даты в datetime объект если есть
        scheduled_time = None
        if datetime_str:
            try:
                scheduled_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        
        # Сохраняем задачу в БД
        task = await add_task(
            user_id=callback.from_user.id,
            text=task_text,
            scheduled_time=scheduled_time
        )
        
        # Формируем ответ пользователю
        if scheduled_time:
            # Добавляем задачу в планировщик
            add_task_reminder(
                bot=callback.bot,
                user_id=callback.from_user.id,
                task_id=task.id,
                text=task_text,
                scheduled_time=scheduled_time
            )
            
            time_str = scheduled_time.strftime("%d.%m.%Y в %H:%M")
            await callback.message.answer(
                f"✅ Поставил напоминание на {time_str}\n\n"
                f"📝 Задача: {task_text}"
            )
        else:
            # Задача без времени - добавляем в бэклог
            await callback.message.answer(
                f"✅ Записал в список задач\n\n"
                f"📝 Задача: {task_text}\n\n"
                f"💡 Если хочешь поставить напоминание, скажи когда!"
            )
        
        # Очищаем состояние
        await state.clear()
        await callback.answer()
        
    except Exception as e:
        await callback.message.answer("❌ Ошибка при обработке задачи")
        print(f"Error in voice_confirm_callback: {e}")
        await callback.answer()


@router.callback_query(F.data == "voice_correct")
async def voice_correct_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик запроса на исправление текста"""
    # Удаляем кнопки
    await callback.message.edit_reply_markup(reply_markup=None)
    
    # Переводим в состояние ожидания исправления
    await state.set_state(VoiceConfirmation.waiting_correction)
    
    await callback.message.answer(
        "✏️ Хорошо, напиши правильный текст или запиши новое голосовое сообщение:"
    )
    await callback.answer()


@router.message(VoiceConfirmation.waiting_correction, F.text)
async def voice_correction_text_handler(message: Message, state: FSMContext):
    """Обработчик исправленного текста"""
    try:
        # Показываем индикатор
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING
        )
        
        # Получаем AI сервис
        service = get_ai_service()
        
        # Парсим задачу с помощью AI
        parsed = await service.parse_task_message(message.text)
        
        task_text = parsed["task"]
        datetime_str = parsed["datetime"]
        
        # Конвертируем строку даты в datetime объект если есть
        scheduled_time = None
        if datetime_str:
            try:
                scheduled_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        
        # Сохраняем задачу в БД
        task = await add_task(
            user_id=message.from_user.id,
            text=task_text,
            scheduled_time=scheduled_time
        )
        
        # Формируем ответ пользователю
        if scheduled_time:
            # Добавляем задачу в планировщик
            add_task_reminder(
                bot=message.bot,
                user_id=message.from_user.id,
                task_id=task.id,
                text=task_text,
                scheduled_time=scheduled_time
            )
            
            time_str = scheduled_time.strftime("%d.%m.%Y в %H:%M")
            await message.answer(
                f"✅ Поставил напоминание на {time_str}\n\n"
                f"📝 Задача: {task_text}"
            )
        else:
            # Задача без времени - добавляем в бэклог
            await message.answer(
                f"✅ Записал в список задач\n\n"
                f"📝 Задача: {task_text}\n\n"
                f"💡 Если хочешь поставить напоминание, скажи когда!"
            )
        
        # Очищаем состояние
        await state.clear()
        
    except Exception as e:
        await message.answer("❌ Ошибка при обработке задачи")
        print(f"Error in voice_correction_text_handler: {e}")
        await state.clear()


@router.message(VoiceConfirmation.waiting_correction, F.voice)
async def voice_correction_voice_handler(message: Message, state: FSMContext):
    """Обработчик нового голосового сообщения при исправлении"""
    # Очищаем состояние и обрабатываем как новое голосовое
    await state.clear()
    await voice_message_handler(message, state)


@router.message(F.text)
async def task_message_handler(message: Message):
    """Обработчик текстовых сообщений для создания задач"""
    try:
        # Показываем индикатор "печатает..."
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING
        )
        
        # Получаем AI сервис
        service = get_ai_service()
        
        # Парсим задачу с помощью AI
        parsed = await service.parse_task_message(message.text)
        
        task_text = parsed["task"]
        datetime_str = parsed["datetime"]
        
        # Конвертируем строку даты в datetime объект если есть
        scheduled_time = None
        if datetime_str:
            try:
                scheduled_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Если не удалось распарсить дату, сохраним без неё
                pass
        
        # Сохраняем задачу в БД
        task = await add_task(
            user_id=message.from_user.id,
            text=task_text,
            scheduled_time=scheduled_time
        )
        
        # Формируем ответ пользователю
        if scheduled_time:
            # Добавляем задачу в планировщик
            add_task_reminder(
                bot=message.bot,
                user_id=message.from_user.id,
                task_id=task.id,
                text=task_text,
                scheduled_time=scheduled_time
            )
            
            time_str = scheduled_time.strftime("%d.%m.%Y в %H:%M")
            await message.answer(
                f"✅ Поставил напоминание на {time_str}\n\n"
                f"📝 Задача: {task_text}"
            )
        else:
            # Задача без времени - добавляем в бэклог
            await message.answer(
                f"✅ Записал в список задач\n\n"
                f"📝 Задача: {task_text}\n\n"
                f"💡 Если хочешь поставить напоминание, скажи когда!"
            )
        
    except Exception as e:
        # Обработка ошибок
        error_message = str(e)
        
        # Специальная обработка для rate limit
        if "429" in error_message or "rate" in error_message.lower():
            await message.answer(
                "⏳ AI сервис временно перегружен.\n"
                "Пожалуйста, попробуй через несколько секунд.\n\n"
                "💡 Это временная проблема бесплатного API."
            )
        else:
            await message.answer(
                "❌ Не получилось обработать задачу.\n"
                "Попробуй переформулировать или попробуй позже."
            )
        
        # Логируем ошибку для отладки
        print(f"Error in task_message_handler: {e}")
