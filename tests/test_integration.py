"""Интеграционные тесты для всего бота"""

import pytest
import os
import json
from datetime import datetime
from bot import (
    load_ready_routes,
    load_route_comments,
    cleanup_old_gpx_files,
    cleanup_old_dashboards
)


class TestIntegration:
    """Интеграционные тесты"""

    def test_load_ready_routes(self, temp_dir):
        """Тест загрузки готовых маршрутов"""
        # Создаем тестовый файл ready_routes.json
        routes_data = {
            "ready_routes": [
                {
                    "name": "Тестовый маршрут 1",
                    "start_point": "Точка А",
                    "start_point_link": "https://maps.google.com/test1",
                    "comment": "Тестовый комментарий 1",
                    "komoot_link": "https://komoot.com/tour/123"
                },
                {
                    "name": "Тестовый маршрут 2",
                    "start_point": "Точка Б",
                    "start_point_link": "https://maps.google.com/test2",
                    "comment": "Тестовый комментарий 2",
                    "komoot_link": "https://komoot.com/tour/456"
                }
            ]
        }

        routes_file = os.path.join(temp_dir, "ready_routes.json")
        with open(routes_file, 'w', encoding='utf-8') as f:
            json.dump(routes_data, f)

        # Меняем рабочую директорию для теста
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            routes = load_ready_routes()

            assert len(routes) == 2
            assert routes[0]['name'] == "Тестовый маршрут 1"
            assert routes[1]['name'] == "Тестовый маршрут 2"
        finally:
            os.chdir(original_cwd)

    def test_load_route_comments(self, temp_dir):
        """Тест загрузки комментариев маршрутов"""
        routes_data = {
            "routes": [
                {
                    "name": "Маршрут 1",
                    "link": "https://komoot.com/tour/123"
                },
                {
                    "name": "Маршрут 2",
                    "link": "https://komoot.com/tour/456"
                }
            ]
        }

        routes_file = os.path.join(temp_dir, "routes.json")
        with open(routes_file, 'w', encoding='utf-8') as f:
            json.dump(routes_data, f)

        # Меняем рабочую директорию для теста
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            routes = load_route_comments()

            assert len(routes) == 2
            assert routes[0]['name'] == "Маршрут 1"
            assert routes[1]['link'] == "https://komoot.com/tour/456"
        finally:
            os.chdir(original_cwd)

    def test_cleanup_old_gpx_files(self, temp_dir):
        """Тест очистки старых GPX файлов"""
        from datetime import datetime, timedelta
        import time

        # Создаем тестовые файлы
        old_file = os.path.join(temp_dir, "old_test.gpx")
        new_file = os.path.join(temp_dir, "new_test.gpx")

        # Создаем старый файл (более 180 дней назад)
        with open(old_file, 'w') as f:
            f.write("test")

        # Изменяем время модификации старого файла
        old_time = time.time() - (181 * 24 * 60 * 60)  # 181 день назад
        os.utime(old_file, (old_time, old_time))

        # Создаем новый файл
        with open(new_file, 'w') as f:
            f.write("test")

        # Меняем рабочую директорию и вызываем функцию
        original_cwd = os.getcwd()
        original_cache_dir = "cache"
        try:
            os.chdir(temp_dir)
            # Патчим CACHE_DIR для теста
            import bot
            bot.CACHE_DIR = temp_dir

            cleanup_old_gpx_files()

            # Проверяем что старый файл удален, новый остался
            assert not os.path.exists(old_file)
            assert os.path.exists(new_file)

        finally:
            os.chdir(original_cwd)
            # Восстанавливаем оригинальное значение
            bot.CACHE_DIR = original_cache_dir

    def test_cleanup_old_dashboards(self, temp_dir):
        """Тест очистки старых дашбордов"""
        import time

        # Создаем тестовые файлы дашбордов
        old_dashboard = os.path.join(temp_dir, "dashboard_old.png")
        new_dashboard = os.path.join(temp_dir, "dashboard_new.png")

        # Создаем старый дашборд
        with open(old_dashboard, 'w') as f:
            f.write("test")

        # Изменяем время модификации старого файла
        old_time = time.time() - (181 * 24 * 60 * 60)  # 181 день назад
        os.utime(old_dashboard, (old_time, old_time))

        # Создаем новый дашборд
        with open(new_dashboard, 'w') as f:
            f.write("test")

        # Меняем рабочую директорию и вызываем функцию
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            cleanup_old_dashboards()

            # Проверяем что старый дашборд удален, новый остался
            assert not os.path.exists(old_dashboard)
            assert os.path.exists(new_dashboard)

        finally:
            os.chdir(original_cwd)
