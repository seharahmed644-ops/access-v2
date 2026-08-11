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
- Curated real opportunities checked against official sources
- Automatic removal of the original fictional demo records during deployment
- Responsive student/admin interface
- Secure cookies on Render, same-origin write protection, and basic security headers

## Real opportunity catalog

The deployment bootstrap currently includes a curated set of opportunities whose deadlines and official source pages were checked on August 11, 2026. Examples include The Gates Scholarship, Coca-Cola Scholars, QuestBridge National College Match, Regeneron Science Talent Search, YoungArts, the Congressional App Challenge, Elks Most Valuable Student, College Board BigFuture Scholarships, Jack Kent Cooke College Scholarship Program, NASA OSTEM internships, VFW Voice of Democracy, and the University of Toronto Lester B. Pearson International Scholarship.

Opportunity details can change. Students should always open the official source from Access and confirm the current eligibility, deadline, award terms, and application instructions before submitting anything.

## Deploy on Render

Click **Deploy to Render** above. During the initial Blueprint setup, Render will ask for:

- `ACCESS_ADMIN_EMAIL` — your private admin email
- `ACCESS_ADMIN_PASSWORD` — use a unique password of at least 12 characters

Do not publish those values in GitHub. Render stores them as environment variables.

The free Render service uses ephemeral filesystem storage. The verified bootstrap catalog is recreated on deployment, but student accounts, saves, applications, and opportunities added only at runtime are not durable enough for a serious production launch. Move the database to managed PostgreSQL or attach persistent storage before relying on Access for real student data.

## Run locally

Requires Python 3.9+ and no third-party packages.

```bash
cat server_parts/01.py server_parts/02.py server_parts/03.py > server.py
python3 bootstrap.py
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

## Production roadmap

Before a larger public launch, add managed PostgreSQL, email verification/password reset, backups, privacy and terms pages, audit logs, stronger rate limiting, and a recurring process for re-verifying opportunities as deadlines and eligibility rules change.
