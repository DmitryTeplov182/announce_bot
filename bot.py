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
ASK_DATE_TIME, ASK_KOMOOT_LINK, PROCESS_GPX, ASK_ROUTE_NAME, ASK_START_POINT, ASK_START_LINK, ASK_PACE, ASK_COMMENT, PREVIEW_STEP = range(9)

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
        with open('start_locations.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            start_points = data.get('start_points', [])
            
            # Автоматически добавляем "Свою точку" в конец списка
            start_points.append({
                'name': 'Своя точка',
                'link': None
            })
            
            return start_points
            
    except FileNotFoundError:
        logger.warning("Файл start_locations.json не найден, используем точки по умолчанию")
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
        logger.error(f"Ошибка при парсинге start_locations.json: {e}")
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tomorrow = datetime.now() + timedelta(days=1)
    date_example = tomorrow.strftime('%d.%m')
    await update.message.reply_text(
        f'🚴‍♂️ <b>Привет! Я бот для создания анонсов велопоездок</b>\n\n'
        f'Создам красивый анонс с маршрутом, точкой старта и всеми деталями.\n\n'
        f'<b>Основные команды:</b>\n'
        f'• /start - создать новый анонс\n'
        f'• /help - показать справку\n'
        f'• /cancel - отменить создание\n'
        f'• /restart - сбросить состояние\n\n'
        f'<b>Давай начнем!</b>\n\n'
        f'Укажи дату и время старта (например: <code>{date_example} 10:00</code>)',
        parse_mode='HTML'
    )
    return ASK_DATE_TIME

async def reload_locations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для перезагрузки точек старта из файла"""
    try:
        global START_POINTS
        START_POINTS = load_start_points()
        points_count = len(START_POINTS)
        await update.message.reply_text(
            f"🔄 Точки старта перезагружены!\n\n"
            f"📍 Загружено точек: {points_count}\n"
            f"📝 Список: {', '.join([p['name'] for p in START_POINTS])}"
        )
    except Exception as e:
        logger.error(f"Ошибка при перезагрузке точек старта: {e}")
        await update.message.reply_text(f"❌ Ошибка при перезагрузке: {str(e)}")

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
        "• /cancel - отменить создание\n"
        "• /restart - сбросить состояние\n\n"
        "<b>Точки старта:</b>\n"
        "• koferajd, Флаги, Лидл Лиман, Железничка Парк\n"
        "• Или укажи свою точку\n\n"
        "<b>Формат даты:</b> ДД.ММ ЧЧ:ММ (например: 19.07 10:00)"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для отмены создания анонса"""
    await update.message.reply_text(
        "❌ Создание анонса отменено.\n\n"
        "Используй /start для создания нового анонса.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

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
    
    if context.user_data.get('edit_mode'):
        context.user_data['edit_mode'] = False
        return await preview_step(update, context)
        
    await update.message.reply_text(
        '✅ Дата и время приняты!\n\n'
        'Теперь пришли <b>публичную</b> ссылку на маршрут Komoot (например: https://www.komoot.com/tour/2526993761):',
        parse_mode='HTML'
    )
    return ASK_KOMOOT_LINK

async def ask_komoot_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    match = KOMOOT_LINK_PATTERN.search(text)
    if not match:
        await update.message.reply_text(
            'Пожалуйста, пришли корректную публичную ссылку на маршрут Komoot (например: https://www.komoot.com/tour/1234567890)'
        )
        return ASK_KOMOOT_LINK
    context.user_data['komoot_link'] = text
    context.user_data['tour_id'] = match.group(3)
    if context.user_data.get('edit_mode'):
        context.user_data['edit_mode'] = False
        return await preview_step(update, context)
    await update.message.reply_text('Скачиваю маршрут и извлекаю данные...')
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
    if text == 'Отправить':
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
    
    await update.message.reply_text(status_text, parse_mode='HTML')

def cleanup_old_gpx_files():
    """Автоматически очищает GPX файлы старше 7 дней"""
    try:
        current_time = datetime.now()
        cache_files = glob.glob(f"{CACHE_DIR}/*.gpx")
        deleted_count = 0
        
        for file_path in cache_files:
            try:
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if (current_time - file_time).days > 7:
                    os.remove(file_path)
                    logger.info(f"Автоматически удален старый файл: {file_path}")
                    deleted_count += 1
            except Exception as e:
                logger.error(f"Ошибка при проверке файла {file_path}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Автоматически очищено {deleted_count} старых GPX файлов")
            
    except Exception as e:
        logger.error(f"Ошибка при автоматической очистке: {e}")

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
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем команды статуса и очистки кэша
    app.add_handler(CommandHandler('status', status_command))
    app.add_handler(CommandHandler('clear_cache', clear_cache_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('cancel', cancel_command))
    app.add_handler(CommandHandler('restart', restart_command)) # Добавляем команду restart
    app.add_handler(CommandHandler('reload_locations', reload_locations_command)) # Добавляем команду reload_locations
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_DATE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_date_time)],
            ASK_KOMOOT_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_komoot_link)],
            ASK_ROUTE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_route_name)],
            ASK_START_POINT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_start_point)],
            ASK_START_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_start_link)],
            ASK_PACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_pace)],
            ASK_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_comment)],
            PREVIEW_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, preview_handler)],
        },
        fallbacks=[CommandHandler('cancel', cancel_command)],
    )
    app.add_handler(conv_handler)
    print('Bot started...')
    app.run_polling() 