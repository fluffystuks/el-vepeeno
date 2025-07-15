import sqlite3
import time

DB_NAME = "vpn_bot.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id TEXT UNIQUE,
                balance REAL DEFAULT 0,
                trial_used INTEGER DEFAULT 0  -- 🟢 Новое поле!
            );

            CREATE TABLE IF NOT EXISTS keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                email TEXT,
                key_link TEXT,
                expiry_time INTEGER,
                created_at INTEGER,
                active INTEGER DEFAULT 1,
                client_id TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                payment_id TEXT,
                amount REAL,
                status TEXT,
                created_at INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
        """)
        conn.commit()

def get_key_by_id(key_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT email, key_link, expiry_time, client_id, active
            FROM keys WHERE id = ?
        """, (key_id,))
        return cursor.fetchone()

def update_key_expiry(key_id: int, new_expiry: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE keys SET expiry_time = ? WHERE id = ?
        """, (new_expiry, key_id))
        conn.commit()

def activate_key(key_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE keys SET active = 1 WHERE id = ?
        """, (key_id,))
        conn.commit()


def get_all_keys(user_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, expiry_time, active FROM keys
            WHERE user_id = ?
        """, (user_id,))
        return cursor.fetchall()


def cancel_pending_payment(user_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE payments
            SET status = 'canceled'
            WHERE user_id = ? AND status = 'pending'
        """, (user_id,))
        conn.commit()


def is_trial_used(user_id: int) -> bool:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT trial_used FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return bool(row[0]) if row else False

def mark_trial_used(user_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET trial_used = 1 WHERE id = ?", (user_id,))
        conn.commit()

def get_or_create_user(tg_id: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, balance FROM users WHERE tg_id = ?", (tg_id,))
        row = cursor.fetchone()
        if row:
            return row[0], row[1]
        else:
            cursor.execute("INSERT INTO users (tg_id) VALUES (?)", (tg_id,))
            conn.commit()
            return cursor.lastrowid, 0

def update_balance(user_id: int, new_balance: float):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
        conn.commit()

def add_key(user_id, email, link, expiry_time, client_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO keys (user_id, email, key_link, expiry_time, created_at, active, client_id)
            VALUES (?, ?, ?, ?, strftime('%s','now'), 1, ?)
        """, (user_id, email, link, expiry_time, client_id))
        conn.commit()

def save_payment(user_id: int, payment_id: str, amount: float):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO payments (user_id, payment_id, amount, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, payment_id, amount, "pending", int(time.time())))
        conn.commit()

def get_last_payment_id(user_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT payment_id FROM payments
            WHERE user_id = ? AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        row = cursor.fetchone()
        return row[0] if row else None

def has_pending_payment(user_id: int) -> bool:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM payments
            WHERE user_id = ? AND status = 'pending'
        """, (user_id,))
        row = cursor.fetchone()
        return row[0] > 0 if row else False


def get_payment_amount(payment_id: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT amount FROM payments WHERE payment_id = ?
        """, (payment_id,))
        row = cursor.fetchone()
        return row[0] if row else 0


def update_payment_status(payment_id: str, status: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE payments SET status = ? WHERE payment_id = ?
        """, (status, payment_id))
        conn.commit()

def get_expiring_keys():
    """ Вернёт список ключей с инфой: сколько осталось """
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        now = int(time.time() * 1000)  # в миллисекундах
        cursor.execute("""
            SELECT keys.id, keys.user_id, keys.email, keys.expiry_time, users.tg_id
            FROM keys
            JOIN users ON keys.user_id = users.id
            WHERE keys.active = 1
        """)
        keys = []
        for row in cursor.fetchall():
            key_id, user_id, email, expiry_ms, tg_id = row
            remaining = (expiry_ms // 1000) - int(time.time())
            keys.append({
                "key_id": key_id,
                "user_id": user_id,
                "tg_id": tg_id,
                "email": email,
                "expiry_time": expiry_ms,
                "remaining_seconds": remaining
            })
        return keys

def deactivate_key(key_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE keys SET active = 0 WHERE id = ?", (key_id,))
        conn.commit()