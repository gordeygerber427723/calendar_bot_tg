import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "calendar.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                event_date TEXT NOT NULL,
                event_time TEXT NOT NULL DEFAULT '00:00',
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                timezone TEXT NOT NULL DEFAULT 'UTC',
                timezone_set INTEGER NOT NULL DEFAULT 0
            )
        """)

        # Проверяем существующие столбцы событий
        columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(events)"
            ).fetchall()
        }

        if "event_time" not in columns:
            conn.execute("""
                ALTER TABLE events
                ADD COLUMN event_time TEXT NOT NULL DEFAULT '00:00'
            """)

        if "daily_reminder" not in columns:
            conn.execute("""
                ALTER TABLE events
                ADD COLUMN daily_reminder INTEGER NOT NULL DEFAULT 0
            """)

        if "event_reminder_sent" not in columns:
            conn.execute("""
                ALTER TABLE events
                ADD COLUMN event_reminder_sent INTEGER NOT NULL DEFAULT 0
            """)

        # Проверяем существующие столбцы пользователей
        user_columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        }

        if "timezone_set" not in user_columns:
            conn.execute("""
                ALTER TABLE users
                ADD COLUMN timezone_set INTEGER NOT NULL DEFAULT 0
            """)

        if "last_reminder_date" not in user_columns:
            conn.execute("""
                ALTER TABLE users
                ADD COLUMN last_reminder_date TEXT
            """)


def save_event(
    user_id: int,
    title: str,
    event_date: str,
    event_time: str,
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO events (
                user_id, title, event_date, event_time
            )
            VALUES (?, ?, ?, ?)
            """,
            (user_id, title, event_date, event_time),
        )
        return cursor.lastrowid


def get_user_events(user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                title,
                event_date,
                event_time,
                description,
                daily_reminder
            FROM events
            WHERE user_id = ?
            ORDER BY event_date ASC, event_time ASC, id ASC
            """,
            (user_id,),
        ).fetchall()

        return [dict(row) for row in rows]


def get_user_event(user_id: int, event_id: int):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                id,
                title,
                event_date,
                event_time,
                description,
                daily_reminder
            FROM events
            WHERE user_id = ? AND id = ?
            """,
            (user_id, event_id),
        ).fetchone()

        return dict(row) if row else None


def delete_user_event(user_id: int, event_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM events
            WHERE id = ? AND user_id = ?
            """,
            (event_id, user_id),
        )
        return cursor.rowcount > 0


def set_daily_reminder(
    user_id: int,
    event_id: int,
    enabled: bool,
) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE events
            SET daily_reminder = ?
            WHERE user_id = ? AND id = ?
            """,
            (int(enabled), user_id, event_id),
        )
        return cursor.rowcount > 0


def get_reminder_events() -> list[dict]:
    """События с включёнными ежедневными напоминаниями."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, title, event_date, event_time
            FROM events
            WHERE daily_reminder = 1
            ORDER BY event_date ASC, event_time ASC
            """
        ).fetchall()

        return [dict(row) for row in rows]


def get_event_reminder_events() -> list[dict]:
    """События, для которых ещё не отправлено напоминание в день события."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, title, event_date, event_time
            FROM events
            WHERE event_reminder_sent = 0
            ORDER BY event_date ASC, event_time ASC
            """
        ).fetchall()

        return [dict(row) for row in rows]


def mark_event_reminder_sent(event_id: int):
    """Отмечает напоминание о событии как отправленное."""
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE events
            SET event_reminder_sent = 1
            WHERE id = ?
            """,
            (event_id,),
        )


def save_user_timezone(user_id: int, timezone: str):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (user_id, timezone, timezone_set)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id)
            DO UPDATE SET
                timezone = excluded.timezone,
                timezone_set = 1
            """,
            (user_id, timezone),
        )


def get_user_timezone(user_id: int) -> str:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT timezone FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    return row["timezone"] if row else "UTC"


def has_user_timezone(user_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT timezone_set FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    return bool(row["timezone_set"]) if row else False


def get_last_reminder_date(user_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT last_reminder_date FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    return row["last_reminder_date"] if row else None


def set_last_reminder_date(user_id: int, reminder_date: str):
    with get_connection() as conn:
        # Создаём запись пользователя, если её ещё нет.
        conn.execute(
            """
            INSERT INTO users (user_id, last_reminder_date)
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET last_reminder_date = excluded.last_reminder_date
            """,
            (user_id, reminder_date),
        )


if __name__ == "__main__":
    init_db()
    print(f"Database initialized: {DB_PATH}")