from flask import Flask, request, render_template, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

DB = "notizen.db"


def db():
    return sqlite3.connect(DB)


def init_db():
    conn = db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS notizen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            zeit TEXT NOT NULL DEFAULT ''
        )
    """)

    # 🔧 MIGRATION: falls alte DB existiert
    try:
        conn.execute("ALTER TABLE notizen ADD COLUMN zeit TEXT DEFAULT ''")
    except:
        pass

    conn.commit()
    conn.close()


init_db()


@app.route("/")
def home():
    q = request.args.get("q", "")

    conn = db()

    if q:
        notizen = conn.execute(
            "SELECT id, text, zeit FROM notizen WHERE text LIKE ? ORDER BY id DESC",
            (f"%{q}%",)
        ).fetchall()
    else:
        notizen = conn.execute(
            "SELECT id, text, zeit FROM notizen ORDER BY id DESC"
        ).fetchall()

    conn.close()

    return render_template("index.html", notizen=notizen, q=q)


@app.route("/speichern", methods=["POST"])
def speichern():
    text = request.form["notiz"]

    conn = db()
    conn.execute(
        "INSERT INTO notizen (text, zeit) VALUES (?, ?)",
        (text, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/loeschen/<int:id>")
def loeschen(id):
    conn = db()
    conn.execute("DELETE FROM notizen WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/")
