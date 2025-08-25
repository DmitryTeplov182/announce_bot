# 🚴‍♂️ Announce Bot

Telegram бот для создания анонсов велопоездок с автоматическим скачиванием GPX маршрутов из Komoot.

## ✨ Возможности

- 📅 Создание анонсов с датой и временем
- 🗺️ Автоматическое скачивание GPX маршрутов из Komoot
- 📍 Настраиваемые точки старта
- 🌝🌚 Выбор темпа поездки
- 💬 Добавление комментариев
- 🔄 Редактирование на любом этапе
- 📱 Удобный интерфейс с кнопками

## 🚀 Установка

### Локальная установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd announce_bot
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` с токеном бота:
```bash
TELEGRAM_TOKEN=your_bot_token_here
```

5. Запустите бота:
```bash
python bot.py
```

**Готово!** Бот уже настроен с точками старта для Нови Сада. При необходимости вы можете отредактировать `start_locations.json` и использовать команду `/reload_locations`.

### Docker установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd announce_bot
```

2. Создайте файл `.env` с токеном бота:
```bash
TELEGRAM_TOKEN=your_bot_token_here
```

3. Запустите через Docker Compose:
```bash
# Переименуйте compose.yml.demo в docker-compose.yml
cp compose.yml.demo docker-compose.yml

# Запустите контейнер
docker-compose up -d
```

**Преимущества Docker:**
- Точки старта монтируются как volume (можно редактировать без пересборки)
- Кэш сохраняется между перезапусками
- Автоматический healthcheck
- Изолированная среда

## ⚙️ Настройка точек старта

Точки старта настраиваются в файле `start_locations.json`. Файл уже содержит готовые точки старта для Нови Сада:

```json
{
  "start_points": [
    {
      "name": "koferajd",
      "link": "https://maps.app.goo.gl/iTBcRqjvhJ9DYvRK7"
    },
    {
      "name": "Флаги", 
      "link": "https://maps.app.goo.gl/j95ME2cuzX8k9hnj7"
    },
    {
      "name": "Лидл Лиман",
      "link": "https://maps.app.goo.gl/5JKtAgGBVe48jM9r7"
    },
    {
      "name": "Железничка Парк",
      "link": "https://maps.app.goo.gl/hSZ9C4Xue5RVpMea8"
    },
    {
      "name": "Макси у Бульвара Европы",
      "link": "https://maps.app.goo.gl/3ZbDZM9VVRBDDddp8?g_st=ipc"
    },
    {
      "name": "Своя точка",
      "link": null
    }
  ]
}
```

### Формат полей:
- `name` - название точки старта (отображается в боте)
- `link` - ссылка на Google Maps или `null` для собственной точки

### Команды для управления:
- `/reload_locations` - перезагрузить точки старта из файла
- `/status` - проверить статус бота

### Добавление новых точек:
Просто отредактируйте файл `start_locations.json` и используйте команду `/reload_locations` для применения изменений без перезапуска бота.

## 📱 Команды бота

- `/start` - создать новый анонс
- `/help` - показать справку
- `/status` - статус бота и кэша
- `/clear_cache` - очистить кэш GPX файлов
- `/cancel` - отменить создание анонса
- `/restart` - сбросить состояние
- `/reload_locations` - перезагрузить точки старта

## 🔧 Требования

- Python 3.8+
- `komootgpx` CLI инструмент
- Telegram Bot Token

## 📁 Структура проекта

```
announce_bot/
├── bot.py                 # Основной код бота
├── start_locations.json   # Настройки точек старта
├── requirements.txt       # Зависимости Python
├── .env                  # Переменные окружения
├── .dockerignore         # Исключения для Docker
├── Dockerfile            # Образ Docker
├── compose.yml.demo      # Пример Docker Compose
├── cache/                # Кэш GPX файлов
├── logs/                 # Логи (при Docker)
└── README.md            # Документация
```

## 🚨 Важные замечания

- Убедитесь, что маршруты Komoot публичные
- `komootgpx` должен быть установлен и доступен в PATH
- Кэш автоматически очищается от файлов старше 7 дней

## 📝 Лицензия

MIT License 