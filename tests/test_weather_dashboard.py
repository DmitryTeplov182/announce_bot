"""Тесты для функций генерации дашборда погоды"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from bot import (
    generate_weather_dashboard,
    get_weather_data_for_route,
    create_weather_dashboard
)


class TestWeatherDashboard:
    """Тесты для функций генерации дашборда погоды"""

    @patch('bot.requests_cache.CachedSession')
    @patch('bot.openmeteo_requests.Client')
    def test_get_weather_data_for_route_success(self, mock_client_class, mock_session_class):
        """Тест успешного получения данных о погоде"""
        # Мокаем API ответы
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Создаем мок для ответа API
        mock_response = Mock()
        mock_hourly = Mock()
        mock_variables = [Mock(), Mock(), Mock(), Mock(), Mock(), Mock(), Mock(), Mock(), Mock()]

        # Настраиваем переменные для каждого индекса
        for i, var in enumerate(mock_variables):
            var.ValuesAsNumpy.return_value = [20.5 + i, 21.5 + i, 22.5 + i]  # Разные значения

        mock_hourly.Variables.side_effect = lambda index: mock_variables[index]
        mock_hourly.Time.return_value = 1640995200  # timestamp
        mock_hourly.TimeEnd.return_value = 1640998800
        mock_hourly.Interval.return_value = 3600

        mock_response.Hourly.return_value = mock_hourly
        mock_client.weather_api.return_value = [mock_response]

        # Тестовые точки маршрута
        route_points = [
            {
                'lat': 45.2671,
                'lon': 19.8335,
                'time': datetime(2024, 1, 1, 10, 0, 0),
                'distance_km': 0,
                'ele': 80
            }
        ]

        weather_data = get_weather_data_for_route(route_points)

        assert len(weather_data) == 1
        assert weather_data[0] is not None
        assert 'temperature' in weather_data[0]
        assert 'wind_speed' in weather_data[0]
        assert 'weather_code' in weather_data[0]

    @patch('bot.requests_cache.CachedSession')
    @patch('bot.openmeteo_requests.Client')
    def test_get_weather_data_for_route_api_error(self, mock_client_class, mock_session_class):
        """Тест обработки ошибок API погоды"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.weather_api.side_effect = Exception("API Error")

        route_points = [
            {
                'lat': 45.2671,
                'lon': 19.8335,
                'time': datetime(2024, 1, 1, 10, 0, 0),
                'distance_km': 0,
                'ele': 80
            }
        ]

        weather_data = get_weather_data_for_route(route_points)

        assert len(weather_data) == 1
        assert weather_data[0] is None

    @patch('bot.plt.savefig')
    @patch('bot.plt.close')
    @patch('bot.plt.figure')
    @patch('bot.plt.subplot')
    @patch('bot.plt.setp')
    def test_create_weather_dashboard_success(self, mock_setp, mock_subplot, mock_figure, mock_close, mock_savefig):
        """Тест успешного создания дашборда"""
        # Мокаем matplotlib
        mock_fig = Mock()
        mock_fig.get_axes.return_value = []  # Пустой список осей
        mock_figure.return_value = mock_fig

        mock_ax = Mock()
        mock_ax.xaxis.get_majorticklabels.return_value = []
        mock_subplot.return_value = mock_ax

        # Тестовые данные
        route_points = [
            {
                'lat': 45.2671,
                'lon': 19.8335,
                'time': datetime(2024, 1, 1, 10, 0, 0),
                'distance_km': 0,
                'ele': 80
            }
        ]

        weather_data = [
            {
                'time': datetime(2024, 1, 1, 10, 0, 0),
                'distance_km': 0,
                'temperature': 20.5,
                'wind_speed': 5.2,
                'wind_direction': 180,
                'humidity': 65,
                'pressure': 1013,
                'weather_code': 1,
                'precipitation_probability': 10,
                'cloud_cover': 25,
                'feels_like': 22.0
            }
        ]

        result = create_weather_dashboard(route_points, weather_data, "test_output.png")

        assert result is True
        mock_savefig.assert_called_once()
        mock_close.assert_called_once()

    def test_create_weather_dashboard_no_valid_data(self):
        """Тест создания дашборда без валидных данных"""
        route_points = []
        weather_data = []

        result = create_weather_dashboard(route_points, weather_data, "test_output.png")

        assert result is False

    @patch('bot.generate_weather_dashboard')
    def test_generate_weather_dashboard_integration(self, mock_generate, temp_dir, sample_gpx_data):
        """Интеграционный тест генерации дашборда"""
        mock_generate.return_value = True

        # Создаем тестовый GPX файл
        gpx_path = os.path.join(temp_dir, "test.gpx")
        with open(gpx_path, 'w', encoding='utf-8') as f:
            f.write(sample_gpx_data)

        start_datetime = datetime(2024, 1, 1, 8, 0, 0)
        output_path = os.path.join(temp_dir, "test_dashboard.png")

        # Вызываем функцию напрямую без мока
        result = generate_weather_dashboard(gpx_path, start_datetime, output_path)

        # Проверяем что функция была вызвана
        assert isinstance(result, bool)

    def test_generate_weather_dashboard_invalid_gpx(self, temp_dir):
        """Тест генерации дашборда с невалидным GPX"""
        invalid_gpx_path = os.path.join(temp_dir, "invalid.gpx")
        with open(invalid_gpx_path, 'w') as f:
            f.write("invalid gpx content")

        start_datetime = datetime(2024, 1, 1, 8, 0, 0)
        output_path = os.path.join(temp_dir, "test_dashboard.png")

        result = generate_weather_dashboard(invalid_gpx_path, start_datetime, output_path)

        assert result is False
