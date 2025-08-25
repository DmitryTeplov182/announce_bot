FROM python:3.11-slim

# Установка зависимостей системы (для gpxpy и работы pip)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем файлы проекта
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы (исключения в .dockerignore)
COPY . .

# Создаем директорию для кэша
RUN mkdir -p /app/cache

# Переменная окружения для python-dotenv
ENV PYTHONUNBUFFERED=1

# Запуск бота
CMD ["python", "bot.py"] 