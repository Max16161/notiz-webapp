from flask import Flask, render_template, request, jsonify, redirect, session
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import re

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

DB = "chat.db"
ADMIN_NAME = "max"
ADMIN_PASSWORD = "admin123"

online_users = set()


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def column_exists(conn, table, column):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def clean_channel_name(name):
    name = name.strip().lower()
    name = name.replace(" ", "-")
    name = re.sub(r"[^a-z0-9äöüß_-]", "", name)
    return name[:30]


def init_db():
    conn = db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    if not column_exists(conn, "users", "role"):
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")

    if not column_exists(conn, "users", "banned"):
        conn.execute("ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            text TEXT NOT NULL,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    if not column_exists(conn, "messages", "channel"):
        conn.execute("ALTER TABLE messages ADD COLUMN channel TEXT DEFAULT 'allgemein'")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS presence (
            user TEXT PRIMARY KEY,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            admin_only INTEGER DEFAULT 0,
            protected INTEGER DEFAULT 0,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    default_channels = [
        ("allgemein", 0, 1),
        ("offtopic", 0, 0),
        ("support", 0, 0),
        ("admin", 1, 1)
    ]

    for name, admin_only, protected in default_channels:
        exists = conn.execute(
            "SELECT id FROM channels WHERE name = ?",
            (name,)
        ).fetchone()

        if not exists:
            conn.execute(
                "INSERT INTO channels (name, admin_only, protected) VALUES (?, ?, ?)",
                (name, admin_only, protected)
            )

    admin = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (ADMIN_NAME,)
    ).fetchone()

    if not admin:
        conn.execute(
            "INSERT INTO users (username, password, role, banned) VALUES (?, ?, 'admin', 0)",
            (ADMIN_NAME, generate_password_hash(ADMIN_PASSWORD))
        )
    else:
        conn.execute(
            "UPDATE users SET role = 'admin', banned = 0 WHERE username = ?",
            (ADMIN_NAME,)
        )

    conn.commit()
    conn.close()


def current_user():
    if "user" not in session:
        return None

    conn = db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (session["user"],)
    ).fetchone()
    conn.close()

    return user


def is_admin():
    user = current_user()
    return bool(user and user["role"] == "admin")


def get_visible_channels():
    user = current_user()

    if not user:
        return []

    conn = db()

    if user["role"] == "admin":
        rows = conn.execute(
            "SELECT name, admin_only, protected FROM channels ORDER BY id ASC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT name, admin_only, protected FROM channels WHERE admin_only = 0 ORDER BY id ASC"
        ).fetchall()

    conn.close()
    return [dict(row) for row in rows]


def can_access_channel(channel):
    user = current_user()

    if not user:
        return False

    conn = db()
    row = conn.execute(
        "SELECT * FROM channels WHERE name = ?",
        (channel,)
    ).fetchone()
    conn.close()

    if not row:
        return False

    if row["admin_only"] and user["role"] != "admin":
        return False

    return True


