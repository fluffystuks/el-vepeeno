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
                trial_used INTEGER DEFAULT 0,
                referred_by INTEGER DEFAULT NULL,
                paid_referrals_count INTEGER DEFAULT 0,
                FOREIGN KEY(referred_by) REFERENCES users(id)
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
                notified_level INTEGER DEFAULT 0,  -- 🟢 Добавлено
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

            CREATE TABLE IF NOT EXISTS bonuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                days INTEGER,
                reason TEXT,
                expiry_time INTEGER,
                status TEXT DEFAULT 'active',
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

def update_notified_level(key_id: int, level: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE keys SET notified_level = ? WHERE id = ?", (level, key_id))
        conn.commit()


def update_key_expiry(key_id: int, new_expiry: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE keys SET expiry_time = ? WHERE id = ?
        """, (new_expiry, key_id))
        conn.commit()

def reset_notified_level(key_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE keys SET notified_level = 0 WHERE id = ?", (key_id,))
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

def mark_notified(key_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE keys SET notified = 1 WHERE id = ?", (key_id,))
        conn.commit()

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


def count_successful_payments(user_id: int) -> int:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM payments WHERE user_id = ? AND status = 'succeeded'",
            (user_id,),
        )
        row = cursor.fetchone()
        return row[0] if row else 0

def reset_notification_flag(key_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE keys SET notified = 0 WHERE id = ?", (key_id,))
        conn.commit()


def get_expiring_keys():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        now = int(time.time() * 1000)
        cursor.execute("""
            SELECT keys.id, keys.user_id, keys.email, keys.expiry_time, users.tg_id, keys.notified_level
            FROM keys
            JOIN users ON keys.user_id = users.id
            WHERE keys.active = 1
        """)
        keys = []
        for row in cursor.fetchall():
            key_id, user_id, email, expiry_ms, tg_id, notified_level = row
            remaining = (expiry_ms // 1000) - int(time.time())
            keys.append({
                "key_id": key_id,
                "user_id": user_id,
                "tg_id": tg_id,
                "email": email,
                "expiry_time": expiry_ms,
                "remaining_seconds": remaining,
                "notified_level": notified_level
            })
        return keys
    
def deactivate_key(key_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE keys SET active = 0 WHERE id = ?", (key_id,))
        conn.commit()


def get_key_owner(key_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM keys WHERE id = ?", (key_id,))
        row = cursor.fetchone()
        return row[0] if row else None


def assign_referrer(user_id: int, referrer_id: int) -> bool:
    if user_id == referrer_id:
        return False
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT referred_by FROM users WHERE id = ?", (user_id,))
        current = cursor.fetchone()
        if current and current[0]:
            return False
        cursor.execute(
            "UPDATE users SET referred_by = ? WHERE id = ? AND referred_by IS NULL",
            (referrer_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_user_referrer(user_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT referred_by FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else None


def increment_paid_referrals(user_id: int) -> int:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET paid_referrals_count = paid_referrals_count + 1 WHERE id = ?",
            (user_id,),
        )
        conn.commit()
        cursor.execute(
            "SELECT paid_referrals_count FROM users WHERE id = ?", (user_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else 0


def get_paid_referrals_count(user_id: int) -> int:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT paid_referrals_count FROM users WHERE id = ?", (user_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else 0


def create_bonus(user_id: int, days: int, reason: str):
    expiry = int(time.time()) + 30 * 86400
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO bonuses (user_id, days, reason, expiry_time, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, days, reason, expiry, int(time.time())),
        )
        conn.commit()


def get_bonus(bonus_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, days, reason, expiry_time, status FROM bonuses WHERE id = ?",
            (bonus_id,),
        )
        row = cursor.fetchone()
        return row


def mark_bonus_used(bonus_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE bonuses SET status = 'used' WHERE id = ?",
            (bonus_id,),
        )
        conn.commit()


def expire_bonus(bonus_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE bonuses SET status = 'expired' WHERE id = ?",
            (bonus_id,),
        )
        conn.commit()


def get_user_active_bonuses(user_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        now = int(time.time())
        cursor.execute(
            """
            SELECT id, days, reason, expiry_time FROM bonuses
            WHERE user_id = ? AND status = 'active' AND expiry_time > ?
            ORDER BY expiry_time
            """,
            (user_id, now),
        )
        return cursor.fetchall()


def get_all_active_bonuses():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT bonuses.id, bonuses.user_id, bonuses.days, bonuses.reason,
                   bonuses.expiry_time, users.tg_id
            FROM bonuses
            JOIN users ON bonuses.user_id = users.id
            WHERE bonuses.status = 'active'
            """
        )
        result = []
        for row in cursor.fetchall():
            result.append(
                {
                    "id": row[0],
                    "user_id": row[1],
                    "days": row[2],
                    "reason": row[3],
                    "expiry_time": row[4],
                    "tg_id": row[5],
                }
            )
        return result
