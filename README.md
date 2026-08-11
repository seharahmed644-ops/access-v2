# Access v2

Access is a student opportunity discovery and application-tracking platform with accounts, personalized recommendations, saved opportunities, an application pipeline, analytics, and an admin dashboard.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Fseharahmed644-ops%2Faccess-v2)

## Features

- Student registration and login sessions
- PBKDF2-SHA256 password hashing
- Personalized opportunity match scoring
- Search, filters, verified-only mode, and sorting
- Per-user saved opportunities
- Application statuses and notes
- Admin dashboard and engagement totals
- Create, edit, delete, and bulk CSV-import opportunities
- 240 clearly labeled fictional demo listings for product testing
- Responsive student/admin interface
- Secure cookies on Render, same-origin write protection, and basic security headers

## Deploy on Render

Click **Deploy to Render** above. During the initial Blueprint setup, Render will ask for:

- `ACCESS_ADMIN_EMAIL` — your private admin email
- `ACCESS_ADMIN_PASSWORD` — use a unique password of at least 12 characters

Do not publish those values in GitHub. Render stores them as environment variables.

The free Render service uses ephemeral filesystem storage, so SQLite data can be reset when the service is replaced or redeployed. This is suitable for a public demo. For real users, move the database to managed PostgreSQL or attach persistent storage before relying on it for durable student data.

## Run locally

Requires Python 3.9+ and no third-party packages.

```bash
python3 server.py
```

Open `http://127.0.0.1:8000`. Student registration works without an admin account. To enable the admin locally:

```bash
ACCESS_ADMIN_EMAIL="you@example.com" ACCESS_ADMIN_PASSWORD="use-a-long-unique-password" python3 server.py
```

## Import verified opportunities

1. Sign in as admin.
2. Open **Admin**.
3. Use the included CSV template.
4. Add opportunities sourced from official websites.
5. Mark `verified=true` only after checking eligibility, deadline, and source URL.
6. Import the CSV.

Supported opportunity types: Scholarship, Internship, Program, Competition, Volunteer, Research, and Fellowship.

## Public-launch note

The built-in 240 opportunities are fictional demo records and are labeled as such. Replace them with verified real opportunities before presenting Access as a live opportunity database. A larger production launch should also add email verification/password reset, backups, privacy/terms pages, audit logs, stronger rate limiting, and a managed database.
