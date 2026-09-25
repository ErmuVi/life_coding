#  АДАЧА 2. Погодный сервис с кешем
#
# Использовать API:
# https://api.open-meteo.com/
#
# На вход программе передаётся список городов с координатами:
#
# cities = [
#     ("Batumi", 41.64, 41.63),
#     ("Tbilisi", 41.69, 44.80),
#     ("Berlin", 52.52, 13.41),
#     ("London", 51.50, -0.12),
# ]
#
# Нужно получить текущую температуру для каждого города.
#
# Требования:
# 1. HTTP-запросы к городам выполнять параллельно.
# 2. Использовать ThreadPoolExecutor.
# 3. Результаты сохранять в SQLite.
# 4. Реализовать кеш:
#       если данные для города моложе 10 минут,
#       HTTP-запрос делать не нужно.
# 5. При ошибке HTTP выполнить до 3 повторных попыток.
# 6. Между попытками использовать задержки:
#       1 секунда
#       2 секунды
#       4 секунды
# 7. Если API недоступен после всех попыток,
#    попробовать вернуть последнее сохранённое значение из БД.
#
# Пример вывода:
#
# Batumi: 24.3°C [API]
# Tbilisi: 27.1°C [CACHE]
# Berlin: 16.8°C [API]
# London: 14.2°C [STALE CACHE]
#
# Запрещено:
# - хранить кеш просто в dict;
# - делать запросы последовательно;
# - падать всей программой из-за ошибки одного города.

import time
import sqlite3
import requests
from concurrent.futures import ThreadPoolExecutor



def init_db():
    conn =sqlite3.connect("app1.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weather_cache (
        city_name TEXT PRIMARY KEY,
        temperature REAL,
        updated_at INTEGER
    );
    """)

    conn.commit()
    conn.close()



def fetch_weather_with_retry(lat: float, lon: float):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"

    for attempt in range(3):
        try:
            response = requests.get(url, timeout=2)
            response.raise_for_status()

            data = response.json()

            return data['current_weather']['temperature']

        except requests.exceptions.RequestException as e:

            if attempt == 2:
                print(f"Три попытки получить данные по координатам ({lat},{lon}) провалились.")
                
                return None

            sleep_time = 2 ** attempt

            print(f"Ошибка HTTP. Попытка {attempt + 1} не удалась. Ждем {sleep_time} сек...")
            time.sleep(sleep_time)



def process_city(city_info):
    name, lat, lon = city_info

    conn = sqlite3.connect("app1.db")
    cursor = conn.cursor()

    cursor.execute("SELECT temperature, updated_at FROM weather_cache WHERE city_name = ?", (name,))
    row = cursor.fetchone()

    current_time = int(time.time())

    if row is not None:
        db_temp, update_at = row

        if (current_time - update_at) < 600:
            conn.close()
            return f"{name}: {db_temp}°C [CACHE]"

    api_temp = fetch_weather_with_retry(lat, lon)

    if api_temp is not None:
        cursor.execute(
            "INSERT OR REPLACE INTO weather_cache (city_name, temperature, updated_at) VALUES (?, ?, ?)",
            (name, api_temp, current_time)
        )

        conn.commit()
        conn.close()
        return f"{name}: {api_temp}°C [API]"

    if row is not None:
        db_temp, update_at = row
        conn.close()
        return f"{name}: {db_temp}°C [STALE CACHE]"

    conn.close()

    return f"{name}: Ошибка [API НЕДОСТУПЕН]"



def main():
    init_db()

    cities = [
        ("Batumi", 41.64, 41.63),
        ("Tbilisi", 41.69, 44.80),
        ("Berlin", 52.52, 13.41),
        ("London", 51.50, -0.12),
    ]

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(process_city, cities)

        print("\nРезультаты:")

        for result in results:
            print(result)



if __name__ == "__main__":
    main()
