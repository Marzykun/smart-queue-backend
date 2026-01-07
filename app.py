from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
import requests

from google.oauth2 import service_account
from google.auth.transport.requests import Request


# ------------------------------
# Flask + CORS
# ------------------------------
app = Flask(__name__)
CORS(app)

DB_NAME = "queue.db"


# ------------------------------
# Firebase HTTP v1 Credentials
# ------------------------------
PROJECT_ID = "smart-queue-501ad"   # <-- change this

SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]

credentials = service_account.Credentials.from_service_account_file(
    "service_account.json",
    scopes=SCOPES
)


def get_access_token():
    creds = credentials.with_scopes(SCOPES)
    creds.refresh(Request())
    return creds.token


# ------------------------------
# SQLite helpers
# ------------------------------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER,
            name TEXT,
            phone TEXT,
            status TEXT,
            position INTEGER,
            push_token TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ------------------------------
# Send Push via HTTP v1
# ------------------------------
def send_push_v1(token, title, body):
    access_token = get_access_token()

    url = f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; UTF-8",
    }

    payload = {
        "message": {
            "token": token,
            "notification": {
                "title": title,
                "body": body
            }
        }
    }

    print("Sending push notification...")
    r = requests.post(url, headers=headers, data=json.dumps(payload))

    print("Status:", r.status_code)
    print("Response:", r.text)


# ------------------------------
# Get Queue
# ------------------------------
@app.route("/shops/<int:shop_id>/queue")
def get_queue(shop_id):
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM queue WHERE shop_id=? AND status='seated'", (shop_id,))
    seated = [dict(row) for row in c.fetchall()]

    c.execute("SELECT * FROM queue WHERE shop_id=? AND status='waiting' ORDER BY position", (shop_id,))
    waiting = [dict(row) for row in c.fetchall()]

    conn.close()

    return jsonify({"seated": seated, "waiting": waiting})


# ------------------------------
# Add Customer
# ------------------------------
@app.route("/shops/<int:shop_id>/customers", methods=["POST"])
def add_customer(shop_id):
    data = request.get_json()
    name = data["name"]
    phone = data["phone"]

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM queue WHERE shop_id=? AND status='seated'", (shop_id,))
    seated_count = c.fetchone()[0]

    if seated_count < 3:
        status = "seated"
        position = None
    else:
        status = "waiting"
        c.execute("SELECT COALESCE(MAX(position),0)+1 FROM queue WHERE shop_id=?", (shop_id,))
        position = c.fetchone()[0]

    c.execute(
        "INSERT INTO queue (shop_id, name, phone, status, position) VALUES (?, ?, ?, ?, ?)",
        (shop_id, name, phone, status, position)
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "customer added"})


# ------------------------------
# Save Push Token
# ------------------------------
@app.route("/save_token", methods=["POST"])
def save_token():
    data = request.get_json()
    phone = data["phone"]
    token = data["token"]

    conn = get_db()
    c = conn.cursor()

    c.execute("UPDATE queue SET push_token=? WHERE phone=?", (token, phone))

    conn.commit()
    conn.close()

    return jsonify({"message": "token saved"})


# ------------------------------
# Finish & notify next
# ------------------------------
@app.route("/queue/<int:entry_id>/finish", methods=["POST"])
def finish_customer(entry_id):
    conn = get_db()
    c = conn.cursor()

    # fetch the entry to get its shop_id
    c.execute("SELECT * FROM queue WHERE id=?", (entry_id,))
    entry = c.fetchone()
    if not entry:
        conn.close()
        return jsonify({"error": "entry not found"}), 404

    shop_id = entry["shop_id"]

    # mark finished
    c.execute("UPDATE queue SET status='done' WHERE id=?", (entry_id,))

    # find next waiting in the same shop
    c.execute(
        "SELECT * FROM queue WHERE shop_id=? AND status='waiting' ORDER BY position ASC LIMIT 1",
        (shop_id,)
    )
    next_waiting = c.fetchone()

    if next_waiting:
        next_id = next_waiting["id"]
        name = next_waiting["name"]
        token = next_waiting["push_token"]
        pos = next_waiting["position"]

        # move to seated
        c.execute("UPDATE queue SET status='seated', position=NULL WHERE id=?", (next_id,))

        # shift up positions for remaining waiting entries in the same shop
        if pos is not None:
            c.execute(
                "UPDATE queue SET position = position - 1 WHERE shop_id=? AND status='waiting' AND position > ?",
                (shop_id, pos)
            )

        # send push if token exists
        if token:
            send_push_v1(
                token,
                "Your turn has come",
                f"Hi {name}, please come to the shop now."
            )
        else:
            print("No push token for this user, skipping notification")

    conn.commit()
    conn.close()

    return jsonify({"message": "finished"})


# ------------------------------
# Run server
# ------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
