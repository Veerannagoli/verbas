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
import time
from collections import defaultdict, deque
from html import escape

import pymysql
import pymysql.cursors
import resend
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request

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


HITS = defaultdict(deque)


def rate_limited(limit=5, window=3600):
    """Allow at most `limit` enquiries per IP per hour (in-memory, per worker)."""
    now, q = time.time(), HITS[client_ip()]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


@app.after_request
def security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return resp


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


# Dedicated, crawlable pages for the URLs already appearing in Google Search.
SEO_PAGES = {
    "about": {
        "title": "About Verbas Pvt Ltd | Software & Digital Growth Company",
        "description": "Learn about Verbas Private Limited, a software development and digital growth company helping businesses with websites, applications, digital marketing and AI automation.",
        "heading": "About Verbas Private Limited",
        "intro": "Verbas brings software development, digital marketing and practical AI automation together to help businesses build better digital experiences and grow with confidence.",
        "sections": [
            {"title": "One team for digital growth", "body": "From a business website or application to customer acquisition and workflow automation, we help connect the pieces into a practical digital plan."},
            {"title": "Business-first problem solving", "body": "We start by understanding your goals, users and everyday challenges, then recommend a solution with clear scope and realistic next steps."},
            {"title": "Built to evolve", "body": "Our focus is on useful, maintainable digital products and ongoing improvement as your business and customer needs change."},
        ],
        "cta": "Tell us what your business wants to improve and we will discuss the next steps.",
    },
    "services": {
        "title": "Software Development, Digital Marketing & AI Services | Verbas",
        "description": "Explore Verbas services: website and app development, custom software, e-commerce, SEO, paid advertising, social media, AI calling and workflow automation.",
        "heading": "Software, marketing and AI services",
        "intro": "Choose the support you need today and build from there. Verbas helps businesses create digital products, reach customers and automate repetitive work.",
        "sections": [
            {"title": "Software and product development", "body": "Website development, mobile app development, custom software, e-commerce experiences, dashboards and application integrations designed around your workflow."},
            {"title": "Digital marketing and customer growth", "body": "Search engine optimisation (SEO), social media management, Meta and Google advertising, email campaigns and content marketing to help you reach relevant audiences."},
            {"title": "AI and business automation", "body": "AI voice and communication, AI Tally Caller workflows, follow-up automation and custom AI integrations that can reduce repetitive manual tasks."},
        ],
        "cta": "Share your goals, preferred timeline and the service you are considering.",
    },
    "tanuku": {
        "title": "Software Development Company in Tanuku | Verbas",
        "description": "Verbas helps businesses in Tanuku and across India with website development, mobile apps, custom software, digital marketing and AI business automation.",
        "heading": "Software development company serving Tanuku",
        "intro": "Verbas supports businesses in Tanuku and the wider region with digital solutions built around real business needs—from an online presence to custom software and automation.",
        "sections": [
            {"title": "Websites and business applications", "body": "Create a professional website, customer-facing application, e-commerce store or internal tool that makes your services easier to discover and use."},
            {"title": "Digital marketing for visibility", "body": "Improve discoverability and customer engagement with SEO, social media, paid advertising and useful content aligned with your business goals."},
            {"title": "AI automation for everyday work", "body": "Explore workflow automation, AI voice solutions and custom integrations to streamline follow-ups and repetitive business processes."},
        ],
        "cta": "Tell us about your business in Tanuku and what you would like to build or improve.",
    },
    "careers": {
        "title": "Careers and Opportunities | Verbas",
        "description": "Connect with Verbas about future opportunities in software development, digital marketing and AI automation.",
        "heading": "Build useful digital experiences with Verbas",
        "intro": "We welcome conversations with people interested in software, digital growth and practical AI solutions. Contact us to share your skills and areas of interest.",
        "sections": [
            {"title": "Software and engineering", "body": "Areas of interest include web development, application engineering, integrations, testing and reliable delivery."},
            {"title": "Marketing and content", "body": "Areas of interest include SEO, social media, advertising, analytics and content that helps businesses communicate clearly."},
            {"title": "AI and automation", "body": "Areas of interest include workflow design, AI-enabled tools, business process improvement and responsible integrations."},
        ],
        "cta": "Email your profile and area of interest. This page does not represent a specific open vacancy.",
    },
    "privacy": {
        "title": "Privacy Policy | Verbas",
        "description": "Read how Verbas handles information submitted through its website enquiries and how to contact us about privacy questions.",
        "heading": "Privacy policy",
        "intro": "This page explains, in general terms, how Verbas may use information you submit through the website's project enquiry form.",
        "sections": [
            {"title": "Information you provide", "body": "If you contact us, we may receive details such as your name, email address, phone number, company, requested service and project message."},
            {"title": "How information is used", "body": "Enquiry information is used to respond to your request, discuss a potential project, maintain relevant business records and protect the website from misuse."},
            {"title": "Retention and questions", "body": "Information should be retained only for legitimate business, operational or legal needs. For a privacy-related question or request, contact verbas.pvt.ltd@gmail.com."},
        ],
        "cta": "For privacy questions, contact verbas.pvt.ltd@gmail.com.",
    },
}


@app.route("/about")
def about_page():
    return render_template("seo_page.html", page=SEO_PAGES["about"], slug="about")


@app.route("/services")
def services_page():
    return render_template("seo_page.html", page=SEO_PAGES["services"], slug="services")


@app.route("/tanuku")
def tanuku_page():
    return render_template("seo_page.html", page=SEO_PAGES["tanuku"], slug="tanuku")


@app.route("/careers")
def careers_page():
    return render_template("seo_page.html", page=SEO_PAGES["careers"], slug="careers")


@app.route("/privacy")
def privacy_page():
    return render_template("seo_page.html", page=SEO_PAGES["privacy"], slug="privacy")


@app.route("/api/contact", methods=["POST"])
def contact():
    data = request.get_json(silent=True) or {}
    if data.get("website"):  # honeypot: real visitors never fill this hidden field
        return jsonify(ok=True, message="Thank you — your enquiry has been sent."), 201
    if rate_limited():
        return jsonify(ok=False, message="Too many enquiries from this connection. Please use WhatsApp or call +91 99511 44669."), 429
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


@app.route("/robots.txt")
def robots():
    return Response(f"User-agent: *\nAllow: /\nSitemap: {request.url_root}sitemap.xml\n", mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    # Include only real, public HTML pages. API endpoints are intentionally excluded.
    urls = ["/", "/about", "/services", "/tanuku", "/careers", "/privacy"]
    items = "".join(
        f"<url><loc>{request.url_root.rstrip('/')}{path}</loc></url>"
        for path in urls
    )
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           f"{items}</urlset>")
    return Response(xml, mimetype="application/xml")


@app.errorhandler(404)
def not_found(_):
    # Keep unknown URLs as real 404 responses rather than returning the homepage as a 404.
    return render_template("not_found.html"), 404


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
