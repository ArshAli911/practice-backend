import json
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
            password_hash BLOB NOT NULL
            )
""")
    
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

def get_user_by_username():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE id = ?", (id,))
    user = cur.fetchone()

    conn.close()
    return user

def create_user_db(username, password_hash):
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (?,?)",
            (username, password_hash)
        )


