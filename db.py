import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bot.db")

DB_PATH = "bot.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user ON messages(user_id)")


def add_message(user_id, role, content):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )


def get_history(user_id, limit=20):
    """Последние limit сообщений в формате, который принимает LLM API."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE user_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def clear_history(user_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
        
def get_stats():
    with get_connection() as conn:
        users = conn.execute(
            "SELECT COUNT(DISTINCT user_id) FROM messages"
        ).fetchone()[0]

        questions = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE role = 'user'"
        ).fetchone()[0]

        by_day = conn.execute(
            "SELECT date(created_at) AS day, COUNT(*) "
            "FROM messages WHERE role = 'user' "
            "GROUP BY day ORDER BY day DESC LIMIT 7"
        ).fetchall()

        top_users = conn.execute(
            "SELECT user_id, COUNT(*) AS cnt "
            "FROM messages WHERE role = 'user' "
            "GROUP BY user_id ORDER BY cnt DESC LIMIT 3"
        ).fetchall()
        
        avg_length = conn.execute(
    "SELECT AVG(LENGTH(content)) FROM messages WHERE role = 'assistant'"
).fetchone()[0]

    return users, questions, by_day, top_users, avg_length
