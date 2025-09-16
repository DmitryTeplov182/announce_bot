#!/usr/bin/env python3
"""
Дашборд погоды для велосипедного маршрута
"""

import sys
import argparse
import gpxpy
import openmeteo_requests
import requests_cache
from retry_requests import retry
from datetime import datetime, timedelta
import os
import math
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch
import numpy as np
from PIL import Image, ImageDraw
import pytz

def get_timezone():
    """Получает временную зону из переменной окружения или возвращает Белград по умолчанию"""
    tz_name = os.getenv('TZ', 'Europe/Belgrade')
    try:
        return pytz.timezone(tz_name)
    except pytz.exceptions.UnknownTimeZoneError:
        print(f"⚠️ Неизвестная временная зона: {tz_name}, используем Europe/Belgrade")
        return pytz.timezone('Europe/Belgrade')

def get_route_points_with_time(gpx_file):
    """Получает точки маршрута с временными метками"""
    with open(gpx_file, 'r', encoding='utf-8') as f:
        gpx = gpxpy.parse(f)

    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                if point.time:
                    points.append({
                        'lat': point.latitude,
                        'lon': point.longitude,
                        'time': point.time,
                        'ele': point.elevation if point.elevation else 0
                    })
    
    # print(f"📍 Загружено {len(points)} точек маршрута с временными метками")  # Убрано для чистоты вывода
    return points

def calculate_route_time_points(points, start_time, speed_kmh=27):
    """Вычисляет точки маршрута через равные интервалы времени"""
    if not points:
        return []
    
    # Получаем временную зону
    tz = get_timezone()
    
    # Конвертируем start_time в нужную временную зону
    if start_time.tzinfo is None:
        start_time = tz.localize(start_time)
    else:
        start_time = start_time.astimezone(tz)
    
    # Конвертируем скорость в км/ч в м/с
    speed_ms = speed_kmh * 1000 / 3600
    
    # Вычисляем общее время маршрута
    total_distance = 0
    for i in range(1, len(points)):
        lat1, lon1 = points[i-1]['lat'], points[i-1]['lon']
        lat2, lon2 = points[i]['lat'], points[i]['lon']
        distance = calculate_distance(lat1, lon1, lat2, lon2)
        total_distance += distance
    
    # print(f"📏 Общая дистанция: {total_distance/1000:.2f} км")  # Убрано для чистоты вывода
    # print(f"⏱️  Время маршрута: {total_distance/speed_ms/3600:.2f} часов")  # Убрано для чистоты вывода
    
    # Разбиваем маршрут на интервалы по 6 км каждый
    interval_distance_km = 6.0  # 6 км между точками
    num_intervals = max(1, int(total_distance / 1000 / interval_distance_km))
    
    route_points = []
    for i in range(num_intervals):
        target_distance = (i + 1) * interval_distance_km * 1000  # в метрах
        
        # Находим точку на нужном расстоянии
        accumulated_distance = 0
        for j in range(1, len(points)):
            lat1, lon1 = points[j-1]['lat'], points[j-1]['lon']
            lat2, lon2 = points[j]['lat'], points[j]['lon']
            segment_distance = calculate_distance(lat1, lon1, lat2, lon2)
            
            if accumulated_distance + segment_distance >= target_distance:
                # Интерполируем точку на сегменте
                ratio = (target_distance - accumulated_distance) / segment_distance
                lat = lat1 + (lat2 - lat1) * ratio
                lon = lon1 + (lon2 - lon1) * ratio
                
                # Вычисляем время для этой точки
                time_offset = target_distance / speed_ms
                point_time = start_time + timedelta(seconds=time_offset)
                
                # Находим высоту для этой точки (интерполируем)
                ele = 0
                if j > 0 and j < len(points):
                    ele1 = points[j-1]['ele'] if 'ele' in points[j-1] else 0
                    ele2 = points[j]['ele'] if 'ele' in points[j] else 0
                    ele = ele1 + (ele2 - ele1) * ratio
                
                route_points.append({
                    'lat': lat,
                    'lon': lon,
                    'time': point_time,
                    'distance_km': target_distance / 1000,
                    'ele': ele
                })
                break
            
            accumulated_distance += segment_distance
    
    return route_points

