import sqlite3

db_name= "app.db"

def get_conn():
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn

conn = get_conn()
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash BLOB NOT NULL,
            role TEXT NOT NULL DEFAULT 'user' 
            )
""")
cur.execute(" UPDATE users SET role = 'admin' WHERE username = 'demo';")
user_columns = {
    row["name"]
    for row in cur.execute("PRAGMA table_info(users)").fetchall()
}
if "role" not in user_columns:
    cur.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
    
cur.execute("""
CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY  AUTOINCREMENT,
            user_id INTEGER,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
            )
""")
conn.commit()
conn.close()

def get_user_by_username(username):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cur.fetchone()

    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()

    conn.close()
    return user

def create_user_db(username, password_hash, role="user"):
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
            (username, password_hash, role)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return None
    conn.close()
    return True

def add_message(user_id, content):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("INSERT INTO messages(user_id, content) VALUES (?,?)",
                 (user_id, content)
)
    
    conn.commit()
    conn.close()


def list_messages():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT messages.id, messages.content, messages.created_at, users.username
        FROM messages
        LEFT JOIN users ON messages.user_id = users.id
        ORDER BY messages.created_at DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return rows
    

