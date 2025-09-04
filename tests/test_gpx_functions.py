"""Тесты для функций работы с GPX файлами"""

import pytest
import os
import gpxpy
from datetime import datetime, timedelta
from bot import (
    get_route_points_with_time,
    calculate_route_time_points,
    calculate_distance,
    extract_route_name_from_gpx
)


class TestGPXFunctions:
    """Тесты для функций обработки GPX данных"""

    def test_calculate_distance(self):
        """Тест расчета расстояния между точками"""
        # Координаты Белграда
        lat1, lon1 = 44.8176, 20.4633  # Белград
        lat2, lon2 = 45.2671, 19.8335  # Нови Сад

        distance = calculate_distance(lat1, lon1, lat2, lon2)

        # Расстояние между Белградом и Новим Садом примерно 70-80 км
        assert 70000 <= distance <= 90000  # в метрах

    def test_calculate_distance_zero_distance(self):
        """Тест расчета расстояния для одинаковых точек"""
        lat, lon = 45.0, 20.0
        distance = calculate_distance(lat, lon, lat, lon)

        assert distance == 0.0

    def test_get_route_points_with_time(self, temp_dir, sample_gpx_data):
        """Тест извлечения точек маршрута с временем"""
        # Создаем временный GPX файл
        gpx_path = os.path.join(temp_dir, "test.gpx")
        with open(gpx_path, 'w', encoding='utf-8') as f:
            f.write(sample_gpx_data)

        points = get_route_points_with_time(gpx_path)

        assert len(points) == 3
        assert all('lat' in point for point in points)
        assert all('lon' in point for point in points)
        assert all('time' in point for point in points)
        assert all('ele' in point for point in points)

        # Проверяем временные метки
        assert isinstance(points[0]['time'], datetime)
        assert points[0]['time'].hour == 8
        assert points[0]['time'].minute == 0

    def test_get_route_points_without_time(self, temp_dir):
        """Тест обработки GPX без временных меток"""
        gpx_data = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Test" xmlns="http://www.topografix.com/GPX/1/1">
    <trk>
        <trkseg>
            <trkpt lat="45.2671" lon="19.8335">
                <ele>80.0</ele>
            </trkpt>
        </trkseg>
    </trk>
</gpx>"""

        gpx_path = os.path.join(temp_dir, "test_no_time.gpx")
        with open(gpx_path, 'w', encoding='utf-8') as f:
            f.write(gpx_data)

        points = get_route_points_with_time(gpx_path)

        # Должен вернуть пустой список, так как нет точек со временем
        assert points == []

    def test_calculate_route_time_points(self, sample_datetime):
        """Тест расчета точек маршрута через интервалы времени"""
        # Создаем тестовые точки с большим расстоянием
        points = [
            {'lat': 45.2671, 'lon': 19.8335, 'time': sample_datetime, 'ele': 80.0},
            {'lat': 45.3671, 'lon': 19.9335, 'time': sample_datetime + timedelta(hours=2), 'ele': 85.0},
            {'lat': 45.4671, 'lon': 20.0335, 'time': sample_datetime + timedelta(hours=4), 'ele': 90.0}
        ]

        route_points = calculate_route_time_points(points, sample_datetime, speed_kmh=30)

        # Для маршрута длиной около 20-25 км должно быть хотя бы 3-4 точки
        assert len(route_points) >= 3

        # Проверяем структуру точек
        for point in route_points:
            assert 'lat' in point
            assert 'lon' in point
            assert 'time' in point
            assert 'distance_km' in point
            assert 'ele' in point
            assert isinstance(point['time'], datetime)

    def test_calculate_route_time_points_empty(self):
        """Тест обработки пустого списка точек"""
        route_points = calculate_route_time_points([], datetime.now())

        assert route_points == []

    def test_extract_route_name_from_gpx(self, temp_dir, sample_gpx_data):
        """Тест извлечения названия маршрута из GPX"""
        gpx_path = os.path.join(temp_dir, "test.gpx")
        with open(gpx_path, 'w', encoding='utf-8') as f:
            f.write(sample_gpx_data)

        name = extract_route_name_from_gpx(gpx_path)

        assert name == "Test Route"

    def test_extract_route_name_no_name(self, temp_dir):
        """Тест обработки GPX без названия"""
        gpx_data = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Test" xmlns="http://www.topografix.com/GPX/1/1">
    <trk>
        <trkseg>
            <trkpt lat="45.2671" lon="19.8335"/>
        </trkseg>
    </trk>
</gpx>"""

        gpx_path = os.path.join(temp_dir, "test_no_name.gpx")
        with open(gpx_path, 'w', encoding='utf-8') as f:
            f.write(gpx_data)

        name = extract_route_name_from_gpx(gpx_path)

        assert name == ""
