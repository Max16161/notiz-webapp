from flask import Flask, request, render_template, redirect, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

DB = "chat.db"


def db():
    return sqlite3.connect(DB)


def init_db():
    conn = db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            text TEXT NOT NULL,
            zeit TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/messages")
def messages():
    conn = db()

    rows = conn.execute(
        "SELECT id, name, text, zeit FROM messages ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return jsonify({
        "messages": [
            {
                "id": r[0],
                "name": r[1],
                "text": r[2],
                "zeit": r[3]
            } for r in rows
        ]
    })


@app.route("/send", methods=["POST"])
def send():
    name = request.form["name"]
    text = request.form["text"]

    conn = db()
    conn.execute(
        "INSERT INTO messages (name, text, zeit) VALUES (?, ?, ?)",
        (name, text, datetime.now().strftime("%H:%M"))
    )
    conn.commit()
    conn.close()

    return ("ok", 200)
