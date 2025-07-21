import os
import re
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)
import logging
import subprocess
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
    ASK_DATE_TIME: '✏️ дату',
    ASK_KOMOOT_LINK: '✏️ ссылку Komoot',
    ASK_ROUTE_NAME: '✏️ название',
    ASK_START_POINT: '✏️ старт',
    ASK_PACE: '✏️ темп',
    ASK_COMMENT: '✏️ коммен.',
}

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')

# Паттерн для извлечения tour_id из Komoot-ссылки
KOMOOT_LINK_PATTERN = re.compile(r'(https?://)?(www\.)?komoot\.[^/]+/tour/(\d+)')
CACHE_DIR = 'cache'
os.makedirs(CACHE_DIR, exist_ok=True)

# Предустановленные точки старта (заполнишь потом)
START_POINTS = [
    {'name': 'koferajd', 'link': 'https://maps.app.goo.gl/iTBcRqjvhJ9DYvRK7'},
    {'name': 'Флаги', 'link': 'https://maps.app.goo.gl/j95ME2cuzX8k9hnj7'},
    {'name': 'Лидл Лиман', 'link': 'https://maps.app.goo.gl/5JKtAgGBVe48jM9r7'},
    {'name': 'Железничка Парк', 'link': 'https://maps.app.goo.gl/hSZ9C4Xue5RVpMea8'},
    {'name': 'Своя точка', 'link': None},
]

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

def parse_date_time(date_time_str: str) -> datetime:
    # Ожидается формат: 19.07 10:00
    try:
        dt = datetime.strptime(date_time_str, '%d.%m %H:%M')
        # Подставляем текущий год
        dt = dt.replace(year=datetime.now().year)
        return dt
    except Exception:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tomorrow = datetime.now() + timedelta(days=1)
    date_example = tomorrow.strftime('%d.%m')
    await update.message.reply_text(
        f'Привет! Давай создадим анонс поездки.\n\n'
        f'Сначала укажи дату и время старта (например: `{date_example} 10:00`)',
        parse_mode='Markdown'
    )
    return ASK_DATE_TIME

async def ask_date_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сохраняем дату и время в user_data
    context.user_data['date_time'] = update.message.text.strip()
    if context.user_data.get('edit_mode'):
        context.user_data['edit_mode'] = False
        return await preview_step(update, context)
    await update.message.reply_text(
        'Теперь пришли публичную ссылку на маршрут Komoot (например: https://www.komoot.com/tour/1234567890):'
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
    try:
        subprocess.run([
            'komootgpx',
            '-d', tour_id,
            '-o', CACHE_DIR,
            '-e',
            '-n'
        ], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        await update.message.reply_text('Ошибка при скачивании GPX. Проверь, что маршрут публичный или попробуй другую ссылку.')
        await update.message.reply_text('Пришли другую публичную ссылку на маршрут Komoot:')
        return ASK_KOMOOT_LINK
    gpx_files = glob.glob(f"{CACHE_DIR}/*-{tour_id}.gpx")
    if not gpx_files:
        await update.message.reply_text('GPX-файл не найден. Попробуй другую ссылку на маршрут Komoot:')
        return ASK_KOMOOT_LINK
    gpx_path = gpx_files[0]
    context.user_data['gpx_path'] = gpx_path
    try:
        with open(gpx_path, 'r') as f:
            gpx = gpxpy.parse(f)
        length_km = gpx.length_2d() / 1000
        uphill = gpx.get_uphill_downhill()[0]
        context.user_data['length_km'] = round(length_km)
        context.user_data['uphill'] = round(uphill)
    except Exception as e:
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
    dt = parse_date_time(date_time_str)
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
        f"**{weekday}, {date_part}, {time_of_day} ({time_part})**\n"
        f"Маршрут: {route_name} ↔️ {length_km} км ⛰ {uphill} м комут ([ссылка]({komoot_link}))\n\n"
        f"Старт: [{start_point_name}]({start_point_link}), выезд в {time_part}\n"
        f"Ожидаемый темп: {pace_emoji}\n"
        f"\n"
        f"{comment}"
    )
    # Кнопки предпросмотра
    buttons = [["Отправить"]]
    for step, name in STEP_TO_NAME.items():
        buttons.append([name])
    await update.message.reply_text(
        announce + '\n\nВсё верно?',
        parse_mode='Markdown',
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
        dt = parse_date_time(date_time_str)
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
            f"**{weekday}, {date_part}, {time_of_day} ({time_part})**\n"
            f"Маршрут: {route_name} ↔️ {length_km} км ⛰ {uphill} м комут ([ссылка]({komoot_link}))\n\n"
            f"Старт: [{start_point_name}]({start_point_link}), выезд в {time_part}\n"
            f"Ожидаемый темп: {pace_emoji}\n"
            f"\n"
            f"{comment}"
        )
        await update.message.reply_text(announce, parse_mode='Markdown', disable_web_page_preview=True)
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

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
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
        fallbacks=[],
    )
    app.add_handler(conv_handler)
    print('Bot started...')
    app.run_polling() 