def calculate_distance(lat1, lon1, lat2, lon2):
    """Вычисляет расстояние между двумя точками в метрах (формула Haversine)"""
    R = 6371000  # Радиус Земли в метрах
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def get_weather_data_for_route(route_points):
    """Получает данные о погоде для всех точек маршрута"""
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=3, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    
    weather_data = []
    
    # Определяем временной диапазон заезда
    start_time = min(point['time'] for point in route_points)
    end_time = max(point['time'] for point in route_points)
    
    # Добавляем небольшой буфер (1 час до и после)
    buffer = timedelta(hours=1)
    start_time = start_time - buffer
    end_time = end_time + buffer
    
    for i, point in enumerate(route_points):
        # print(f"🌪️  Получение данных о погоде {i+1}/{len(route_points)}...")  # Убрано для чистоты вывода
        
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": point['lat'],
            "longitude": point['lon'],
            "hourly": [
                "temperature_2m",
                "apparent_temperature", 
                "relative_humidity_2m",
                "wind_speed_10m",
                "wind_direction_10m",
                "pressure_msl",
                "weather_code",
                "precipitation_probability",
                "cloud_cover"
            ],
            "timezone": "auto",
            "start_date": start_time.strftime('%Y-%m-%d'),
            "end_date": end_time.strftime('%Y-%m-%d')
        }
        
        try:
            responses = openmeteo.weather_api(url, params=params)
            response = responses[0]
            
            hourly = response.Hourly()
            hourly_time = range(hourly.Time(), hourly.TimeEnd(), hourly.Interval())
            
            # Находим ближайший час
            target_timestamp = int(point['time'].timestamp())
            closest_time = None
            min_diff = float('inf')
            
            for j, timestamp in enumerate(hourly_time):
                time_diff = abs(timestamp - target_timestamp)
                if time_diff < min_diff:
                    min_diff = time_diff
                    closest_time = j
            
            if closest_time is None:
                weather_data.append(None)
                continue
            
            # Получаем данные для найденного времени
            hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
            hourly_apparent_temperature = hourly.Variables(1).ValuesAsNumpy()
            hourly_relative_humidity_2m = hourly.Variables(2).ValuesAsNumpy()
            hourly_wind_speed_10m = hourly.Variables(3).ValuesAsNumpy()
            hourly_wind_direction_10m = hourly.Variables(4).ValuesAsNumpy()
            hourly_pressure_msl = hourly.Variables(5).ValuesAsNumpy()
            hourly_weather_code = hourly.Variables(6).ValuesAsNumpy()
            hourly_precipitation_probability = hourly.Variables(7).ValuesAsNumpy()
            hourly_cloud_cover = hourly.Variables(8).ValuesAsNumpy()
            
            weather_data.append({
                'time': point['time'],
                'distance_km': point['distance_km'],
                'temperature': hourly_temperature_2m[closest_time],
                'feels_like': hourly_apparent_temperature[closest_time],
                'humidity': hourly_relative_humidity_2m[closest_time],
                'wind_speed': hourly_wind_speed_10m[closest_time],
                'wind_direction': hourly_wind_direction_10m[closest_time],
                'pressure': hourly_pressure_msl[closest_time],
                'weather_code': int(hourly_weather_code[closest_time]),
                'precipitation_probability': hourly_precipitation_probability[closest_time],
                'cloud_cover': hourly_cloud_cover[closest_time]
            })
            
        except Exception as e:
            # print(f"❌ Ошибка получения данных о ветре: {e}")  # Убрано для чистоты вывода
            weather_data.append(None)
    
    return weather_data

