# ЗАДАЧА 2. Очередь задач для погодного сервиса
#
# Использовать Open-Meteo.
#
# В SQLite создать таблицы:
#
# cities:
# id
# name
# latitude
# longitude
#
# weather:
# id
# city_id
# temperature
# wind_speed
# created_at
#
# Добавить минимум 5 городов.
#
# Нужно:
# 1. Прочитать города из БД.
# 2. Для каждого города создать задачу на получение погоды.
# 3. Положить задачи в queue.Queue.
# 4. Запустить 3 worker-потока.
# 5. Каждый worker:
#    - берёт город из очереди;
#    - делает запрос в Open-Meteo;
#    - получает текущую температуру и скорость ветра;
#    - сохраняет результат в таблицу weather.
# 6. Worker не должен завершаться из-за ошибки одного запроса.
# 7. После выполнения всех задач вывести последнее измерение
#    для каждого города.
#
# Дополнительно:
# если температура изменилась больше чем на 5°C
# относительно предыдущего измерения, вывести:
#
# WARNING: Batumi temperature changed by 6.2°C
#
# Обязательно:
# - queue.Queue
# - threading
# - sqlite3
# - requests
# - обработка ошибок

import requests
import sqlite3
import threading
import queue
from datetime import datetime


CITIES_DATA = [
    ("Москва", 55.7558, 37.6173),
    ("Санкт-Петербург", 59.9343, 30.3351),
    ("Батуми", 41.6461, 41.6409),
    ("Тбилиси", 41.6941, 44.8337),
    ("Астана", 51.1605, 71.4704)
]



def init_db():
    with sqlite3.connect("weather.db") as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                latitude REAL,
                longitude REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_id INTEGER,
                temperature REAL,
                wind_speed REAL,
                created_at TEXT
            )
        """)

        cursor.execute("SELECT COUNT(*) FROM cities")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("""
                INSERT INTO cities (name, latitude, longitude) VALUES (?, ?, ?)
            """, CITIES_DATA)
            conn.commit()


def weather_worker(q):
    while True:
        city = q.get()
        if city is None:
            break
        city_id, city_name, lat, lon = city

        url = "https://api.open-meteo.com/v1/forecast" 

        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,wind_speed_10m"
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

            current_temp = data["current"]["temperature_2m"]
            current_wind = data["current"]["wind_speed_10m"]

            with sqlite3.connect("weather.db") as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT temperature FROM weather 
                    WHERE city_id = ? 
                    ORDER BY id DESC LIMIT 1
                """, (city_id,))
                result = cursor.fetchone()
                
                if result:
                    old_temp = result[0]
                    diff = abs(current_temp - old_temp)
                    if diff > 5.0:
                        print(f"\nWARNING: {city_name} temperature changed by {diff:.1f}°C")

                query = """
            INSERT INTO weather (city_id, temperature, wind_speed, created_at)
            VALUES (?, ?, ?, ?)
            """
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(query, (city_id, current_temp, current_wind, now))
            conn.commit()

        except requests.RequestException as e:
            print(f"Ошибка API для города {city_name}: {e}")
        except sqlite3.Error as e:
            print(f"Ошибка БД в потоке для города {city_name}: {e}")
        finally:
            q.task_done()

def main():
    init_db()
    q = queue.Queue()

    for _ in range(3):
        t = threading.Thread(target=weather_worker, args=(q,), daemon=True)
        t.start()

    with sqlite3.connect("weather.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, latitude, longitude FROM cities")
        cities = cursor.fetchall()

    for city in cities:
        q.put(city)

    q.join()

    print("\n--- Все задачи выполнены. Последние измерения: ---")

    with sqlite3.connect("weather.db") as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id, name FROM cities")
        cities_list = cursor.fetchall()
        
        for city_id, city_name in cities_list:
            cursor.execute("""
                SELECT temperature, wind_speed, created_at FROM weather
                WHERE city_id = ?
                ORDER BY id DESC
                LIMIT 1
            """, (city_id,))
            
            weather = cursor.fetchone()
            if weather:
                temp, wind, dt = weather
                print(f"Город: {city_name:15} -> {temp:5.1f}°C, скорость ветра: {wind:4.1f} м/с (Замерено: {dt})")


if __name__ == "__main__":
    main()