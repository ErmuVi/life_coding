# ЗАДАЧА 1. Синхронизация API -> SQLite
#
# API:
# https://jsonplaceholder.typicode.com/users
# https://jsonplaceholder.typicode.com/posts
#
# Нужно:
# 1. Получить пользователей и посты через HTTP.
# 2. Создать SQLite БД app.db.
# 3. Создать таблицы users и posts со связью FOREIGN KEY.
# 4. Сохранить полученные данные в БД.
# 5. Повторный запуск программы не должен создавать дубликаты.
# 6. Все изменения БД выполнить внутри транзакции.
# 7. После синхронизации вывести TOP-3 пользователей по количеству постов.
#
# Дополнительно:
# - timeout для HTTP-запросов;
# - обработка HTTP ошибок;
# - rollback транзакции при ошибке;
# - использовать параметры SQL, а не собирать запросы через f-string.
#
# Пример результата:
# Leanne Graham: 10 posts
# Ervin Howell: 10 posts
# Clementine Bauch: 10 posts


# ============================================================
import requests
import sqlite3


def fetch_data(url: str):
    try:
        response = requests.get(url, timeout=2)

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе а {url}: {e}")
        return None



def main():
    users_data = fetch_data("https://jsonplaceholder.typicode.com/users")
    posts_data = fetch_data("https://jsonplaceholder.typicode.com/posts")

    if not users_data or not posts_data:
        print("Не удалось получить данные из API. Выход.")
        return

    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys = ON")


        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            title TEXT,
            body TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """)

        for user in users_data:
            cursor.execute(
                "INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)",
                (user['id'], user['name'])
            )

        for post in posts_data:
                cursor.execute(
                    "INSERT OR IGNORE INTO posts (id, user_id, title, body) VALUES (?, ?, ?, ?)",
                    (post['id'], post['userId'], post['title'], post['body'])
                )

        conn.commit()
        print("Данные успешно синхронизированы в app.db!")

        cursor.execute("""
        SELECT users.name, COUNT(posts.id) AS post_count
        FROM users
        JOIN posts ON users.id = posts.user_id
        GROUP BY users.id
        ORDER BY post_count DESC
        LIMIT 3;
        """)

        top_users = cursor.fetchall()

        for name, count in top_users:
            print(f"{name}: {count} posts")

    except Exception as e:
        conn.rollback()

        print(f"Ошибка базы данных, транзакция отменена: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()