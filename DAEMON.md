# Настройка бота как системного демона (systemd)

Этот документ описывает, как настроить Telegram-бота как системный демон с автозапуском при загрузке системы.

## Установка демона

### 1. Копирование unit-файла systemd

```bash
sudo cp /root/my_telegram_bot/telegram-bot.service /etc/systemd/system/
```

### 2. Перезагрузка конфигурации systemd

```bash
sudo systemctl daemon-reload
```

### 3. Включение автозапуска

```bash
sudo systemctl enable telegram-bot.service
```

### 4. Запуск сервиса

```bash
sudo systemctl start telegram-bot.service
```

## Управление демоном

### Проверка статуса

```bash
sudo systemctl status telegram-bot.service
```

### Остановка бота

```bash
sudo systemctl stop telegram-bot.service
```

### Перезапуск бота

```bash
sudo systemctl restart telegram-bot.service
```

### Отключение автозапуска

```bash
sudo systemctl disable telegram-bot.service
```

## Просмотр логов

### Последние логи

```bash
sudo journalctl -u telegram-bot.service -n 50
```

### Логи в реальном времени

```bash
sudo journalctl -u telegram-bot.service -f
```

### Логи за сегодня

```bash
sudo journalctl -u telegram-bot.service --since today
```

### Логи за определенный период

```bash
sudo journalctl -u telegram-bot.service --since "2024-01-01 00:00:00" --until "2024-01-02 00:00:00"
```

## Настройка service-файла

Файл `telegram-bot.service` содержит следующие ключевые параметры:

- **Type=simple** - простой процесс, который не fork'ается
- **WorkingDirectory** - рабочая директория бота
- **ExecStart** - команда запуска (Python из виртуального окружения)
- **Restart=always** - автоматический перезапуск при падении
- **RestartSec=10** - пауза 10 секунд перед перезапуском
- **After=network.target** - запуск после инициализации сети

## Важные замечания

1. **Виртуальное окружение**: Сервис использует Python из venv (`/root/my_telegram_bot/venv/bin/python`)
2. **.env файл**: Убедитесь, что файл `.env` находится в директории проекта и содержит все необходимые переменные
3. **Права доступа**: Сервис запускается от имени пользователя `root` (указан в файле service)
4. **Автоматический перезапуск**: При сбое бот автоматически перезапустится через 10 секунд

## Устранение неполадок

### Бот не запускается

1. Проверьте логи:
```bash
sudo journalctl -u telegram-bot.service -n 100
```

2. Убедитесь, что виртуальное окружение существует:
```bash
ls -la /root/my_telegram_bot/venv/bin/python
```

3. Проверьте наличие .env файла:
```bash
ls -la /root/my_telegram_bot/.env
```

### Изменение конфигурации

После изменения файла `telegram-bot.service`:

1. Скопируйте обновленный файл:
```bash
sudo cp /root/my_telegram_bot/telegram-bot.service /etc/systemd/system/
```

2. Перезагрузите конфигурацию:
```bash
sudo systemctl daemon-reload
```

3. Перезапустите сервис:
```bash
sudo systemctl restart telegram-bot.service
```

## Обновление бота

При обновлении кода бота:

```bash
# Перейти в директорию проекта
cd /root/my_telegram_bot

# Активировать виртуальное окружение (если нужно установить зависимости)
source venv/bin/activate

# Обновить зависимости (опционально)
pip install -r requirements.txt

# Деактивировать venv
deactivate

# Перезапустить сервис
sudo systemctl restart telegram-bot.service

# Проверить статус
sudo systemctl status telegram-bot.service
```

## Удаление демона

Если нужно полностью удалить сервис:

```bash
# Остановить сервис
sudo systemctl stop telegram-bot.service

# Отключить автозапуск
sudo systemctl disable telegram-bot.service

# Удалить unit-файл
sudo rm /etc/systemd/system/telegram-bot.service

# Перезагрузить systemd
sudo systemctl daemon-reload
```
