# ЗАДАЧА 1. Многопоточный сборщик статистики
#
# Использовать JSONPlaceholder:
# /users
# /posts?userId={id}
# /comments?postId={id}
#
# Нужно:
# 1. Получить всех пользователей.
# 2. Для каждого пользователя отдельный worker должен:
#    - получить его посты;
#    - получить комментарии к каждому посту;
#    - посчитать количество постов и комментариев.
# 3. Одновременно должно работать максимум 5 workers.
# 4. Результат сохранить в SQLite:
#
# user_stats:
# id
# user_id
# name
# posts_count
# comments_count
# updated_at
#
# 5. Повторный запуск не должен создавать дубликаты:
#    существующая статистика должна обновляться.
# 6. В конце вывести TOP-3 пользователей по количеству комментариев.
#
# Обязательно:
# - requests
# - ThreadPoolExecutor
# - sqlite3
# - timeout и обработка ошибок HTTP
#
# Пример:
# Leanne Graham | posts: 10 | comments: 50

import sqlite3
import requests
from concurrent.futures import ThreadPoolExecutor
from requests.exceptions import RequestException

def init_db():
    conn = sqlite3.connect('statistics.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,         -- Обязательно UNIQUE для защиты от дубликатов!
            name TEXT,
            posts_count INTEGER,
            comments_count INTEGER,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

def save_user_stats(user_id, name, posts_count, comments_count):
    conn = sqlite3.connect('statistics.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO user_stats (user_id, name, posts_count, comments_count, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, name, posts_count, comments_count))

    conn.commit()
    conn.close()


def get_top_users():
    conn = sqlite3.connect('statistics.db')
    cursor = conn.cursor()

    cursor.execute("SELECT name, comments_count FROM user_stats ORDER BY comments_count DESC LIMIT 3")
    top_users = cursor.fetchall()

    conn.commit()
    conn.close()
    return top_users

def get_all_users():
    url = "https://jsonplaceholder.typicode.com/users"
    try:
        response = requests.get(url, timeout=5)

        response.raise_for_status()

        return response.json()
    except RequestException as e:
        print(f"Ошибка при получении пользователей: {e}")
        return []

def worker_function(user):
    user_id = user['id']
    name = user['name']
    posts_url = f"https://jsonplaceholder.typicode.com//posts?userId={user_id}"
    response = requests.get(posts_url, timeout=5)
    posts_user = response.json()
    posts_count = len(posts_user)

    total_comments = 0

    for post in posts_user:
        post_id = post['id']
        url_com = f"https://jsonplaceholder.typicode.com/comments?postId={post_id}"
        res_com = requests.get(url_com, timeout=5)
        comments_list = res_com.json()

        total_comments += len(comments_list)

        save_user_stats(user_id, name, posts_count, total_comments)

if __name__ == "__main__":
    init_db()
    print("Получаем список пользователей из API...")
    users = get_all_users()

    if users:
        print(f"Найдено {len(users)} пользователей. Запускаем 5 потоков...")

        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(worker_function, users)
            
        print("Сбор данных завершен. Данные сохранены в базу!")

        print("\n=== TOP-3 ПОЛЬЗОВАТЕЛЕЙ ПО КОММЕНТАРИЯМ ===")
        top_3 = get_top_users()

        for index, row in enumerate(top_3, 1):
            print(f"{index}. {row[0]} | Всего комментариев: {row[1]}")

    else:
        print("Не удалось получить список пользователей. Проверьте интернет.")
