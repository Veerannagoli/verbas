"""
Verbas — Flask backend

- Serves the website (templates/index.html)
- POST /api/contact           -> saves the enquiry to MySQL and emails it through Resend
- POST /api/whatsapp-enquiry  -> records a WhatsApp enquiry click (best effort)
- GET  /api/health            -> checks the app and the database

Run locally:  python app.py   (then open http://localhost:5000)
"""
import os
import re
from html import escape

import pymysql
import pymysql.cursors
import resend
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()
app = Flask(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "verbas"),
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
    "connect_timeout": 8,
}
# Aiven / most hosted MySQL need SSL. Set DB_SSL=false for a local MySQL.
if os.getenv("DB_SSL", "true").lower() == "true":
    DB_CONFIG["ssl"] = {"cert_reqs": 0}

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM = os.getenv("RESEND_FROM", "Verbas <onboarding@resend.dev>").strip()
MAIL_RECIPIENT = os.getenv("MAIL_RECIPIENT", "").strip()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SERVICES = {
    "Web Development", "App Development", "Software Development", "e-Commerce Development",
    "Application Services", "Social Media Handling", "Meta Ads", "Google Ads", "SEO",
    "E-mail Marketing", "Content Marketing", "AI Tally Caller", "AI Voice & Communication",
    "Workflow Automation", "Custom AI Integrations", "Not sure — need guidance",
}

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS contact_messages (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(120) NOT NULL,
        email VARCHAR(190) NOT NULL,
        phone VARCHAR(40) NULL,
        company VARCHAR(160) NULL,
        service VARCHAR(120) NOT NULL,
        timeline VARCHAR(60) NULL,
        message TEXT NOT NULL,
        ip_address VARCHAR(64) NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_created_at (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS whatsapp_enquiries (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        service VARCHAR(120) NULL,
        ip_address VARCHAR(64) NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_created_at (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]


def db():
    return pymysql.connect(**DB_CONFIG)


def ensure_tables():
    """Create the tables on start-up so no manual SQL step is needed."""
    try:
        conn = db()
        with conn, conn.cursor() as cur:
            for statement in SCHEMA:
                cur.execute(statement)
        app.logger.info("Database tables ready.")
    except Exception as exc:  # the site must still start without a database
        app.logger.warning("Database not ready: %s", exc)


def client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    return (forwarded.split(",")[0].strip() or request.remote_addr or "")[:64]


def clean(data, key, limit):
    return str(data.get(key) or "").strip()[:limit]


def send_email(p):
    if not (RESEND_API_KEY and MAIL_RECIPIENT):
        app.logger.warning("Email skipped: RESEND_API_KEY or MAIL_RECIPIENT missing.")
        return False
    try:
        resend.api_key = RESEND_API_KEY
        rows = "".join(
            f"<tr><td style='padding:6px 12px;color:#5b6b8c'>{label}</td>"
            f"<td style='padding:6px 12px'><b>{escape(value or '—')}</b></td></tr>"
            for label, value in [("Name", p["name"]), ("Email", p["email"]), ("Phone", p["phone"]),
                                 ("Company", p["company"]), ("Service", p["need"]), ("Timeline", p["timeline"])]
        )
        message = escape(p["message"]).replace("\n", "<br>")
        resend.Emails.send({
            "from": RESEND_FROM,
            "to": [MAIL_RECIPIENT],
            "reply_to": p["email"],
            "subject": f"Verbas enquiry: {p['need']} — {p['name']}",
            "html": (
                "<div style='font-family:Arial,sans-serif;color:#12244a;max-width:620px'>"
                "<h2 style='color:#0b2348'>New project enquiry</h2>"
                f"<table style='border-collapse:collapse;font-size:14px'>{rows}</table>"
                f"<h3 style='margin-top:20px'>Project details</h3><p style='line-height:1.6'>{message}</p></div>"
            ),
        })
        return True
    except Exception as exc:
        app.logger.exception("Resend failed: %s", exc)
        return False


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/contact", methods=["POST"])
def contact():
    data = request.get_json(silent=True) or {}
    p = {
        "name": clean(data, "name", 120), "email": clean(data, "email", 190),
        "phone": clean(data, "phone", 40), "company": clean(data, "company", 160),
        "need": clean(data, "need", 120), "timeline": clean(data, "timeline", 60),
        "message": clean(data, "message", 4000),
    }
    if not p["name"]:
        return jsonify(ok=False, message="Please enter your name."), 400
    if not EMAIL_RE.match(p["email"]):
        return jsonify(ok=False, message="Please enter a valid email address."), 400
    if p["need"] not in SERVICES:
        return jsonify(ok=False, message="Please choose the service you need."), 400
    if len(p["message"]) < 20:
        return jsonify(ok=False, message="Please tell us a little more about your project (at least 20 characters)."), 400

    saved = False
    try:
        conn = db()
        with conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO contact_messages (name,email,phone,company,service,timeline,message,ip_address)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (p["name"], p["email"], p["phone"] or None, p["company"] or None, p["need"],
                 p["timeline"] or None, p["message"], client_ip()),
            )
        saved = True
    except pymysql.MySQLError as exc:
        app.logger.exception("MySQL error: %s", exc)

    emailed = send_email(p)
    if saved or emailed:
        return jsonify(ok=True, message="Thank you — your enquiry has been sent. We will get back to you soon."), 201
    return jsonify(ok=False, message="We could not send your enquiry right now. Please use WhatsApp or call +91 99511 44669."), 500


@app.route("/api/whatsapp-enquiry", methods=["POST"])
def whatsapp_enquiry():
    data = request.get_json(silent=True) or {}
    try:
        conn = db()
        with conn, conn.cursor() as cur:
            cur.execute("INSERT INTO whatsapp_enquiries (service, ip_address) VALUES (%s,%s)",
                        (clean(data, "need", 120) or None, client_ip()))
    except pymysql.MySQLError as exc:
        app.logger.warning("WhatsApp enquiry not stored: %s", exc)
    return jsonify(ok=True), 201


@app.route("/api/health")
def health():
    try:
        conn = db()
        with conn, conn.cursor() as cur:
            cur.execute("SELECT 1 AS ok")
        return jsonify(status="ok", database="connected")
    except Exception:
        return jsonify(status="degraded", database="unreachable"), 500


ensure_tables()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")),
            debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
