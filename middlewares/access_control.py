import os
from typing import Callable, Dict, Any, Awaitable, List
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class AccessControlMiddleware(BaseMiddleware):
    """Middleware для ограничения доступа к боту по ID пользователя."""
    
    def __init__(self) -> None:
        """Инициализация middleware с загрузкой разрешенных ID."""
        super().__init__()
        self.allowed_user_ids = self._load_allowed_users()
    
    def _load_allowed_users(self) -> List[int]:
        """
        Загрузить список разрешенных ID пользователей из переменной окружения.
        
        Returns:
            List[int]: Список разрешенных Telegram user IDs
        """
        allowed_ids_str = os.getenv("ALLOWED_USER_IDS", "")
        
        if not allowed_ids_str:
            # Если не задано, разрешаем всем (пустой список = нет ограничений)
            return []
        
        try:
            # Парсим строку вида "123456789,987654321" в список int
            return [int(user_id.strip()) for user_id in allowed_ids_str.split(",") if user_id.strip()]
        except ValueError:
            print("Warning: Invalid ALLOWED_USER_IDS format in .env file")
            return []
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        """
        Проверка доступа пользователя перед выполнением обработчика.
        
        Args:
            handler: Следующий обработчик в цепочке
            event: Событие (сообщение)
            data: Дополнительные данные
            
        Returns:
            Результат выполнения обработчика или None при отказе в доступе
        """
        # Если список пустой, доступ разрешен всем
        if not self.allowed_user_ids:
            return await handler(event, data)
        
        # Проверяем, есть ли ID пользователя в списке разрешенных
        if event.from_user and event.from_user.id in self.allowed_user_ids:
            # Доступ разрешен - продолжаем обработку
            return await handler(event, data)
        else:
            # Доступ запрещен - отправляем сообщение и останавливаем обработку
            await event.answer(
                "🚫 Извини, у тебя нет доступа к этому боту.\n\n"
                "Бот работает только для авторизованных пользователей."
            )
            # Не вызываем handler - останавливаем обработку
            return None
