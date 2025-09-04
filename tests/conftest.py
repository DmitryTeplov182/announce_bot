"""Конфигурация для pytest и общие фикстуры"""

import pytest
import os
import tempfile
import json
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes
import pytz


@pytest.fixture
def temp_dir():
    """Временная директория для тестов"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_update():
    """Mock для Update объекта Telegram"""
    update = Mock(spec=Update)
    update.message = Mock(spec=Message)
    update.message.text = "test message"
    update.message.from_user = Mock(spec=User)
    update.message.from_user.id = 12345
    update.message.from_user.username = "test_user"
    update.message.chat = Mock(spec=Chat)
    update.message.chat.id = 12345
    update.message.chat.type = "private"

    # Создаем асинхронные моки
    async def async_reply(*args, **kwargs):
        return None

    async def async_reply_photo(*args, **kwargs):
        return None

    update.message.reply_text = Mock(side_effect=async_reply)
    update.message.reply_photo = Mock(side_effect=async_reply_photo)
    return update


@pytest.fixture
def mock_context():
    """Mock для Context объекта"""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    context.bot = Mock()
    context.bot.send_message = Mock(return_value=None)
    context.bot.send_photo = Mock(return_value=None)
    return context


@pytest.fixture
def sample_gpx_data():
    """Пример GPX данных для тестирования"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Test" xmlns="http://www.topografix.com/GPX/1/1">
    <trk>
        <name>Test Route</name>
        <trkseg>
            <trkpt lat="45.2671" lon="19.8335">
                <time>2024-01-01T08:00:00Z</time>
                <ele>80.0</ele>
            </trkpt>
            <trkpt lat="45.2771" lon="19.8435">
                <time>2024-01-01T08:30:00Z</time>
                <ele>85.0</ele>
            </trkpt>
            <trkpt lat="45.2871" lon="19.8535">
                <time>2024-01-01T09:00:00Z</time>
                <ele>90.0</ele>
            </trkpt>
        </trkseg>
    </trk>
</gpx>"""


@pytest.fixture
def sample_start_points():
    """Пример данных точек старта"""
    return [
        {
            "name": "Test Start Point",
            "link": "https://maps.google.com/test"
        },
        {
            "name": "Своя точка",
            "link": None
        }
    ]


@pytest.fixture
def sample_datetime():
    """Пример даты и времени"""
    return datetime(2024, 12, 25, 10, 0, 0)


@pytest.fixture
def sample_timezone():
    """Пример временной зоны"""
    return pytz.timezone('Europe/Belgrade')


@pytest.fixture
def timezone_aware_datetime(sample_datetime, sample_timezone):
    """Пример timezone-aware datetime"""
    return sample_timezone.localize(sample_datetime)


@pytest.fixture(autouse=True)
def mock_timezone_env():
    """Мокаем переменную окружения TIMEZONE для всех тестов"""
    with patch.dict(os.environ, {'TIMEZONE': 'Europe/Belgrade'}):
        yield