@app.route("/")
def index():
    user = current_user()

    if not user:
        return redirect("/login")

    return render_template(
        "index.html",
        user=user["username"],
        is_admin=user["role"] == "admin",
        channels=get_visible_channels()
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            return "Username und Passwort fehlen"

        conn = db()

        try:
            conn.execute(
                "INSERT INTO users (username, password, role, banned) VALUES (?, ?, 'user', 0)",
                (username, generate_password_hash(password))
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "User existiert schon"

        conn.close()
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if user and user["banned"]:
            return "Dieser Account ist gebannt"

        if user and check_password_hash(user["password"], password):
            session["user"] = username
            return redirect("/")

        return "Login falsch"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/channels")
def channels():
    if not current_user():
        return jsonify([]), 403

    return jsonify(get_visible_channels())


@app.route("/messages")
def messages():
    if not current_user():
        return jsonify([]), 403

    channel = request.args.get("channel", "allgemein")

    if not can_access_channel(channel):
        return jsonify([]), 403

    conn = db()
    rows = conn.execute("""
        SELECT id, user, text, created, channel
        FROM messages
        WHERE channel = ?
        ORDER BY id ASC
        LIMIT 300
    """, (channel,)).fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/admin/users")
def admin_users():
    if not is_admin():
        return jsonify({"error": "admin required"}), 403

    conn = db()
    rows = conn.execute("""
        SELECT username, role, banned
        FROM users
        ORDER BY role DESC, username ASC
    """).fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/admin/channels")
def admin_channels():
    if not is_admin():
        return jsonify({"error": "admin required"}), 403

    conn = db()
    rows = conn.execute("""
        SELECT name, admin_only, protected
        FROM channels
        ORDER BY id ASC
    """).fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/admin/create-channel", methods=["POST"])
def admin_create_channel():
    if not is_admin():
        return jsonify({"error": "admin required"}), 403

    data = request.get_json()

    name = clean_channel_name(data.get("name", ""))
    admin_only = 1 if data.get("admin_only") else 0

    if not name:
        return jsonify({"error": "invalid channel name"}), 400

    conn = db()

    try:
        conn.execute(
            "INSERT INTO channels (name, admin_only, protected) VALUES (?, ?, 0)",
            (name, admin_only)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "channel exists"}), 400

    conn.close()

    socketio.emit("channels_changed")

    return jsonify({"ok": True, "name": name})


@app.route("/admin/delete-channel", methods=["POST"])
def admin_delete_channel():
    if not is_admin():
        return jsonify({"error": "admin required"}), 403

    data = request.get_json()
    name = data.get("name", "")

    conn = db()

    channel = conn.execute(
        "SELECT * FROM channels WHERE name = ?",
        (name,)
    ).fetchone()

    if not channel:
        conn.close()
        return jsonify({"error": "channel not found"}), 404

    if channel["protected"]:
        conn.close()
        return jsonify({"error": "protected channel"}), 400

    conn.execute("DELETE FROM messages WHERE channel = ?", (name,))
    conn.execute("DELETE FROM channels WHERE name = ?", (name,))

    conn.commit()
    conn.close()

    socketio.emit("channels_changed")
    socketio.emit("chat_cleared", {"channel": name})

    return jsonify({"ok": True})


@app.route("/admin/delete-message", methods=["POST"])
def admin_delete_message():
    if not is_admin():
        return jsonify({"error": "admin required"}), 403

    data = request.get_json()
    msg_id = data.get("id")

    conn = db()
    conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()

    socketio.emit("message_deleted", {"id": msg_id})

    return jsonify({"ok": True})


@app.route("/admin/clear-chat", methods=["POST"])
def admin_clear_chat():
    if not is_admin():
        return jsonify({"error": "admin required"}), 403

    data = request.get_json()
    channel = data.get("channel", "allgemein")

    if not can_access_channel(channel):
        return jsonify({"error": "unknown channel"}), 400

    conn = db()
    conn.execute("DELETE FROM messages WHERE channel = ?", (channel,))
    conn.commit()
    conn.close()

    socketio.emit("chat_cleared", {"channel": channel})

    return jsonify({"ok": True})


@app.route("/admin/toggle-ban", methods=["POST"])
def admin_toggle_ban():
    if not is_admin():
        return jsonify({"error": "admin required"}), 403

    data = request.get_json()
    username = data.get("username")

    if username == ADMIN_NAME:
        return jsonify({"error": "admin cannot be banned"}), 400

    conn = db()

    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if not user:
        conn.close()
        return jsonify({"error": "user not found"}), 404

    new_status = 0 if user["banned"] else 1

    conn.execute(
        "UPDATE users SET banned = ? WHERE username = ?",
        (new_status, username)
    )

    conn.commit()
    conn.close()

    socketio.emit("admin_users_changed")

    return jsonify({"ok": True, "banned": new_status})


@socketio.on("connect")
def socket_connect():
    user = current_user()

    if not user:
        return False

    online_users.add(user["username"])

    conn = db()
    conn.execute(
        "INSERT OR REPLACE INTO presence (user, last_seen) VALUES (?, CURRENT_TIMESTAMP)",
        (user["username"],)
    )
    conn.commit()
    conn.close()

    emit("online_users", sorted(list(online_users)), broadcast=True)


@socketio.on("disconnect")
def socket_disconnect():
    username = session.get("user")

    if username in online_users:
        online_users.remove(username)

    emit("online_users", sorted(list(online_users)), broadcast=True)


@socketio.on("ping_presence")
def ping_presence():
    user = current_user()

    if not user:
        return

    online_users.add(user["username"])

    conn = db()
    conn.execute(
        "INSERT OR REPLACE INTO presence (user, last_seen) VALUES (?, CURRENT_TIMESTAMP)",
        (user["username"],)
    )
    conn.commit()
    conn.close()

    emit("online_users", sorted(list(online_users)), broadcast=True)


@socketio.on("send_message")
def socket_send_message(data):
    user = current_user()

    if not user:
        return

    if user["banned"]:
        emit("send_error", {"error": "Du bist gebannt."})
        return

    text = (data.get("text") or "").strip()
    channel = data.get("channel", "allgemein")

    if not can_access_channel(channel):
        emit("send_error", {"error": "Kein Zugriff auf diesen Raum."})
        return

    if not text:
        return

    conn = db()

    cur = conn.execute(
        "INSERT INTO messages (user, text, channel) VALUES (?, ?, ?)",
        (user["username"], text, channel)
    )

    msg_id = cur.lastrowid

    row = conn.execute(
        "SELECT id, user, text, created, channel FROM messages WHERE id = ?",
        (msg_id,)
    ).fetchone()

    conn.execute(
        "INSERT OR REPLACE INTO presence (user, last_seen) VALUES (?, CURRENT_TIMESTAMP)",
        (user["username"],)
    )

    conn.commit()
    conn.close()

    socketio.emit("new_message", dict(row))


if __name__ == "__main__":
    init_db()
    socketio.run(app, debug=True, host="127.0.0.1", port=5000)
