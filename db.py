import sqlite3

conn = sqlite3.connect("app.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               username TEXT UNIQUE
               password_hash TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS message(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               user_id INTEGER
               message TEXT
)
""")

conn.commit()
conn.close()

