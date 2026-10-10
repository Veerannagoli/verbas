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
from flask import Flask, jsonify, render_template, request, make_response

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


SITE_URL = "https://verbas.in"
SEO_PAGES = {
 "about": {"title":"About Verbas Pvt Ltd | Verbas","description":"Learn about Verbas Pvt Ltd, a software development and digital growth company.","heading":"About Verbas Pvt Ltd","intro":"Verbas brings software engineering, product thinking, design and digital growth together to help businesses build useful digital experiences.","sections":[("Our focus","We work across web development, application development, custom business software, e-commerce, digital marketing and AI-enabled business automation."),("How we work","We start by understanding the problem, users and desired outcome, then build maintainable solutions that can evolve as requirements change."),("Technology and growth","Verbas brings software development and digital growth services together to help businesses strengthen their digital presence.")]},
 "services": {"title":"Software Development, Digital Marketing & AI Automation | Verbas","description":"Explore Verbas web development, app development, custom software, digital marketing, SEO and AI business automation services.","heading":"Services by Verbas","intro":"Digital services designed around business needs—from building online experiences to improving visibility and automating repeatable workflows.","sections":[("Software development","Web development, mobile apps, custom software, e-commerce websites, dashboards, integrations and business applications."),("Digital marketing","Social media handling, Meta Ads, Google Ads, SEO, email marketing and content marketing."),("AI business automation","AI-assisted voice workflows, communication automation, workflow automation and integrations with existing business systems.")]},
 "tanuku": {"title":"Software Development Company in Tanuku | Verbas","description":"Verbas helps businesses in Tanuku with websites, applications, custom software, digital marketing, SEO and AI business automation.","heading":"Software Development Company in Tanuku","intro":"Verbas supports businesses in Tanuku and nearby areas with digital solutions that improve online presence, customer experiences and business workflows.","sections":[("Website and app development","Build responsive business websites, web applications and mobile-friendly digital experiences."),("Custom business software","Plan business applications, dashboards, workflow tools and integrations around the way your team works."),("Digital marketing and SEO","Improve online visibility with search-friendly website content, SEO, social media and advertising campaigns."),("AI workflow automation","Explore practical automation for repetitive tasks, communication workflows and connections between software tools.")]},
 "careers": {"title":"Careers | Verbas","description":"Enquire about future career and collaboration opportunities with Verbas.","heading":"Careers at Verbas","intro":"We welcome enquiries from people interested in software, digital experiences, marketing and business automation.","sections":[("Areas of interest","Software development, web design, application development, digital marketing, content and AI-enabled workflows."),("Contact us","Email your profile, skills and the type of opportunity you are looking for to verbas.pvt.ltd@gmail.com.")]},
 "privacy": {"title":"Privacy Policy | Verbas","description":"Read the Verbas website privacy policy for information submitted through project enquiry forms.","heading":"Privacy Policy","intro":"This policy explains in general terms how information submitted through the Verbas website may be handled.","sections":[("Information you provide","Project enquiries may include your name, email address, phone number, company, service interest and message."),("How information is used","Information is used to respond to enquiries, communicate about requested services and maintain website operation and security."),("Contact and updates","For privacy-related questions, contact verbas.pvt.ltd@gmail.com. This policy may be updated as website features change.")]},
 "blog": {"title":"Blog | Verbas — Software, Marketing & AI Automation","description":"Insights from Verbas on software development, digital marketing, SEO and AI business automation.","heading":"Ideas on software, growth and automation","intro":"Practical topics to help businesses make informed decisions about digital products, marketing and automation.","sections":[("Custom software or off-the-shelf?","Compare business processes, team needs, budget and long-term plans before deciding whether to build custom software."),("SEO foundations for local businesses","Useful pages, clear service information, crawlable links and consistent business details help search engines understand a website."),("Where AI automation fits","Start with repetitive, measurable workflows and evaluate reliability before scaling automation.")]}
}

PAGE_META = {
    "home": ("Verbas | Software, Digital Marketing & AI Business Automations", "Verbas Private Limited helps businesses with website and app development, custom software, digital marketing, SEO and AI business automation.", "https://verbas.in/"),
    "services": ("What We Do | Software, Marketing & AI Automation | Verbas", "Explore Verbas software development, digital marketing and AI business automation services.", "https://verbas.in/services"),
    "approach": ("Our Approach | Verbas Private Limited", "Learn how Verbas understands business needs, designs with purpose, builds maintainable solutions and improves continuously.", "https://verbas.in/approach"),
    "about": ("About Verbas Private Limited", "Learn about Verbas Private Limited, a software development and digital growth company.", "https://verbas.in/about"),
    "blog": ("Blog | Verbas — Software, Marketing & AI Automation", "Ideas and practical guidance from Verbas on software development, digital marketing and AI business automation.", "https://verbas.in/blog"),
    "contact": ("Contact & Project Enquiry | Verbas", "Contact Verbas Private Limited to discuss website development, software, digital marketing or AI automation projects.", "https://verbas.in/contact"),
}

def render_main_page(template, current_page):
    title, description, canonical = PAGE_META[current_page]
    return render_template(template, current_page=current_page, page_title=title,
                           page_description=description, page_canonical=canonical)

@app.route("/")
def home():
    return render_main_page("index.html", "home")

@app.route("/services")
def services():
    return render_main_page("services.html", "services")

@app.route("/approach")
def approach():
    return render_main_page("approach.html", "approach")

def seo_page(slug):
    page = dict(SEO_PAGES[slug])
    page["sections"] = [{"heading": h, "body": b} for h, b in page["sections"]]
    return render_template("site_page.html", page=page, page_slug=slug)

@app.route("/about")
def about():
    return render_main_page("about.html", "about")

@app.route("/tanuku")
def tanuku():
    return seo_page("tanuku")

@app.route("/careers")
def careers():
    return seo_page("careers")

@app.route("/privacy")
def privacy():
    return seo_page("privacy")

@app.route("/blog")
def blog():
    return render_main_page("blog.html", "blog")

@app.route("/contact")
def contact_page():
    return render_main_page("contact.html", "contact")

@app.route("/sitemap.xml")
def sitemap():
    paths = ["", "/services", "/approach", "/about", "/blog", "/contact", "/tanuku", "/careers", "/privacy"]
    urls = "".join(f"<url><loc>{SITE_URL}{p}</loc></url>" for p in paths)
    response = make_response('<?xml version="1.0" encoding="UTF-8"?>' + '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + '</urlset>')
    response.headers["Content-Type"] = "application/xml; charset=utf-8"
    return response

@app.route("/robots.txt")
def robots():
    response = make_response("User-agent: *\nAllow: /\nSitemap: https://verbas.in/sitemap.xml\n")
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


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
