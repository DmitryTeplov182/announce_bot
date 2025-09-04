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
    
    print(f"📍 Загружено {len(points)} точек маршрута с временными метками")
    return points

def calculate_route_time_points(points, start_time, speed_kmh=27):
    """Вычисляет точки маршрута через равные интервалы времени"""
    if not points:
        return []
    
    # Конвертируем скорость в км/ч в м/с
    speed_ms = speed_kmh * 1000 / 3600
    
    # Вычисляем общее время маршрута
    total_distance = 0
    for i in range(1, len(points)):
        lat1, lon1 = points[i-1]['lat'], points[i-1]['lon']
        lat2, lon2 = points[i]['lat'], points[i]['lon']
        distance = calculate_distance(lat1, lon1, lat2, lon2)
        total_distance += distance
    
    print(f"📏 Общая дистанция: {total_distance/1000:.2f} км")
    print(f"⏱️  Время маршрута: {total_distance/speed_ms/3600:.2f} часов")
    
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
    
    for i, point in enumerate(route_points):
        print(f"🌪️  Получение данных о погоде {i+1}/{len(route_points)}...")
        
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
            "forecast_days": 2
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
            print(f"❌ Ошибка получения данных о ветре: {e}")
            weather_data.append(None)
    
    return weather_data

def create_weather_dashboard(route_points, weather_data, output_path="weather_dashboard.png"):
    """Создает дашборд с графиками погоды"""
    
    # Настройка стиля matplotlib
    plt.style.use('default')
    plt.rcParams.update({
        'font.size': 32,
        'axes.titlesize': 36,
        'axes.labelsize': 32,
        'xtick.labelsize': 28,
        'ytick.labelsize': 28,
        'legend.fontsize': 19,
        'figure.titlesize': 40
    })
    fig = plt.figure(figsize=(16, 10))
    fig.patch.set_facecolor('white')
    
    # Фильтруем данные (убираем None)
    valid_data = [(p, w) for p, w in zip(route_points, weather_data) if w is not None]
    if not valid_data:
        print("❌ Нет данных о погоде для создания дашборда")
        return False
    
    route_points_clean, weather_data_clean = zip(*valid_data)
    times = [w['time'] for w in weather_data_clean]
    distances = [w['distance_km'] for w in weather_data_clean]
    
    # График 1: Wind (верхний левый)
    ax1 = plt.subplot(2, 2, 1)
    wind_speeds = [w['wind_speed'] * 3.6 for w in weather_data_clean]  # м/с в км/ч
    wind_gusts = [w['wind_speed'] * 3.6 * 1.5 for w in weather_data_clean]  # Примерные порывы
    
    ax1.plot(times, wind_speeds, color='orange', linewidth=3, label='Wind')
    ax1.fill_between(times, wind_speeds, wind_gusts, alpha=0.3, color='darkorange', label='Gust')
    ax1.set_title('Wind (km/h)', fontweight='bold')
    ax1.set_ylabel('')
    ax1.legend()
    ax1.grid(True, alpha=0.3, linewidth=1)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    
    # График 2: Temperature (верхний правый)
    ax2 = plt.subplot(2, 2, 2)
    ax2.plot(times, [w['temperature'] for w in weather_data_clean], color='orange', linewidth=3)
    ax2.set_title('Temp (°C)', fontweight='bold')
    ax2.set_ylabel('')
    ax2.grid(True, alpha=0.3, linewidth=1)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    # График 3: Wind Direction Map (нижний, растянутый по горизонтали)
    ax3 = plt.subplot(2, 1, 2)
    
    # Получаем границы маршрута
    lats = [p['lat'] for p in route_points_clean]
    lons = [p['lon'] for p in route_points_clean]
    
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    # Добавляем отступы (адаптивные для коротких маршрутов)
    lat_range = max_lat - min_lat
    lon_range = max_lon - min_lon
    
    # Минимальные отступы для коротких маршрутов
    min_margin = 0.01  # Минимальный отступ в градусах
    
    lat_margin = max(lat_range * 0.1, min_margin)
    lon_margin = max(lon_range * 0.1, min_margin)
    
    ax3.set_xlim(min_lon - lon_margin, max_lon + lon_margin)
    ax3.set_ylim(min_lat - lat_margin, max_lat + lat_margin)
    
    # Рисуем маршрут
    ax3.plot(lons, lats, 'orange', linewidth=3)
    
    # Рисуем треугольники ветра
    for i, (point, weather) in enumerate(zip(route_points_clean, weather_data_clean)):
        if weather and weather['wind_speed'] > 0:
            wind_dir_rad = math.radians(weather['wind_direction'])
            
            # Длина сторон равнобедренного треугольника (компактная)
            # Фиксированный небольшой размер для всех маршрутов
            head_length = 0.008  # Фиксированный компактный размер
            head_angle = math.pi / 6  # 30 градусов

            # Вычисляем перпендикуляр к направлению ветра для треугольника
            perp_angle = wind_dir_rad + math.pi / 2
            
            # Левый угол треугольника (симметрично относительно направления ветра)
            left_lon = point['lon'] - head_length * math.cos(perp_angle - head_angle)
            left_lat = point['lat'] - head_length * math.sin(perp_angle - head_angle)
            
            # Правый угол треугольника
            right_lon = point['lon'] - head_length * math.cos(perp_angle + head_angle)
            right_lat = point['lat'] - head_length * math.sin(perp_angle + head_angle)
            
            # Рисуем равнобедренный треугольник с заливкой поверх маршрута
            ax3.fill([left_lon, point['lon'], right_lon], [left_lat, point['lat'], right_lat], 
                    color='black', alpha=1.0, zorder=10)
            
            # Добавляем линию от вершины через центр основания и дальше
            B_lon = point['lon']
            B_lat = point['lat']
            H_lon = (left_lon + right_lon) / 2
            H_lat = (left_lat + right_lat) / 2
            
            vec_lon = H_lon - B_lon
            vec_lat = H_lat - B_lat
            
            magnitude = math.sqrt(vec_lon**2 + vec_lat**2)
            if magnitude > 0:
                unit_vec_lon = vec_lon / magnitude
                unit_vec_lat = vec_lat / magnitude
                
                tail_length = head_length * 2
                end_lon = H_lon + unit_vec_lon * tail_length
                end_lat = H_lat + unit_vec_lat * tail_length
                
                ax3.plot([B_lon, end_lon], [B_lat, end_lat], 
                        color='black', linewidth=2, solid_capstyle='round', zorder=11)

    # Точки начала и конца (компактный размер)
    marker_size = 6  # Фиксированный компактный размер
    ax3.plot(lons[0], lats[0], 'go', markersize=marker_size, label='Start')
    ax3.plot(lons[-1], lats[-1], 'ro', markersize=marker_size, label='End')
    
    ax3.set_title('Wind Direction', fontweight='bold')
    ax3.set_xticks([])
    ax3.set_yticks([])
    ax3.legend()
    ax3.grid(False)
    
    plt.tight_layout()
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
    
    # Вычисляем время старта (завтра в 8:00)
    tomorrow = datetime.now() + timedelta(days=1)
    start_time = tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
    print(f"🕐 Время старта: {start_time.strftime('%Y-%m-%d %H:%M')}")
    
    # Вычисляем точки маршрута через равные интервалы
    route_points = calculate_route_time_points(points, start_time, args.speed)
    print(f"📍 Точки для проверки погоды: {len(route_points)} (каждые 6 км)")
    
    # Получаем данные о погоде
    weather_data = get_weather_data_for_route(route_points)
    
    # Создаем дашборд
    success = create_weather_dashboard(route_points, weather_data, args.output)
    
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
