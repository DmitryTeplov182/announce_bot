#!/usr/bin/env python3
"""
Тестовый скрипт для проверки интеграции с внешним модулем weather_dashboard.py
"""

import os
import sys
from datetime import datetime

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем функцию из bot.py
from bot import generate_weather_dashboard

def test_weather_dashboard():
    """Тестирует генерацию дашборда погоды"""
    
    # Тестовые данные
    gpx_path = "cache/Bukovac from flags-2070100198.gpx"
    start_datetime = datetime(2025, 9, 6, 8, 30)  # 06.09.2025 08:30
    output_path = "test_dashboard.png"
    speed_kmh = 27
    
    print("🧪 Тестирование интеграции с weather_dashboard.py")
    print(f"📁 GPX файл: {gpx_path}")
    print(f"🕐 Время старта: {start_datetime}")
    print(f"🖼️ Выходной файл: {output_path}")
    print(f"🚗 Скорость: {speed_kmh} км/ч")
    print()
    
    # Проверяем, что GPX файл существует
    if not os.path.exists(gpx_path):
        print(f"❌ GPX файл не найден: {gpx_path}")
        return False
    
    # Вызываем функцию генерации дашборда
    print("🌤️ Вызываем generate_weather_dashboard...")
    success = generate_weather_dashboard(gpx_path, start_datetime, output_path, speed_kmh)
    
    if success:
        print("✅ Дашборд успешно создан!")
        
        # Проверяем, что файл создан
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"📊 Размер файла: {file_size} байт")
            return True
        else:
            print("❌ Файл дашборда не найден после успешного создания")
            return False
    else:
        print("❌ Ошибка при создании дашборда")
        return False

if __name__ == "__main__":
    success = test_weather_dashboard()
    if success:
        print("\n🎉 Тест прошел успешно!")
        sys.exit(0)
    else:
        print("\n💥 Тест не прошел!")
        sys.exit(1)
