from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "🔥 FLASK LÄUFT WIRKLICH 🔥"

app.run(debug=True, port=5000)
