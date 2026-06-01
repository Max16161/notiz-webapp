from flask import Flask, request, render_template, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)


def db():
    return sqlite3.connect("notizen.db")


@app.route("/")
def home():
    q = request.args.get("q")

    conn = db()

    if q:
        notizen = conn.execute(
            "SELECT id, text, zeit FROM notizen WHERE text LIKE ? ORDER BY id DESC",
            ("%" + q + "%",)
        ).fetchall()
    else:
        notizen = conn.execute(
            "SELECT id, text, zeit FROM notizen ORDER BY id DESC"
        ).fetchall()

    conn.close()

    return render_template("index.html", notizen=notizen, q=q or "")


@app.route("/speichern", methods=["POST"])
def speichern():
    text = request.form["notiz"]
    zeit = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = db()
    conn.execute(
        "INSERT INTO notizen(text, zeit) VALUES(?, ?)",
        (text, zeit)
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


if __name__ == "__main__":
    app.run(debug=True)
