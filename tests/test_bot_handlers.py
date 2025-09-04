"""Тесты для обработчиков сообщений бота"""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from bot import (
    ask_date_time,
    ask_komoot_link,
    ask_route_name,
    ask_start_point,
    ASK_DATE,
    ASK_KOMOOT_LINK,
    ASK_ROUTE_NAME,
    ASK_START_POINT
)


class TestBotHandlers:
    """Тесты для обработчиков сообщений бота"""

    @pytest.mark.asyncio
    async def test_ask_date_time_valid_date(self, mock_update, mock_context):
        """Тест обработки корректной даты и времени"""
        mock_update.message.text = "25.12 10:30"

        with patch('bot.parse_date_time') as mock_parse:
            mock_parse.return_value = (Mock(), None)

            result = await ask_date_time(mock_update, mock_context)

            assert result == ASK_KOMOOT_LINK
            assert mock_context.user_data['date_time'] == "25.12 10:30"
            mock_update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_ask_date_time_invalid_date(self, mock_update, mock_context):
        """Тест обработки некорректной даты"""
        mock_update.message.text = "invalid date"

        with patch('bot.parse_date_time') as mock_parse:
            mock_parse.return_value = (None, "Ошибка валидации")

            result = await ask_date_time(mock_update, mock_context)

            assert result == ASK_DATE
            mock_update.message.reply_text.assert_called_with("Ошибка валидации", parse_mode='HTML')

    @pytest.mark.asyncio
    async def test_ask_komoot_link_valid(self, mock_update, mock_context):
        """Тест обработки корректной ссылки Komoot"""
        test_url = "https://www.komoot.com/tour/123456"
        mock_update.message.text = test_url

        with patch('bot.KOMOOT_LINK_PATTERN') as mock_pattern, \
             patch('bot.process_gpx') as mock_process_gpx:
            mock_match = Mock()
            mock_match.group.return_value = "123456"
            mock_pattern.search.return_value = mock_match
            mock_process_gpx.return_value = 4  # PROCESS_GPX

            result = await ask_komoot_link(mock_update, mock_context)

            assert result == 4  # PROCESS_GPX
            assert mock_context.user_data['komoot_link'] == test_url
            assert mock_context.user_data['tour_id'] == "123456"

    @pytest.mark.asyncio
    async def test_ask_komoot_link_invalid(self, mock_update, mock_context):
        """Тест обработки некорректной ссылки"""
        mock_update.message.text = "invalid url"

        with patch('bot.KOMOOT_LINK_PATTERN') as mock_pattern:
            mock_pattern.search.return_value = None

            result = await ask_komoot_link(mock_update, mock_context)

            assert result == ASK_KOMOOT_LINK
            mock_update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_ask_route_name(self, mock_update, mock_context):
        """Тест обработки названия маршрута"""
        mock_update.message.text = "Тестовый маршрут"
        mock_context.user_data['extracted_name'] = None
        mock_context.user_data['length_km'] = 50
        mock_context.user_data['uphill'] = 500

        result = await ask_route_name(mock_update, mock_context)

        assert result == ASK_START_POINT
        assert mock_context.user_data['route_name'] == "Тестовый маршрут"
        mock_update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_ask_route_name_use_extracted(self, mock_update, mock_context):
        """Тест использования извлеченного названия"""
        mock_update.message.text = "✅ Оставить извлеченное"
        mock_context.user_data['extracted_name'] = "Извлеченное название"
        mock_context.user_data['length_km'] = 50
        mock_context.user_data['uphill'] = 500

        result = await ask_route_name(mock_update, mock_context)

        assert result == ASK_START_POINT
        assert mock_context.user_data['route_name'] == "Извлеченное название"

    @pytest.mark.asyncio
    async def test_ask_start_point_valid(self, mock_update, mock_context, sample_start_points):
        """Тест выбора точки старта"""
        mock_update.message.text = sample_start_points[0]['name']
        mock_context.user_data['length_km'] = 50
        mock_context.user_data['uphill'] = 500

        with patch('bot.START_POINTS', sample_start_points):
            result = await ask_start_point(mock_update, mock_context)

            assert result == 7  # ASK_FINISH_POINT
            assert mock_context.user_data['start_point_name'] == sample_start_points[0]['name']

    @pytest.mark.asyncio
    async def test_ask_start_point_custom(self, mock_update, mock_context):
        """Тест выбора своей точки старта"""
        mock_update.message.text = "Своя точка"

        result = await ask_start_point(mock_update, mock_context)

        assert result == 6  # ASK_START_LINK
        assert mock_context.user_data['start_point_name'] is None

    @pytest.mark.asyncio
    async def test_ask_start_point_invalid(self, mock_update, mock_context):
        """Тест выбора несуществующей точки старта"""
        mock_update.message.text = "Несуществующая точка"

        result = await ask_start_point(mock_update, mock_context)

        assert result == ASK_START_POINT
        mock_update.message.reply_text.assert_called_with('Пожалуйста, выбери точку старта из списка.')
