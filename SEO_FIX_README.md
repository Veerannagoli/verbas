# Verbas website — SEO route fix

## What changed
- Added dedicated Flask routes and unique page content for `/about`, `/services`, `/tanuku`, `/careers`, `/privacy`, `/terms`, `/services/seo`, and `/services/website-development`.
- Added canonical URLs, page-specific titles/descriptions, Open Graph metadata, and WebPage structured data on these pages.
- Updated navigation and footer links to point to the dedicated pages.
- Updated `/sitemap.xml` to include all real public pages, including the new terms and service-detail pages; `/robots.txt` continues to reference it.
- Kept the top navigation focused on the main site sections and added crawlable footer links to supporting pages.
- Added unique page titles, descriptions, canonical URLs, Open Graph metadata and structured WebPage data for the supporting pages.
- Expanded privacy and terms content as a practical starting draft; review the wording against your actual data practices and legal requirements before relying on it as legal advice.
- Fixed the 404 handler so unknown URLs return a real 404 page rather than the homepage HTML with a 404 status.
- Removed `.git` history and `.env` files from this delivery ZIP for safety. Configure secrets in Render Environment settings; use `.env.example` only as a template.

## Deploy
1. Extract this ZIP and open the `verbas` folder.
2. Commit and push the changed files to the repository connected to your Render web service.
3. In Render, confirm the service root directory and start command match your current setup (commonly `gunicorn app:app` when the root directory is `verbas`).
4. Wait for deployment to finish, then test:
   - https://verbas.in/about
   - https://verbas.in/services
   - https://verbas.in/tanuku
   - https://verbas.in/careers
   - https://verbas.in/privacy
   - https://verbas.in/terms
   - https://verbas.in/services/seo
   - https://verbas.in/services/website-development
   - https://verbas.in/sitemap.xml
5. In Google Search Console, use URL Inspection → Test Live URL. Request indexing only after each URL returns HTTP 200.

## Note
This ZIP fixes the code, but it does not automatically deploy it to Render or update Google's existing index. Google may need time to recrawl the pages.
