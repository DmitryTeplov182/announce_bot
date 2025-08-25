FROM python:3.11-slim

# Установка зависимостей системы (для gpxpy и работы pip)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка komootgpx
RUN curl -L https://github.com/komoot/komoot-gpx/releases/latest/download/komootgpx-linux-x86_64 -o /usr/local/bin/komootgpx \
    && chmod +x /usr/local/bin/komootgpx

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