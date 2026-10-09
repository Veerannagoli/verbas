# Verbas — Flask + MySQL

Software development, digital marketing and AI business automation website.

## Layout
```
app.py                  Flask app (site + /api/contact + /api/whatsapp-enquiry + /api/health)
requirements.txt
.env.example            copy to .env and fill in
database/schema.sql     optional - app.py creates the tables automatically
templates/index.html
static/css/style.css
static/js/script.js
static/img/             verbas-logo.png (replace with your real logo) and favicon.svg
```

## Run locally
```
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # macOS/Linux: cp .env.example .env
python app.py
```
Open http://localhost:5000

The site loads even without a database or email key. Without MySQL the form cannot store
enquiries, and without `RESEND_API_KEY` + `MAIL_RECIPIENT` it cannot email them. If both are
missing, the visitor is asked to use WhatsApp or call instead.

## Deploy (Render)
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app`
- Add every variable from `.env.example` in the Render dashboard (use `DB_SSL=true` for Aiven).

## Logo
`static/img/verbas-logo.png` is a placeholder. Replace it with your real logo (same file name).
Never commit `.env` — it holds your passwords and API keys.
\n## SEO updates\nDedicated pages are served at `/about`, `/services`, `/tanuku`, `/careers`, `/privacy`, and `/blog`. The app also serves `/sitemap.xml` and `/robots.txt`. After deployment, test each route and request indexing in Google Search Console. Keep `.env` and credentials out of Git and shared ZIPs.\n