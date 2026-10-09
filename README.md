# Verbas — Flask + MySQL
Software, digital marketing and AI automation website.

## Run locally
    python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env     # then fill in your own values
    python app.py            # http://localhost:5000

The site works without a database or email key; the form then asks visitors to use WhatsApp or call.

## Deploy (Render)
Build: `pip install -r requirements.txt` · Start: `gunicorn app:app` · add every `.env.example` variable in the dashboard (`DB_SSL=true` for Aiven).

## Before launch
- Update the canonical URL and og:url in `templates/index.html` if the domain is not https://verbas.in
- Rotate the database password and Resend key that were in the old `.env`; never commit `.env`.
- Add real client logos, case studies and testimonials when available.
