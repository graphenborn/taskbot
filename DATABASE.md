# База данных проекта

## Структура

Проект использует **SQLAlchemy 2.0** (async) с драйвером **aiosqlite**.

### Файловая структура

```
database/
├── __init__.py       # Инициализация пакета
├── models.py         # Модели данных (User)
├── engine.py         # Настройка подключения к БД
└── requests.py       # Функции для работы с данными
```

### Модель User

**Таблица:** `users`

| Поле     | Тип        | Описание                    |
|----------|------------|-----------------------------|
| id       | INTEGER    | Первичный ключ (auto)       |
| tg_id    | BIGINT     | Telegram ID (unique)        |
| username | VARCHAR    | Имя пользователя (nullable) |

### Функции

#### `set_user(tg_id: int, username: str | None = None)`

Добавляет нового пользователя или обновляет существующего (upsert).

**Параметры:**
- `tg_id` - Telegram ID пользователя
- `username` - Имя пользователя (опционально)

**Пример использования:**
```python
from database.requests import set_user

# Сохранить пользователя
await set_user(tg_id=123456789, username='john_doe')

# Обновить username для существующего пользователя
await set_user(tg_id=123456789, username='new_username')
```

### Инициализация

База данных автоматически инициализируется при запуске бота в `bot.py`:

```python
from database.engine import async_main as create_db

# В функции main()
await create_db()
```

### Тестирование

Для тестирования работы базы данных выполните:

```bash
python test_db.py
```

### Файл базы данных

База данных хранится в файле `bot.db` в корне проекта.

**Важно:** Файл `bot.db` исключен из отслеживания (.clineignore).
