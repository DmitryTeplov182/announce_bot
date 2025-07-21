FROM python:3.11-slim

# Установка зависимостей системы (для gpxpy и работы pip)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем файлы проекта
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Переменная окружения для python-dotenv (опционально)
ENV PYTHONUNBUFFERED=1

# Запуск бота
CMD ["python", "bot.py"] 