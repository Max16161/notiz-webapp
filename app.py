from flask import Flask, render_template, request, jsonify
import sqlite3
import os

app = Flask(__name__)
DB = "chat.db"


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if not os.path.exists(DB):
        with open("schema.sql") as f:
            conn = db()
            conn.executescript(f.read())
            conn.commit()
            conn.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/messages")
def messages():
    conn = db()
    rows = conn.execute(
        "SELECT * FROM messages ORDER BY created DESC LIMIT 50"
    ).fetchall()
    conn.close()

    return jsonify([dict(r) for r in rows])


@app.route("/send", methods=["POST"])
def send():
    data = request.get_json()
    user = data.get("user", "anon")
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "empty"}), 400

    conn = db()
    conn.execute(
        "INSERT INTO messages (user, text) VALUES (?, ?)",
        (user, text)
    )
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
