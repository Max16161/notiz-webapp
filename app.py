from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, emit
from flask_bcrypt import Bcrypt
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecret-key"

socketio = SocketIO(app, cors_allowed_origins="*")
bcrypt = Bcrypt(app)

DB = "chat.db"


def db():
    return sqlite3.connect(DB)


def init_db():
    conn = db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            text TEXT,
            zeit TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------------- AUTH ---------------- #

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        hashed = bcrypt.generate_password_hash(password).decode("utf-8")

        conn = db()
        try:
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed)
            )
            conn.commit()
        except:
            return "User existiert schon"

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if user and bcrypt.check_password_hash(user[2], password):
            session["user"] = username
            return redirect("/")
        else:
            return "Login fehlgeschlagen"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


# ---------------- CHAT ---------------- #

@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")

    return render_template("index.html", user=session["user"])


@socketio.on("send_message")
def handle_message(data):
    msg = {
        "name": data["name"],
        "text": data["text"],
        "zeit": datetime.now().strftime("%H:%M")
    }

    conn = db()
    conn.execute(
        "INSERT INTO messages (name, text, zeit) VALUES (?, ?, ?)",
        (msg["name"], msg["text"], msg["zeit"])
    )
    conn.commit()
    conn.close()

    emit("new_message", msg, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
