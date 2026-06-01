import sqlite3

conn = sqlite3.connect("notizen.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS notizen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    zeit TEXT NOT NULL
)
""")

conn.commit()
conn.close()

print("✅ Datenbank erstellt / aktualisiert")
