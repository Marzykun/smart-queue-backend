from flask import Flask, request, jsonify, g
from flask_cors import CORS
import sqlite3
from datetime import datetime
import os
import json
import requests

from google.oauth2 import service_account
from google.auth.transport.requests import Request

app = Flask(__name__)
CORS(app)

DB_NAME = os.path.join(os.path.dirname(__file__), "queue.db")

# ------------------ DATABASE ------------------

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            status TEXT,
            position INTEGER,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            phone TEXT PRIMARY KEY,
            token TEXT
        )
    """)

    conn.commit()
    conn.close()

# Flask 3 compatible "run once" hook
@app.before_request
def init_db_once():
    if not getattr(app, "db_init", False):
        init_db()
        app.db_init = True

def get_db():
	# return a sqlite3 connection with Row factory, stored on flask.g
	if not hasattr(g, "db"):
		conn = sqlite3.connect(DB_NAME, check_same_thread=False)
		conn.row_factory = sqlite3.Row
		g.db = conn
	return g.db

@app.teardown_appcontext
def close_connection(exception):
	db = g.pop("db", None)
	if db is not None:
		db.close()

# ------------------ FIREBASE AUTH ------------------

SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]

cred_json = os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]

credentials = service_account.Credentials.from_service_account_info(
    json.loads(cred_json),
    scopes=SCOPES
)

def get_access_token():
    auth_req = Request()
    credentials.refresh(auth_req)
    return credentials.token

# ------------------ API ROUTES ------------------

@app.route("/shops/<int:shop_id>/queue")
def get_queue(shop_id):
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM queue WHERE status='seated'")
    seated = [dict(row) for row in c.fetchall()]

    c.execute("SELECT * FROM queue WHERE status='waiting' ORDER BY position ASC")
    waiting = [dict(row) for row in c.fetchall()]

    return jsonify({"seated": seated, "waiting": waiting})

@app.route("/shops/<int:shop_id>/customers", methods=["POST"])
def add_customer(shop_id):
    data = request.json
    name = data["name"]
    phone = data["phone"]

    conn = get_db()
    c = conn.cursor()

    # count seated first 3
    c.execute("SELECT COUNT(*) FROM queue WHERE status='seated'")
    seated_count = c.fetchone()[0]

    if seated_count < 3:
        status = "seated"
        position = None
    else:
        status = "waiting"

        c.execute("SELECT COALESCE(MAX(position), 0)+1 FROM queue WHERE status='waiting'")
        position = c.fetchone()[0]

    c.execute("""
        INSERT INTO queue (name, phone, status, position, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (name, phone, status, position, datetime.now().isoformat()))

    conn.commit()
    conn.close()

    return jsonify({"message": "Customer added", "status": status})

@app.route("/queue/<int:entry_id>/finish", methods=["POST"])
def finish_customer(entry_id):
    conn = get_db()
    c = conn.cursor()

    c.execute("UPDATE queue SET status='done' WHERE id=?", (entry_id,))

    # get next waiting
    c.execute("""
        SELECT * FROM queue
        WHERE status='waiting'
        ORDER BY position ASC
        LIMIT 1
    """)
    next_waiting = c.fetchone()

    if next_waiting:
        next_id = next_waiting["id"]
        next_pos = next_waiting["position"]

        c.execute(
            "UPDATE queue SET status='seated', position=NULL WHERE id=?",
            (next_id,)
        )

        # shift positions of remaining waiting customers down by 1
        c.execute(
            "UPDATE queue SET position = position - 1 WHERE status='waiting' AND position > ?",
            (next_pos,)
        )

        # get phone for notification
        phone = next_waiting["phone"]

        # get FCM token for that phone
        c.execute("SELECT token FROM tokens WHERE phone=?", (phone,))
        row = c.fetchone()

        if row:
            send_push(row["token"], "Your turn!", "Please come inside the shop 😊")

    conn.commit()
    conn.close()

    return jsonify({"message": "Finished"})

# -------------- SAVE PUSH TOKEN ------------------

@app.route("/save_token", methods=["POST"])
def save_token():
    data = request.json
    phone = data["phone"]
    token = data["token"]

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        INSERT OR REPLACE INTO tokens (phone, token)
        VALUES (?, ?)
    """, (phone, token))

    conn.commit()
    conn.close()

    return jsonify({"message": "Token saved"})

# -------------- SEND PUSH ------------------

def send_push(token, title, body):
    access_token = get_access_token()

    message = {
        "message": {
            "token": token,
            "notification": {
                "title": title,
                "body": body
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    project_id = json.loads(cred_json)["project_id"]

    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

    requests.post(url, headers=headers, json=message)

# -------------- RUN ------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