def create_weather_dashboard(route_points, weather_data, output_path="weather_dashboard.png", route_length_km=None):
    """Создает дашборд с графиками погоды в стиле Epic Ride Weather"""
    
    # Настройка стиля matplotlib для светлой темы
    plt.style.use('default')
    plt.rcParams.update({
        'font.size': 10,
        'axes.titlesize': 12,
        'axes.labelsize': 10,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 8,
        'figure.titlesize': 14,
        'axes.facecolor': 'white',
        'figure.facecolor': 'white',
        'axes.edgecolor': '#cccccc',
        'text.color': '#333333',
        'axes.labelcolor': '#333333',
        'xtick.color': '#333333',
        'ytick.color': '#333333',
        'font.weight': 'bold'  # Делаем все шрифты жирными
    })
    
    # Создаем фигуру для мобильного формата (узкая и длинная)
    fig = plt.figure(figsize=(10, 10))
    fig.patch.set_facecolor('white')
    
    # Фильтруем данные (убираем None)
    valid_data = [(p, w) for p, w in zip(route_points, weather_data) if w is not None]
    if not valid_data:
        print("❌ Нет данных о погоде для создания дашборда")
        return False
    
    route_points_clean, weather_data_clean = zip(*valid_data)
    
    # Вычисляем длину маршрута, если не передана
    if route_length_km is None:
        total_distance = 0
        for i in range(1, len(route_points_clean)):
            lat1, lon1 = route_points_clean[i-1]['lat'], route_points_clean[i-1]['lon']
            lat2, lon2 = route_points_clean[i]['lat'], route_points_clean[i]['lon']
            distance = calculate_distance(lat1, lon1, lat2, lon2)
            total_distance += distance
        route_length_km = total_distance / 1000
    
    times = [w['time'] for w in weather_data_clean]
    distances = [w['distance_km'] for w in weather_data_clean]
    
    # Заголовок дашборда убран
    
    # 1. Temperature (верхний левый)
    ax1 = plt.subplot(3, 2, 1)
    temperatures = [w['temperature'] for w in weather_data_clean]
    feels_like = [w['feels_like'] for w in weather_data_clean]
    
    ax1.plot(times, temperatures, color='#1f77b4', linewidth=4, label='Температура (°C)')
    ax1.plot(times, feels_like, color='#ff7f0e', linewidth=4, label='Ощущается (°C)')
    ax1.set_title('Температура', fontweight='bold', color='#333333')
    ax1.legend(loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3, linewidth=0.5)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax1.set_xlim(min(times), max(times))  # Ограничиваем ось X только временем заезда
    ax1.tick_params(colors='#333333')
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, fontsize=8)
    
    # 2. Precipitation and Cloud Cover (верхний правый)
    ax2 = plt.subplot(3, 2, 2)
    precipitation_prob = [max(0, w['precipitation_probability']) for w in weather_data_clean]  # Убираем отрицательные значения
    cloud_cover = [w['cloud_cover'] for w in weather_data_clean]
    
    # График осадков (столбчатая диаграмма)
    ax2.bar(times, precipitation_prob, alpha=0.7, color='#87ceeb', label='Вероятность (%)', width=0.8, zorder=5)
    ax2.set_ylim(0, 100)  # Ограничиваем от 0 до 100%
    ax2.set_xlim(min(times), max(times))  # Ограничиваем ось X только временем заезда
    
    # График облачности (линия на правой оси)
    ax2_twin = ax2.twinx()
    ax2_twin.plot(times, cloud_cover, color='#808080', linewidth=4, label='Облачность (%)', zorder=1)
    ax2_twin.set_ylim(0, 100)  # Ограничиваем от 0 до 100%
    ax2_twin.set_xlim(min(times), max(times))  # Ограничиваем ось X только временем заезда
    
    ax2.set_title('Осадки и Облачность', fontweight='bold', color='#333333')
    # Объединяем легенды на одной оси
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2_twin.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=8, 
                   framealpha=0.9, facecolor='white', edgecolor='gray')
    ax2.grid(True, alpha=0.3, linewidth=0.5)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax2.tick_params(colors='#333333')
    ax2_twin.tick_params(colors='#333333')
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, fontsize=8)
    
    # 3. Wind Direction Map (занимает 2 строки - средний и нижний левый)
    ax3 = plt.subplot(3, 2, (3, 5))
    
    # Получаем границы маршрута
    lats = [p['lat'] for p in route_points_clean]
    lons = [p['lon'] for p in route_points_clean]
    
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    # Добавляем отступы
    lat_range = max_lat - min_lat
    lon_range = max_lon - min_lon
    min_margin = 0.01
    
    lat_margin = max(lat_range * 0.1, min_margin)
    lon_margin = max(lon_range * 0.1, min_margin)
    
    # Адаптивные размеры элементов в зависимости от длины трека в км
    print(f"🔍 Длина трека: {route_length_km:.2f} км")
    
    if route_length_km < 20:  # Очень маленький трек (как example_route.gpx ~29км)
        arrow_scale = 0.04  # В 2 раза толще
        wind_arrow_scale = 0.025  # В 2 раза короче
        route_arrow_scale = 0.001
        print("📏 Используем размеры для маленького трека")
    elif route_length_km < 100:  # Средний трек
        arrow_scale = 0.01  # В 2 раза толще
        wind_arrow_scale = 0.017  # В 3 раза короче (0.05/3)
        route_arrow_scale = 0.002
        print("📏 Используем размеры для среднего трека")
    elif route_length_km < 200:  # Большой трек
        arrow_scale = 0.02  # В 2 раза толще
        wind_arrow_scale = 0.1  # В 2 раза короче
        route_arrow_scale = 0.005
        print("📏 Используем размеры для большого трека")
    else:  # Очень большой трек (≥200км)
        arrow_scale = 0.01  # Оригинальная толщина
        wind_arrow_scale = 0.1  # В 2 раза короче
        route_arrow_scale = 0.005
        print("📏 Используем размеры для очень большого трека")
    
    ax3.set_xlim(min_lon - lon_margin, max_lon + lon_margin)
    ax3.set_ylim(min_lat - lat_margin, max_lat + lat_margin)
    
    # Рисуем маршрут сплошной линией
    ax3.plot(lons, lats, '#ff6b6b', linewidth=3, zorder=5)
    
    # Добавляем стрелки направления на маршруте
    for i in range(0, len(lons)-1, 3):  # Каждые 3 точки для более частых стрелок
        if i + 1 < len(lons):
            # Вычисляем направление между точками
            dx_route = lons[i+1] - lons[i]
            dy_route = lats[i+1] - lats[i]
            length = math.sqrt(dx_route**2 + dy_route**2)
            
            if length > 0:
                # Нормализуем и масштабируем (адаптивная длина)
                dx_route = (dx_route / length) * route_arrow_scale
                dy_route = (dy_route / length) * route_arrow_scale
                
                # Рисуем стрелку направления (адаптивный размер головки)
                if route_length_km < 20:  # Маленький трек
                    head_size = route_arrow_scale * 1  # Маленькие стрелки для маленького трека
                elif route_length_km < 100:  # Средний трек
                    head_size = route_arrow_scale * 2
                else:  # Большой трек
                    head_size = route_arrow_scale * 5  # Большие стрелки для большого трека
                ax3.arrow(lons[i], lats[i], dx_route, dy_route,
                         head_width=head_size, head_length=head_size,
                         fc='#ff6b6b', ec='#ff6b6b', linewidth=2, zorder=5)
    
    # Рисуем стрелки ветра (от точек данных о погоде в направлении ветра)
    for i, (point, weather) in enumerate(zip(route_points_clean, weather_data_clean)):
        if weather and weather['wind_speed'] > 0:  # Каждая точка с данными о ветре
            wind_dir_rad = math.radians(weather['wind_direction'])
            wind_speed = weather['wind_speed']  # м/с
            
            # Адаптивный размер стрелки в зависимости от размера трека
            arrow_length = wind_arrow_scale
            
            # Направление ветра от точки данных
            # Конвертируем метеорологический угол в математический
            # В метеорологии: 0°=север, 90°=восток, 180°=юг, 270°=запад
            # В математике: 0°=восток, 90°=север, 180°=запад, 270°=юг
            math_angle_rad = wind_dir_rad - math.pi/2  # Поворачиваем на -90°
            
            # Стрелка показывает направление ветра от точки данных
            dx = arrow_length * math.cos(math_angle_rad)
            dy = arrow_length * math.sin(math_angle_rad)
            
            # Продлеваем стрелку за точку получения данных
            # Начало стрелки сдвигаем назад по направлению ветра
            start_x = point['lon'] - dx * 1.1  # Сдвигаем назад на 1.8 длины
            start_y = point['lat'] - dy * 1.1
            
            # Векторы с треугольниками (адаптивный размер)
            ax3.quiver(start_x, start_y, dx, dy, 
                      color='black', linewidth=4, alpha=0.8, zorder=5,
                      scale=1, scale_units='xy', angles='xy', width=arrow_scale)
    
    # Точки начала и конца
    ax3.plot(lons[0], lats[0], 'go', markersize=8, label='Старт', zorder=15)
    ax3.plot(lons[-1], lats[-1], 'ro', markersize=8, label='Финиш', zorder=15)
    
    ax3.set_title('Направление Ветра', fontweight='bold', color='#333333')
    ax3.set_xticks([])
    ax3.set_yticks([])
    ax3.legend(loc='upper right', fontsize=8, 
              framealpha=0.9, facecolor='white', edgecolor='gray')
    ax3.grid(False)
    
    # 4. Wind (средний правый)
    ax4 = plt.subplot(3, 2, 4)
    wind_speeds = [w['wind_speed'] for w in weather_data_clean]  # м/с
    
    ax4.plot(times, wind_speeds, color='#1f77b4', linewidth=4, label='Ветер (м/с)')
    ax4.set_title('Ветер', fontweight='bold', color='#333333')
    ax4.legend(loc='upper left', fontsize=8, 
              framealpha=0.9, facecolor='white', edgecolor='gray')
    ax4.grid(True, alpha=0.3, linewidth=0.5)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax4.set_xlim(min(times), max(times))  # Ограничиваем ось X только временем заезда
    ax4.tick_params(colors='#333333')
    plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, fontsize=8)
    
    # 5. Elevation (нижний правый)
    ax5 = plt.subplot(3, 2, 6)
    elevations = [p['ele'] for p in route_points_clean]
    
    ax5.fill_between(times, elevations, alpha=0.7, color='#ff7f0e')
    ax5.plot(times, elevations, color='#ff6b6b', linewidth=4)
    ax5.set_title('Высота', fontweight='bold', color='#333333')
    ax5.set_ylim(0, None)  # Минимальное значение высоты = 0
    ax5.grid(True, alpha=0.3, linewidth=0.5)
    ax5.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax5.set_xlim(min(times), max(times))  # Ограничиваем ось X только временем заезда
    ax5.tick_params(colors='#333333')
    plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45, fontsize=8)
    

    
    plt.tight_layout()
    plt.subplots_adjust(top=0.92, bottom=0.05)
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✅ Дашборд сохранен в: {output_path}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Дашборд погоды для велосипедного маршрута')
    parser.add_argument('gpx_file', help='Путь к GPX файлу')
    parser.add_argument('-o', '--output', default='weather_dashboard.png',
                       help='Файл для сохранения (по умолчанию: weather_dashboard.png)')
    parser.add_argument('-s', '--speed', type=float, default=27.0,
                       help='Скорость движения км/ч (по умолчанию: 27)')
    parser.add_argument('-d', '--date', default='06.09.2025',
                       help='Дата старта в формате ДД.ММ.ГГГГ (по умолчанию: 06.09.2025)')
    parser.add_argument('-t', '--time', default='08:30',
                       help='Время старта в формате ЧЧ:ММ (по умолчанию: 08:30)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.gpx_file):
        print(f"❌ Файл {args.gpx_file} не найден!")
        sys.exit(1)
    
    print("🌤️  Создание дашборда погоды для велосипедного маршрута")
    print(f"📁 Файл: {args.gpx_file}")
    print(f"🖼️  Выход: {args.output}")
    print(f"🚗 Скорость: {args.speed} км/ч")
    print()
    
    # Получаем точки маршрута
    points = get_route_points_with_time(args.gpx_file)
    if not points:
        print("❌ Не удалось загрузить точки маршрута")
        sys.exit(1)
    
    # Парсим дату и время из аргументов
    try:
        date_parts = args.date.split('.')
        if len(date_parts) != 3:
            raise ValueError("Неверный формат даты")
        
        day, month, year = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
        
        time_parts = args.time.split(':')
        if len(time_parts) != 2:
            raise ValueError("Неверный формат времени")
        
        hour, minute = int(time_parts[0]), int(time_parts[1])
        
        start_time = datetime(year, month, day, hour, minute, 0)
        print(f"🕐 Время старта: {start_time.strftime('%Y-%m-%d %H:%M')}")
        
    except (ValueError, IndexError) as e:
        print(f"❌ Ошибка в формате даты/времени: {e}")
        print("Используйте формат: -d ДД.ММ.ГГГГ -t ЧЧ:ММ")
        sys.exit(1)
    
    # Вычисляем точки маршрута через равные интервалы
    route_points = calculate_route_time_points(points, start_time, args.speed)
    print(f"📍 Точки для проверки погоды: {len(route_points)} (каждые 6 км)")
    
    # Получаем данные о погоде
    weather_data = get_weather_data_for_route(route_points)
    
    # Вычисляем длину маршрута
    total_distance = 0
    for i in range(1, len(route_points)):
        lat1, lon1 = route_points[i-1]['lat'], route_points[i-1]['lon']
        lat2, lon2 = route_points[i]['lat'], route_points[i]['lon']
        distance = calculate_distance(lat1, lon1, lat2, lon2)
        total_distance += distance
    route_length_km = total_distance / 1000
    
    # Создаем дашборд
    success = create_weather_dashboard(route_points, weather_data, args.output, route_length_km)
    
    if success:
        print("\n🎉 Готово! Дашборд погоды создан.")
        print("📊 Дашборд включает:")
        print("   💨 График скорости ветра (Wind)")
        print("   🌡️  График температуры (Temp)")
        print("   🗺️  Карта маршрута с направлением ветра")
    else:
        print("\n❌ Ошибка при создании дашборда")

if __name__ == "__main__":
    main()
