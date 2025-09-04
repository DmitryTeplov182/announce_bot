"""Тесты для функций валидации данных"""

import pytest
import os
import json
from datetime import datetime, timedelta
from unittest.mock import patch
import pytz
from bot import (
    parse_date_time,
    get_time_of_day,
    load_points_from_file,
    get_default_points
)


class TestDataValidation:
    """Тесты для функций валидации данных"""

    def test_parse_date_time_valid(self):
        """Тест парсинга корректной даты и времени"""
        dt, error_msg = parse_date_time("25.12 10:30")

        assert dt is not None
        assert error_msg is None
        assert dt.day == 25
        assert dt.month == 12
        assert dt.hour == 10
        assert dt.minute == 30

    def test_parse_date_time_past_date(self):
        """Тест парсинга прошедшей даты"""
        # Дата в прошлом
        past_date = (datetime.now() - timedelta(days=1)).strftime("%d.%m %H:%M")
        dt, error_msg = parse_date_time(past_date)

        assert dt is None
        assert error_msg is not None
        assert "уже прошла" in error_msg

    def test_parse_date_time_past_time_today(self):
        """Тест парсинга прошедшего времени сегодня"""
        # Текущее время минус час
        past_time = (datetime.now() - timedelta(hours=1)).strftime("%H:%M")
        today = datetime.now().strftime("%d.%m")
        date_time_str = f"{today} {past_time}"

        dt, error_msg = parse_date_time(date_time_str)

        assert dt is None
        assert error_msg is not None
        assert "уже прошло" in error_msg

    def test_parse_date_time_future_date(self):
        """Тест парсинга будущей даты"""
        # Дата через неделю
        future_date = (datetime.now() + timedelta(days=7)).strftime("%d.%m %H:%M")
        dt, error_msg = parse_date_time(future_date)

        assert dt is not None
        assert error_msg is None

    def test_parse_date_time_returns_timezone_aware(self):
        """Тест что parse_date_time возвращает timezone-aware datetime"""
        future_date = "25.12 10:30"
        dt, error_msg = parse_date_time(future_date)

        assert dt is not None
        assert error_msg is None

        # Проверяем что datetime timezone-aware
        assert dt.tzinfo is not None
        assert hasattr(dt.tzinfo, 'utcoffset')

        # Проверяем что используется правильная timezone
        expected_tz = pytz.timezone('Europe/Belgrade')
        assert dt.tzinfo.zone == expected_tz.zone

    def test_parse_date_time_timezone_handling(self):
        """Тест обработки timezone в parse_date_time"""
        # Этот тест проверяет что функция корректно работает с timezone
        # без проверки конкретной зоны, так как она может быть переопределена
        dt, error_msg = parse_date_time("25.12 10:30")

        assert dt is not None
        assert error_msg is None

        # Проверяем что datetime timezone-aware
        assert dt.tzinfo is not None
        assert hasattr(dt.tzinfo, 'zone')

        # Проверяем что время корректное
        assert dt.hour == 10
        assert dt.minute == 30

    def test_parse_date_time_invalid_format(self):
        """Тест парсинга некорректного формата"""
        dt, error_msg = parse_date_time("invalid date")

        assert dt is None
        assert error_msg is not None
        assert "Неверный формат" in error_msg

    def test_get_time_of_day_morning(self):
        """Тест определения времени суток - утро"""
        tz = pytz.timezone('Europe/Belgrade')
        dt = tz.localize(datetime(2024, 1, 1, 8, 0, 0))
        time_of_day = get_time_of_day(dt)

        assert time_of_day == "утро"

    def test_get_time_of_day_day(self):
        """Тест определения времени суток - день"""
        tz = pytz.timezone('Europe/Belgrade')
        dt = tz.localize(datetime(2024, 1, 1, 14, 0, 0))
        time_of_day = get_time_of_day(dt)

        assert time_of_day == "день"

    def test_get_time_of_day_evening(self):
        """Тест определения времени суток - вечер"""
        tz = pytz.timezone('Europe/Belgrade')
        dt = tz.localize(datetime(2024, 1, 1, 20, 0, 0))
        time_of_day = get_time_of_day(dt)

        assert time_of_day == "вечер"

    def test_get_time_of_day_night(self):
        """Тест определения времени суток - ночь"""
        tz = pytz.timezone('Europe/Belgrade')
        dt = tz.localize(datetime(2024, 1, 1, 2, 0, 0))
        time_of_day = get_time_of_day(dt)

        assert time_of_day == "утро"  # Рано утром считается утро

    def test_load_points_from_file_not_exists(self, temp_dir):
        """Тест загрузки точек из несуществующего файла"""
        points = load_points_from_file("nonexistent.json", fallback_points=[])

        # Функция возвращает дефолтные точки, когда файл не найден
        assert len(points) >= 5  # Минимум дефолтные точки
        assert points[-1]["name"] == "Своя точка"

    def test_load_points_from_file_empty(self, temp_dir):
        """Тест загрузки точек из пустого файла"""
        file_path = os.path.join(temp_dir, "empty.json")
        with open(file_path, 'w') as f:
            f.write("{}")

        points = load_points_from_file(file_path, fallback_points=[])

        # Функция всегда добавляет "Свою точку" в конец списка
        assert len(points) == 1
        assert points[0]["name"] == "Своя точка"

    def test_load_points_from_file_with_data(self, temp_dir, sample_start_points):
        """Тест загрузки точек из файла с данными"""
        import json
        file_path = os.path.join(temp_dir, "points.json")
        with open(file_path, 'w') as f:
            json.dump({"points": sample_start_points}, f)

        points = load_points_from_file(file_path)

        assert len(points) == 3  # Оригинальные 2 + "Своя точка"
        assert points[-1]["name"] == "Своя точка"  # Последняя точка должна быть "Своя точка"

    def test_get_default_points(self):
        """Тест получения точек по умолчанию"""
        points = get_default_points()

        assert len(points) >= 5  # Минимум базовые точки
        assert points[-1]["name"] == "Своя точка"  # Последняя должна быть "Своя точка"
        assert all("name" in point for point in points)
        assert all("link" in point for point in points)
