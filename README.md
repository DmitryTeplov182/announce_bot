# 🚴‍♂️ Announce Bot

Telegram бот для создания анонсов велопоездок с автоматическим скачиванием GPX маршрутов из Komoot. Большое спасибо проекту [komootgpx](https://github.com/timschneeb/KomootGPX) за возможность скачивать GPX файлы.

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
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` с переменными окружения:
```bash
# Обязательно: токен Telegram бота (получить у @BotFather)
TELEGRAM_TOKEN=your_bot_token_here

# Опционально: временная зона (по умолчанию Europe/Belgrade)
# Поддерживаются все стандартные timezone из IANA database
# Примеры: Europe/Belgrade, Europe/Moscow, America/New_York, Asia/Tokyo, UTC
TIMEZONE=Europe/Belgrade
```

5. Запустите бота:
```bash
python bot.py
```

**Готово!** Бот уже настроен с точками старта для Нови Сада и готовыми маршрутами. При запуске автоматически загружаются все готовые маршруты в кеш для быстрой работы.

### Docker установка

1. Клонируйте репозиторий:
```bash
git clone git@github.com:DmitryTeplov182/announce_bot.git
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
docker-compose up --build -d
```

## ⚙️ Настройка

### Точки старта

Точки старта настраиваются в файле `start_points.json`:

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
    }
  ]
}
```

### Готовые маршруты

Готовые маршруты настраиваются в файле `routes.json`:

```json
{
  "routes": [
    {
      "name": "Руменка - Футог - Яма(От Бульвара Европы)",
      "link": "https://www.komoot.com/tour/2526993761"
    },
    {
      "name": "Frushka Lite CCW(от Флагов)",
      "link": "https://www.komoot.com/tour/2396106518"
    }
  ]
}
```

### Формат полей:
- `name` - название маршрута (отображается на кнопке)
- `link` - ссылка на маршрут Komoot

### Команды для управления:
- `/status` - проверить статус бота и кеша
- `/clear_cache` - очистить кеш GPX файлов

### Добавление новых маршрутов и точек старта:
Отредактируйте файлы `routes.json` и `routes.json` - изменения применятся при следующем запуске бота.

## 📱 Команды бота

- `/start` - создать новый анонс
- `/help` - показать справку
- `/status` - статус бота и кеша
- `/clear_cache` - очистить кеш GPX файлов (не видна простому пользователю, но доступна)
- `/restart` - сбросить состояние

## 🔧 Требования

- Python 3.8+
- [komootgpx](https://github.com/timschneeb/KomootGPX)
- Telegram Bot Token

## 📁 Структура проекта

```
announce_bot/
├── bot.py                 # Основной код бота
├── start_points.json      # Настройки точек старта
├── routes.json            # Готовые маршруты
├── requirements.txt       # Зависимости Python
├── .env                  # Переменные окружения
├── .dockerignore         # Исключения для Docker
├── Dockerfile            # Образ Docker
├── compose.yml.demo      # Пример Docker Compose
├── Makefile              # Команды для управления
├── cache/                # Кэш GPX файлов
├── logs/                 # Логи (при Docker)
└── README.md            # Документация
```

## 🧪 Тестирование

Проект включает полный набор автоматических тестов для обеспечения качества кода.

### Запуск тестов
```bash
# Активация виртуального окружения
source venv/bin/activate

# Запуск всех тестов
pytest tests/

# С покрытием кода
pytest tests/ --cov=bot --cov-report=term-missing

# Использование Makefile
make test
```

### Метрики качества
- ✅ **Всего тестов**: 41
- ✅ **Проходят**: 41
- 📊 **Покрытие кода**: 37%
- ⚡ **Время выполнения**: ~2 секунды

Подробная информация о тестах: [README_TESTS.md](README_TESTS.md)

## 🚨 Важные замечания

- Убедитесь, что маршруты Komoot публичные
- `komootgpx` должен быть установлен и доступен в PATH
- **Кэш автоматически очищается от файлов старше 180 дней**
- **При запуске бота автоматически загружаются все готовые маршруты в кеш**

## 📝 Лицензия

THE BEER-WARE LICENSE