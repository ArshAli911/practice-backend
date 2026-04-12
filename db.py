import sqlite3
from contextlib import contextmanager

db_name = "app.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(db_name, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash BLOB NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user' 
                    )
        """)
        conn.execute("UPDATE users SET role = 'admin' WHERE username = 'demo'")
        user_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        if "role" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")

        conn.execute("""
        CREATE TABLE IF NOT EXISTS messages(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                    )
        """)


def get_user_by_username(username):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

def get_user_by_id(user_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

def create_user_db(username, password_hash, role="user"):
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
                (username, password_hash, role)
            )
    except sqlite3.IntegrityError:
        return None
    return True

def add_message(user_id, content):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages(user_id, content) VALUES (?,?)",
            (user_id, content)
        )


def list_messages(limit=None, offset=0):
    sql = """
        SELECT messages.id, messages.content, messages.created_at, users.username
        FROM messages
        LEFT JOIN users ON messages.user_id = users.id
        ORDER BY messages.created_at DESC
    """
    params = ()

    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params = (limit, offset)

    with get_conn() as conn:
        return conn.execute(sql, params).fetchall()


def count_messages():
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) AS total FROM messages").fetchone()["total"]
    
