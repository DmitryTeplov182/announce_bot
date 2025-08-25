import os
import re
import json
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)
import logging
import asyncio
import glob
import gpxpy
import gpxpy.gpx
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
ASK_DATE_TIME, ASK_KOMOOT_LINK, PROCESS_GPX, ASK_ROUTE_NAME, ASK_START_POINT, ASK_START_LINK, ASK_PACE, ASK_COMMENT, PREVIEW_STEP, SELECT_ROUTE = range(10)

STEP_TO_NAME = {
    ASK_DATE_TIME: '✏️ Изм. дату',
    ASK_KOMOOT_LINK: '✏️ Изм. ссылку Komoot',
    ASK_ROUTE_NAME: '✏️ Изм. название',
    ASK_START_POINT: '✏️ Изм. старт',
    ASK_PACE: '✏️ Изм. темп',
    ASK_COMMENT: '✏️ Изм. коммен.',
}

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')

# Паттерн для извлечения tour_id из Komoot-ссылки
KOMOOT_LINK_PATTERN = re.compile(r'(https?://)?(www\.)?komoot\.[^/]+/tour/(\d+)')
CACHE_DIR = 'cache'
os.makedirs(CACHE_DIR, exist_ok=True)

def load_start_points():
    """Загружает точки старта из JSON файла"""
    try:
        with open('start_points.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            start_points = data.get('start_points', [])
            
            # Автоматически добавляем "Свою точку" в конец списка
            start_points.append({
                'name': 'Своя точка',
                'link': None
            })
            
            return start_points
            
    except FileNotFoundError:
        logger.warning("Файл start_points.json не найден, используем точки по умолчанию")
        default_points = [
            {'name': 'koferajd', 'link': 'https://maps.app.goo.gl/iTBcRqjvhJ9DYvRK7'},
            {'name': 'Флаги', 'link': 'https://maps.app.goo.gl/j95ME2cuzX8k9hnj7'},
            {'name': 'Лидл Лиман', 'link': 'https://maps.app.goo.gl/5JKtAgGBVe48jM9r7'},
            {'name': 'Железничка Парк', 'link': 'https://maps.app.goo.gl/hSZ9C4Xue5RVpMea8'},
            {'name': 'Макси у Бульвара Европы', 'link': 'https://maps.app.goo.gl/3ZbDZM9VVRBDDddp8?g_st=ipc'},
        ]
        
        # Добавляем "Свою точку" и к точкам по умолчанию
        default_points.append({
            'name': 'Своя точка',
            'link': None
        })
        
        return default_points
        
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка при парсинге start_points.json: {e}")
        default_points = [
            {'name': 'koferajd', 'link': 'https://maps.app.goo.gl/iTBcRqjvhJ9DYvRK7'},
            {'name': 'Флаги', 'link': 'https://maps.app.goo.gl/j95ME2cuzX8k9hnj7'},
            {'name': 'Лидл Лиман', 'link': 'https://maps.app.goo.gl/5JKtAgGBVe48jM9r7'},
            {'name': 'Железничка Парк', 'link': 'https://maps.app.goo.gl/hSZ9C4Xue5RVpMea8'},
            {'name': 'Макси у Бульвара Европы', 'link': 'https://maps.app.goo.gl/3ZbDZM9VVRBDDddp8?g_st=ipc'},
        ]
        
        # Добавляем "Свою точку" и к точкам по умолчанию
        default_points.append({
            'name': 'Своя точка',
            'link': None
        })
        
        return default_points
        
    except Exception as e:
        logger.error(f"Неожиданная ошибка при загрузке точек старта: {e}")
        default_points = [
            {'name': 'koferajd', 'link': 'https://maps.app.goo.gl/iTBcRqjvhJ9DYvRK7'},
            {'name': 'Флаги', 'link': 'https://maps.app.goo.gl/j95ME2cuzX8k9hnj7'},
            {'name': 'Лидл Лиман', 'link': 'https://maps.app.goo.gl/5JKtAgGBVe48jM9r7'},
            {'name': 'Железничка Парк', 'link': 'https://maps.app.goo.gl/hSZ9C4Xue5RVpMea8'},
            {'name': 'Макси у Бульвара Европы', 'link': 'https://maps.app.goo.gl/3ZbDZM9VVRBDDddp8?g_st=ipc'},
        ]
        
        # Добавляем "Свою точку" и к точкам по умолчанию
        default_points.append({
            'name': 'Своя точка',
            'link': None
        })
        
        return default_points

# Загружаем точки старта при импорте модуля
START_POINTS = load_start_points()

# Предустановленные точки старта (заполнишь потом)
# START_POINTS = [
#     {'name': 'koferajd', 'link': 'https://maps.app.goo.gl/iTBcRqjvhJ9DYvRK7'},
#     {'name': 'Флаги', 'link': 'https://maps.app.goo.gl/j95ME2cuzX8k9hnj7'},
#     {'name': 'Лидл Лиман', 'link': 'https://maps.app.goo.gl/5JKtAgGBVe48jM9r7'},
#     {'name': 'Железничка Парк', 'link': 'https://maps.app.goo.gl/hSZ9C4Xue5RVpMea8'},
#     {'name': 'Своя точка', 'link': None},
# ]

PACE_OPTIONS = [
    '🌝🌚🌚',
    '🌝🌗🌚',
    '🌝🌝🌚',
    '🌝🌝🌗',
    '🌝🌝🌝',
]

RU_WEEKDAYS = [
    'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'
]

def get_time_of_day(dt: datetime) -> str:
    if dt.hour < 12:
        return 'утро'
    elif dt.hour < 18:
        return 'день'
    else:
        return 'вечер'

def parse_date_time(date_time_str: str) -> tuple[datetime, str]:
    """
    Парсит строку даты и времени, возвращает (datetime, error_message)
    Ожидается формат: 19.07 10:00
    """
    try:
        dt = datetime.strptime(date_time_str, '%d.%m %H:%M')
        # Подставляем текущий год
        dt = dt.replace(year=datetime.now().year)
        
        # Проверяем, что дата не в прошлом
        now = datetime.now()
        if dt < now:
            return None, "❌ <b>Указанная дата уже прошла!</b> Укажи будущую дату."
        
        # Проверяем, что дата не слишком далеко в будущем (больше года)
        if dt > now + timedelta(days=365):
            return None, "❌ <b>Дата слишком далеко в будущем!</b> Укажи дату в пределах года."
            
        return dt, None
        
    except ValueError:
        return None, "❌ <b>Неверный формат даты!</b> Используй формат: ДД.ММ ЧЧ:ММ (например: 19.07 10:00)"
    except Exception as e:
        return None, f"❌ <b>Ошибка при обработке даты:</b> {str(e)}"

def load_ready_routes():
    """Загружает готовые маршруты из JSON файла"""
    try:
        with open('ready_routes.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            routes = data.get('ready_routes', [])
            logger.info(f"Загружено готовых маршрутов: {len(routes)}")
            for i, route in enumerate(routes):
                logger.info(f"Маршрут {i+1}: {route['name']} -> {route['start_point']}")
            return routes
    except FileNotFoundError:
        logger.warning("Файл ready_routes.json не найден")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка при парсинге ready_routes.json: {e}")
        return []
    except Exception as e:
        logger.error(f"Неожиданная ошибка при загрузке готовых маршрутов: {e}")
        return []

# Загружаем готовые маршруты при импорте модуля
READY_ROUTES = load_ready_routes()

def load_route_comments():
    """Загружает готовые ссылки на маршруты из JSON файла"""
    try:
        with open('routes.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            routes = data.get('routes', [])
            logger.info(f"Загружено готовых ссылок на маршруты: {len(routes)}")
            return routes
    except FileNotFoundError:
        logger.warning("Файл routes.json не найден")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка при парсинге routes.json: {e}")
        return []
    except Exception as e:
        logger.error(f"Неожиданная ошибка при загрузке готовых ссылок: {e}")
        return []

# Загружаем готовые ссылки на маршруты при импорте модуля
ROUTE_COMMENTS = load_route_comments()

async def quick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для быстрого создания анонса из готового маршрута"""
    logger.info(f"quick_command вызван, READY_ROUTES: {len(READY_ROUTES)}")
    
    if not READY_ROUTES:
        logger.warning("READY_ROUTES пуст")
        await update.message.reply_text(
            "❌ Готовые маршруты не найдены. Обратитесь к администратору."
        )
        return ConversationHandler.END
    
    # Создаем клавиатуру с готовыми маршрутами
    keyboard = []
    for i, route in enumerate(READY_ROUTES):
        keyboard.append([f"{i+1}. {route['name']}"])
        logger.info(f"Добавлена кнопка: {i+1}. {route['name']}")
    
    keyboard.append(["❌ Отмена"])
    
    await update.message.reply_text(
        "🚴‍♂️ <b>Выбери готовый маршрут:</b>\n\n"
        "Просто выбери маршрут, и тебе нужно будет указать только дату, время и темп!",
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    
    # Сохраняем состояние для обработки выбора маршрута
    context.user_data['quick_mode'] = True
    logger.info("quick_command завершен, возвращаем SELECT_ROUTE")
    return SELECT_ROUTE

async def handle_route_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор готового маршрута"""
    text = update.message.text.strip()
    logger.info(f"handle_route_selection вызван с текстом: '{text}'")
    
    # Проверяем отмену
    if text == "❌ Отмена":
        logger.info("Пользователь отменил выбор маршрута")
        await update.message.reply_text(
            "❌ Выбор маршрута отменен.\n\n"
            "Используй /start для создания нового анонса.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    # Проверяем, что это выбор маршрута
    if text.startswith(('1.', '2.', '3.', '4.', '5.')):
        try:
            route_index = int(text.split('.')[0]) - 1
            logger.info(f"Выбран маршрут с индексом: {route_index}")
            if 0 <= route_index < len(READY_ROUTES):
                route = READY_ROUTES[route_index]
                logger.info(f"Загружен маршрут: {route['name']}")
                context.user_data.update({
                    'komoot_link': route['komoot_link'],
                    'route_name': route['name'],
                    'start_point_name': route['start_point'],
                    'start_point_link': route['start_point_link'],
                    'comment': route['comment'],
                    'quick_mode': True
                })
                
                await update.message.reply_text(
                    f"🚴‍♂️ <b>Выбран готовый маршрут:</b>\n\n"
                    f"<b>{route['name']}</b>\n"
                    f"📍 Старт: {route['start_point']}\n"
                    f"💬 {route['comment']}\n\n"
                    f"Теперь укажи дату и время старта (например: <code>26.08 10:00</code>)",
                    parse_mode='HTML',
                    reply_markup=ReplyKeyboardRemove()
                )
                return ASK_DATE_TIME
            else:
                logger.warning(f"Индекс маршрута {route_index} вне диапазона")
        except (ValueError, IndexError) as e:
            logger.error(f"Ошибка при обработке выбора маршрута: {e}")
            pass
    
    # Если это не выбор маршрута, возвращаемся к выбору
    logger.info("Неверный выбор маршрута, показываем список снова")
    keyboard = []
    for i, route in enumerate(READY_ROUTES):
        keyboard.append([f"{i+1}. {route['name']}"])
    keyboard.append(["❌ Отмена"])
    
    await update.message.reply_text(
        "Пожалуйста, выбери маршрут из списка выше.",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return SELECT_ROUTE

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, есть ли готовый маршрут в команде
    command_args = update.message.text.split()
    if len(command_args) > 1 and command_args[1].isdigit():
        # Если передан номер маршрута, загружаем его
        route_index = int(command_args[1]) - 1
        if 0 <= route_index < len(READY_ROUTES):
            route = READY_ROUTES[route_index]
            context.user_data.update({
                'komoot_link': route['komoot_link'],
                'route_name': route['name'],
                'start_point_name': route['start_point'],
                'start_point_link': route['start_point_link'],
                'comment': route['comment'],
                'quick_mode': True
            })
            await update.message.reply_text(
                f"🚴‍♂️ <b>Выбран готовый маршрут:</b>\n\n"
                f"<b>{route['name']}</b>\n"
                f"📍 Старт: {route['start_point']}\n"
                f"💬 {route['comment']}\n\n"
                f"Теперь укажи дату и время старта (например: <code>26.08 10:00</code>)",
                parse_mode='HTML'
            )
            return ASK_DATE_TIME
    
    # Обычный старт
    tomorrow = datetime.now() + timedelta(days=1)
    date_example = tomorrow.strftime('%d.%m')
    
    # Первое сообщение - приветствие и команды
    await update.message.reply_text(
        f'🚴‍♂️ <b>Привет! Я бот для создания анонсов велопоездок</b>\n\n'
        f'Создам красивый анонс с маршрутом, точкой старта и всеми деталями.\n\n'
        f'<b>Основные команды:</b>\n'
        f'• /start - создать новый анонс\n'
        f'• /help - показать справку\n'
        f'• /restart - сбросить состояние',
        parse_mode='HTML'
    )
    
    # Второе сообщение - начало работы
    await update.message.reply_text(
        f'<b>Давай начнем!</b>\n\n'
        f'Укажи дату и время старта (например: <code>{date_example} 10:00</code>)',
        parse_mode='HTML'
    )
    
    return ASK_DATE_TIME

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда помощи"""
    help_text = (
        "🚴‍♂️ <b>Справка по боту</b>\n\n"
        "<b>Как создать анонс:</b>\n"
        "1. Укажи дату и время старта (формат: ДД.ММ ЧЧ:ММ)\n"
        "2. Пришли ссылку на маршрут Komoot\n"
        "3. Введи название маршрута\n"
        "4. Выбери точку старта\n"
        "5. Укажи ожидаемый темп (количество лун)\n"
        "6. Добавь комментарий\n"
        "7. Проверь и отправь анонс\n\n"
        "<b>Основные команды:</b>\n"
        "• /start - создать новый анонс\n"
        "• /help - эта справка\n"
        "• /restart - сбросить состояние\n\n"
        "<b>Точки старта:</b>\n"
        "• koferajd, Флаги, Лидл Лиман, Железничка Парк\n"
        "• Или укажи свою точку\n\n"
        "<b>Формат даты:</b> ДД.ММ ЧЧ:ММ (например: 19.07 10:00)"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

async def ask_date_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сохраняем дату и время в user_data
    date_time_str = update.message.text.strip()
    
    # Валидируем дату
    dt, error_msg = parse_date_time(date_time_str)
    if error_msg:
        await update.message.reply_text(error_msg)
        return ASK_DATE_TIME
    
    context.user_data['date_time'] = date_time_str
    context.user_data['parsed_datetime'] = dt  # Сохраняем распарсенную дату
    
    # Проверяем быстрый режим
    if context.user_data.get('quick_mode'):
        # В быстром режиме после даты спрашиваем темп
        context.user_data['quick_mode'] = False
        keyboard = [[p] for p in PACE_OPTIONS]
        await update.message.reply_text(
            '✅ Дата и время приняты!\n\n'
            'Теперь выбери ожидаемый темп (количество лун):',
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_PACE
    
    if context.user_data.get('edit_mode'):
        context.user_data['edit_mode'] = False
        return await preview_step(update, context)
        
    # Создаем клавиатуру с готовыми ссылками
    keyboard = []
    for route in ROUTE_COMMENTS:
        keyboard.append([f"🔗 {route['name']}"])
    
    keyboard.append(["❌ Отмена"])
    
    await update.message.reply_text(
        '✅ Дата и время приняты!\n\n'
        'Теперь пришли <b>публичную</b> ссылку на маршрут Komoot\n\n'
        'Или выбери готовый маршрут:',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_KOMOOT_LINK

async def ask_komoot_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    logger.info(f"ask_komoot_link вызван с текстом: '{text}'")
    logger.info(f"ROUTE_COMMENTS загружено: {len(ROUTE_COMMENTS)}")
    
    # Проверяем, не выбрана ли готовая ссылка
    if text.startswith("🔗 "):
        route_name = text[2:]  # Убираем эмодзи
        logger.info(f"Выбрана готовая ссылка: '{route_name}'")
        # Ищем маршрут по названию
        selected_route = None
        for route in ROUTE_COMMENTS:
            if route['name'] == route_name:
                selected_route = route
                break
        
        if selected_route:
            # Автоматически вставляем готовую ссылку
            text = selected_route['link']
            logger.info(f"Найден маршрут: {selected_route['name']} -> {selected_route['link']}")
            await update.message.reply_text(
                f"✅ Выбран готовый маршрут: <b>{selected_route['name']}</b>\n\n"
                f"Ссылка: {selected_route['link']}",
                parse_mode='HTML',
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            logger.warning(f"Маршрут не найден: '{route_name}'")
            await update.message.reply_text(
                "❌ Маршрут не найден. Попробуй еще раз.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ASK_KOMOOT_LINK
    
    # Проверяем отмену
    if text == "❌ Отмена":
        logger.info("Пользователь отменил ввод ссылки")
        await update.message.reply_text(
            "❌ Ввод ссылки отменен.\n\n"
            "Используй /start для создания нового анонса.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    match = KOMOOT_LINK_PATTERN.search(text)
    logger.info(f"Результат поиска ссылки: {match}")
    
    if not match:
        # Если ссылка некорректная, просто просим ввести правильную
        await update.message.reply_text(
            '❌ Неверный формат ссылки!\n\n'
            'Пожалуйста, пришли корректную публичную ссылку на маршрут Komoot\n\n'
            'Или используй кнопки выше для выбора готового маршрута.'
        )
        return ASK_KOMOOT_LINK
    
    context.user_data['komoot_link'] = text
    context.user_data['tour_id'] = match.group(3)
    if context.user_data.get('edit_mode'):
        context.user_data['edit_mode'] = False
        return await preview_step(update, context)
    # Переходим к обработке GPX
    return await process_gpx(update, context)

async def process_gpx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tour_id = context.user_data['tour_id']
    logger.info(f"Начинаю скачивание GPX для tour_id: {tour_id}")
    
    try:
        # Используем асинхронный subprocess
        process = await asyncio.create_subprocess_exec(
            'komootgpx',
            '-d', tour_id,
            '-o', CACHE_DIR,
            '-e',
            '-n',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        logger.info(f"Процесс komootgpx запущен с PID: {process.pid}")
        
        # Ждем завершения с таймаутом
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60.0)
            logger.info(f"Процесс komootgpx завершен с кодом: {process.returncode}")
        except asyncio.TimeoutError:
            # Если процесс завис, убиваем его
            logger.warning(f"Процесс komootgpx завис, убиваю PID: {process.pid}")
            process.kill()
            await update.message.reply_text('Превышено время ожидания при скачивании GPX. Попробуй другую ссылку на маршрут Komoot:')
            return ASK_KOMOOT_LINK
            
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Неизвестная ошибка"
            logger.error(f"Ошибка komootgpx: {error_msg}")
            await update.message.reply_text(f'Ошибка при скачивании GPX: {error_msg}. Попробуй другую ссылку на маршрут Komoot:')
            return ASK_KOMOOT_LINK
            
    except Exception as e:
        logger.error(f"Исключение при скачивании GPX: {str(e)}", exc_info=True)
        await update.message.reply_text(f'Ошибка при скачивании GPX: {str(e)}. Попробуй другую ссылку на маршрут Komoot:')
        return ASK_KOMOOT_LINK
        
    # Проверяем, что файл действительно скачался
    gpx_files = glob.glob(f"{CACHE_DIR}/*-{tour_id}.gpx")
    if not gpx_files:
        logger.warning(f"GPX файл не найден для tour_id: {tour_id}")
        await update.message.reply_text('GPX-файл не найден. Попробуй другую ссылку на маршрут Komoot:')
        return ASK_KOMOOT_LINK
        
    gpx_path = gpx_files[0]
    logger.info(f"GPX файл найден: {gpx_path}")
    context.user_data['gpx_path'] = gpx_path
    
    try:
        with open(gpx_path, 'r') as f:
            gpx = gpxpy.parse(f)
        length_km = gpx.length_2d() / 1000
        uphill = gpx.get_uphill_downhill()[0]
        context.user_data['length_km'] = round(length_km)
        context.user_data['uphill'] = round(uphill)
        logger.info(f"GPX обработан: длина {length_km} км, набор {uphill} м")
    except Exception as e:
        logger.error(f"Ошибка при обработке GPX файла: {str(e)}", exc_info=True)
        await update.message.reply_text('Ошибка при обработке GPX-файла. Попробуй другую ссылку на маршрут Komoot:')
        return ASK_KOMOOT_LINK
        
    await update.message.reply_text('Введи название маршрута (например: Шайкаш - Чуруг - Србобран - Темерин):')
    return ASK_ROUTE_NAME

async def ask_route_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['route_name'] = update.message.text.strip()
    if context.user_data.get('edit_mode'):
        context.user_data['edit_mode'] = False
        return await preview_step(update, context)
    # Кнопки для выбора точки старта
    keyboard = [[p['name']] for p in START_POINTS]
    await update.message.reply_text(
        f"Маршрут: {context.user_data['length_km']} км, набор: {context.user_data['uphill']} м\n\nВыбери точку старта:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_START_POINT

async def ask_start_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    point_name = update.message.text.strip()
    point = next((p for p in START_POINTS if p['name'] == point_name), None)
    if not point:
        await update.message.reply_text('Пожалуйста, выбери точку старта из списка.')
        return ASK_START_POINT
    if point['name'] == 'Своя точка':
        context.user_data['start_point_name'] = None
        context.user_data['start_point_link'] = None
        await update.message.reply_text('Введи название своей точки старта:')
        return ASK_START_LINK
    else:
        context.user_data['start_point_name'] = point['name']
        context.user_data['start_point_link'] = point['link']
        if context.user_data.get('edit_mode'):
            context.user_data['edit_mode'] = False
            return await preview_step(update, context)
        keyboard = [[p] for p in PACE_OPTIONS]
        await update.message.reply_text(
            'Выбери ожидаемый темп (количество лун):',
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_PACE

async def ask_start_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Если не было имени, значит сейчас ждём имя, иначе ждём ссылку
    if not context.user_data.get('start_point_name'):
        context.user_data['start_point_name'] = update.message.text.strip()
        await update.message.reply_text('Введи ссылку на Google Maps для своей точки старта:')
        return ASK_START_LINK
    else:
        link = update.message.text.strip()
        if not (link.startswith('http://') or link.startswith('https://')):
            await update.message.reply_text('Пожалуйста, пришли корректную ссылку на Google Maps (начинается с http...)')
            return ASK_START_LINK
        context.user_data['start_point_link'] = link
        if context.user_data.get('edit_mode'):
            context.user_data['edit_mode'] = False
            return await preview_step(update, context)
        keyboard = [[p] for p in PACE_OPTIONS]
        await update.message.reply_text(
            'Выбери ожидаемый темп (количество лун):',
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_PACE

async def ask_pace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pace = update.message.text.strip()
    if pace not in PACE_OPTIONS:
        await update.message.reply_text('Пожалуйста, выбери темп из предложенных вариантов.')
        return ASK_PACE
    context.user_data['pace'] = pace
    
    # Проверяем быстрый режим
    if context.user_data.get('quick_mode'):
        # В быстром режиме после темпа сразу к предпросмотру
        context.user_data['quick_mode'] = False
        # Комментарий уже есть из готового маршрута
        return await preview_step(update, context)
    
    if context.user_data.get('edit_mode'):
        context.user_data['edit_mode'] = False
        return await preview_step(update, context)
    await update.message.reply_text(
        'Теперь напиши комментарий к анонсу (можно несколько строк):',
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_COMMENT

async def ask_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment = update.message.text.strip()
    context.user_data['comment'] = comment
    if context.user_data.get('edit_mode'):
        context.user_data['edit_mode'] = False
        return await preview_step(update, context)
    return await preview_step(update, context)

async def preview_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Формируем анонс
    date_time_str = context.user_data.get('date_time', '-')
    dt, error_msg = parse_date_time(date_time_str)
    if dt:
        weekday = RU_WEEKDAYS[dt.weekday()]
        time_of_day = get_time_of_day(dt)
        date_part = dt.strftime('%d.%m')
        time_part = dt.strftime('%H:%M')
    else:
        weekday = 'День недели?'
        time_of_day = 'время суток?'
        date_part = date_time_str
        time_part = ''
        if error_msg:
            await update.message.reply_text(error_msg, parse_mode='HTML')
            return ASK_DATE_TIME # Вернуться к запросу даты
    komoot_link = context.user_data.get('komoot_link', '-')
    route_name = context.user_data.get('route_name', '-')
    start_point_name = context.user_data.get('start_point_name', '-')
    start_point_link = context.user_data.get('start_point_link', '-')
    length_km = context.user_data.get('length_km', '-')
    uphill = context.user_data.get('uphill', '-')
    pace = context.user_data.get('pace', '-')
    comment = context.user_data.get('comment', '-')
    gpx_path = context.user_data.get('gpx_path', None)
    pace_emoji = pace.split(' ')[0] if pace else '-'
    announce = (
        f"<b>{weekday}, {date_part}, {time_of_day} ({time_part})</b>\n"
        f"Маршрут: {route_name} ↔️ {length_km} км ⛰ {uphill} м (<a href=\"{komoot_link}\">комут</a>)\n\n"
        f"Старт: <a href=\"{start_point_link}\">{start_point_name}</a>, выезд в {time_part}\n"
        f"Ожидаемый темп: {pace_emoji}\n"
        f"\n"
        f"{comment}"
    )
    # Кнопки предпросмотра
    buttons = [["✅ Отправить"]]
    for step, name in STEP_TO_NAME.items():
        buttons.append([name])
    await update.message.reply_text(
        announce + '\n\nВсё верно?',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True),
        disable_web_page_preview=True
    )
    return PREVIEW_STEP

async def preview_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    # Отправить — публикуем анонс и GPX
    if text == '✅ Отправить':
        # Формируем анонс (тот же код, что в preview_step)
        date_time_str = context.user_data.get('date_time', '-')
        dt, error_msg = parse_date_time(date_time_str)
        if dt:
            weekday = RU_WEEKDAYS[dt.weekday()]
            time_of_day = get_time_of_day(dt)
            date_part = dt.strftime('%d.%m')
            time_part = dt.strftime('%H:%M')
        else:
            weekday = 'День недели?'
            time_of_day = 'время суток?'
            date_part = date_time_str
            time_part = ''
            if error_msg:
                await update.message.reply_text(error_msg, parse_mode='HTML')
                return ASK_DATE_TIME # Вернуться к запросу даты
        komoot_link = context.user_data.get('komoot_link', '-')
        route_name = context.user_data.get('route_name', '-')
        start_point_name = context.user_data.get('start_point_name', '-')
        start_point_link = context.user_data.get('start_point_link', '-')
        length_km = context.user_data.get('length_km', '-')
        uphill = context.user_data.get('uphill', '-')
        pace = context.user_data.get('pace', '-')
        comment = context.user_data.get('comment', '-')
        gpx_path = context.user_data.get('gpx_path', None)
        pace_emoji = pace.split(' ')[0] if pace else '-'
        announce = (
            f"<b>{weekday}, {date_part}, {time_of_day} ({time_part})</b>\n"
            f"Маршрут: {route_name} ↔️ {length_km} км ⛰ {uphill} м (<a href=\"{komoot_link}\">комут</a>)\n\n"
            f"Старт: <a href=\"{start_point_link}\">{start_point_name}</a>, выезд в {time_part}\n"
            f"Ожидаемый темп: {pace_emoji}\n"
            f"\n"
            f"{comment}"
        )
        await update.message.reply_text(announce, parse_mode='HTML', disable_web_page_preview=True)
        if gpx_path:
            with open(gpx_path, 'rb') as f:
                await update.message.reply_document(f, filename=os.path.basename(gpx_path))
        
        # Отправляем финальное сообщение
        await update.message.reply_text(
            "✅ <b>Анонс создан, можешь переслать его друзьям.</b>\n\n"
            "🚴‍♂️ <b>Хорошей покатушки!</b>\n\n"
            "Используй /start для создания нового анонса.",
            parse_mode='HTML',
            reply_markup=ReplyKeyboardRemove()
        )
        
        return ConversationHandler.END
    # Если выбрана кнопка редактирования — возвращаем на нужный этап
    for step, name in STEP_TO_NAME.items():
        if text == name:
            context.user_data['edit_mode'] = True
            if step == ASK_DATE_TIME:
                await update.message.reply_text('Укажи дату и время старта:', reply_markup=ReplyKeyboardRemove())
                return ASK_DATE_TIME
            elif step == ASK_KOMOOT_LINK:
                await update.message.reply_text('Пришли публичную ссылку на маршрут Komoot:', reply_markup=ReplyKeyboardRemove())
                return ASK_KOMOOT_LINK
            elif step == ASK_ROUTE_NAME:
                await update.message.reply_text('Введи название маршрута:', reply_markup=ReplyKeyboardRemove())
                return ASK_ROUTE_NAME
            elif step == ASK_START_POINT:
                keyboard = [[p['name']] for p in START_POINTS]
                await update.message.reply_text('Выбери точку старта:', reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
                return ASK_START_POINT
            elif step == ASK_PACE:
                keyboard = [[p] for p in PACE_OPTIONS]
                await update.message.reply_text('Выбери ожидаемый темп (количество лун):', reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
                return ASK_PACE
            elif step == ASK_COMMENT:
                await update.message.reply_text('Введи комментарий:', reply_markup=ReplyKeyboardRemove())
                return ASK_COMMENT
    # Если что-то другое — повторяем предпросмотр
    return await preview_step(update, context)

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для сброса состояния и начала заново"""
    # Очищаем все данные пользователя
    context.user_data.clear()
    await update.message.reply_text(
        "Состояние сброшено! Начинаем заново.\n\n"
        "Используй /start для создания нового анонса.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для проверки статуса бота"""
    cache_files = glob.glob(f"{CACHE_DIR}/*.gpx")
    cache_size = len(cache_files)
    
    # Проверяем размер кэша
    total_size = 0
    if cache_files:
        total_size = sum(os.path.getsize(f) for f in cache_files)
    
    status_text = f"🤖 <b>Статус бота</b>\n\n"
    status_text += f"📁 Файлов в кэше: {cache_size}\n"
    status_text += f"💾 Размер кэша: {total_size / 1024:.1f} KB\n"
    status_text += f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}\n"
    status_text += f"📅 Дата: {datetime.now().strftime('%d.%m.%Y')}\n"
    
    if cache_size > 10:
        status_text += "\n⚠️ Много файлов в кэше! Используй /clear_cache"
    elif cache_size == 0:
        status_text += "\n✅ Кэш пуст"
    else:
        status_text += f"\n✅ Кэш в порядке ({cache_size} файлов)"
    
    status_text += "\n🔄 Кэш автоматически очищается раз в 180 дней"
    
    await update.message.reply_text(status_text, parse_mode='HTML')

def cleanup_old_gpx_files():
    """Автоматически очищает GPX файлы старше 180 дней"""
    try:
        current_time = datetime.now()
        cache_files = glob.glob(f"{CACHE_DIR}/*.gpx")
        deleted_count = 0
        
        for file_path in cache_files:
            try:
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if (current_time - file_time).days > 180:
                    os.remove(file_path)
                    logger.info(f"Автоматически удален старый файл: {file_path}")
                    deleted_count += 1
            except Exception as e:
                logger.error(f"Ошибка при проверке файла {file_path}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Автоматически очищено {deleted_count} старых GPX файлов")
            
    except Exception as e:
        logger.error(f"Ошибка при автоматической очистке: {e}")

async def preload_ready_routes():
    """Предварительно загружает все готовые маршруты в кеш"""
    logger.info("Начинаю предварительную загрузку готовых маршрутов в кеш...")
    
    for route in ROUTE_COMMENTS:
        try:
            # Извлекаем tour_id из ссылки
            match = KOMOOT_LINK_PATTERN.search(route['link'])
            if not match:
                logger.warning(f"Не удалось извлечь tour_id из ссылки: {route['link']}")
                continue
                
            tour_id = match.group(3)
            route_name = route['name']
            
            # Проверяем, есть ли уже файл в кеше
            gpx_files = glob.glob(f"{CACHE_DIR}/*-{tour_id}.gpx")
            if gpx_files:
                logger.info(f"Маршрут '{route_name}' уже в кеше, пропускаю")
                continue
            
            logger.info(f"Загружаю маршрут '{route_name}' (tour_id: {tour_id})")
            
            # Скачиваем GPX
            process = await asyncio.create_subprocess_exec(
                'komootgpx',
                '-d', tour_id,
                '-o', CACHE_DIR,
                '-e',
                '-n',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60.0)
                if process.returncode == 0:
                    logger.info(f"✅ Маршрут '{route_name}' успешно загружен в кеш")
                else:
                    error_msg = stderr.decode() if stderr else "Неизвестная ошибка"
                    logger.error(f"❌ Ошибка при загрузке маршрута '{route_name}': {error_msg}")
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Таймаут при загрузке маршрута '{route_name}', убиваю процесс")
                process.kill()
                
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при загрузке маршрута '{route.get('name', 'Unknown')}': {e}")
    
    logger.info("Предварительная загрузка готовых маршрутов завершена")

def preload_ready_routes_sync():
    """Синхронная версия предзагрузки готовых маршрутов для запуска при старте"""
    logger.info("Начинаю синхронную предзагрузку готовых маршрутов в кеш...")
    
    for route in ROUTE_COMMENTS:
        try:
            # Извлекаем tour_id из ссылки
            match = KOMOOT_LINK_PATTERN.search(route['link'])
            if not match:
                logger.warning(f"Не удалось извлечь tour_id из ссылки: {route['link']}")
                continue
                
            tour_id = match.group(3)
            route_name = route['name']
            
            # Проверяем, есть ли уже файл в кеше
            gpx_files = glob.glob(f"{CACHE_DIR}/*-{tour_id}.gpx")
            if gpx_files:
                logger.info(f"Маршрут '{route_name}' уже в кеше, пропускаю")
                continue
            
            logger.info(f"Загружаю маршрут '{route_name}' (tour_id: {tour_id})")
            
            # Скачиваем GPX синхронно
            import subprocess
            try:
                result = subprocess.run(
                    ['komootgpx', '-d', tour_id, '-o', CACHE_DIR, '-e', '-n'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    logger.info(f"✅ Маршрут '{route_name}' успешно загружен в кеш")
                else:
                    logger.error(f"❌ Ошибка при загрузке маршрута '{route_name}': {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                logger.warning(f"⏰ Таймаут при загрузке маршрута '{route_name}'")
            except FileNotFoundError:
                logger.error(f"❌ komootgpx не найден в системе")
                break
                
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при загрузке маршрута '{route.get('name', 'Unknown')}': {e}")
    
    logger.info("Синхронная предзагрузка готовых маршрутов завершена")

async def clear_cache_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для очистки кэша"""
    try:
        # Сначала очищаем старые файлы
        cleanup_old_gpx_files()
        
        cache_files = glob.glob(f"{CACHE_DIR}/*.gpx")
        deleted_count = 0
        
        for file_path in cache_files:
            try:
                os.remove(file_path)
                logger.info(f"Удален файл кэша: {file_path}")
                deleted_count += 1
            except Exception as e:
                logger.error(f"Ошибка при удалении {file_path}: {e}")
        
        if deleted_count == 0:
            await update.message.reply_text("🗑️ Кэш уже пуст!")
        else:
            await update.message.reply_text(f"🗑️ Кэш очищен! Удалено файлов: {deleted_count}")
        
    except Exception as e:
        logger.error(f"Ошибка при очистке кэша: {e}")
        await update.message.reply_text(f"❌ Ошибка при очистке кэша: {str(e)}")

if __name__ == '__main__':
    # Автоматически очищаем старые GPX файлы при запуске
    cleanup_old_gpx_files()
    
    # Предварительно загружаем все готовые маршруты в кеш
    preload_ready_routes_sync()
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем команды статуса и очистки кэша
    app.add_handler(CommandHandler('status', status_command))
    app.add_handler(CommandHandler('clear_cache', clear_cache_command))
    app.add_handler(CommandHandler('help', help_command))


    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('quick', quick_command)
        ],
        states={
            ASK_DATE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_date_time)],
            ASK_KOMOOT_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_komoot_link)],
            ASK_ROUTE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_route_name)],
            ASK_START_POINT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_start_point)],
            ASK_START_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_start_link)],
            ASK_PACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_pace)],
            ASK_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_comment)],
            PREVIEW_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, preview_handler)],
            SELECT_ROUTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_route_selection)],
        },
        fallbacks=[CommandHandler('restart', restart_command)],
    )
    app.add_handler(conv_handler)
    print('Bot started...')
    app.run_polling() 