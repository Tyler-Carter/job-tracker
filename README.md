# JobTracker

> A personal job application tracker with pipeline management and analytics — built with Flask, HTMX, and Tailwind CSS.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-lightgrey?logo=flask)
![Deployed on Railway](https://img.shields.io/badge/Deployed%20on-Railway-blueviolet?logo=railway)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Overview

JobTracker helps you manage your job search from first application to final decision. Log every application, track each interview stage, and surface analytics that reveal which channels, company sizes, and roles are actually converting.

The app runs in **public read-only mode** by default — any visitor can view the data. Write access (add, edit, delete) is protected behind a single admin password, making it easy to share your live pipeline without exposing controls.

---

## Features

### Application Tracker
- Add, edit, and delete job applications with company, role, salary, source, and status fields
- Filter the dashboard table by status and source channel in real time (no page reload)
- View a full timeline of stage events per application (phone screen, technical, final round, etc.)
- Log stage outcomes (passed / failed / withdrew / pending) with dates and notes
- Current status auto-syncs to the latest logged stage event

### Analytics Dashboard
- Summary cards: total applications, active pipeline, responded count, response rate
- Status breakdown doughnut chart
- Applications submitted over time (weekly bar chart)
- Company size and source channel breakdown charts
- Stage conversion funnel
- Salary range table and pipeline staleness tracker (days since last activity)

### Auth & UX
- Public read-only mode; all writes protected by `@require_admin` decorator
- HTMX-powered inline editing and filtering with no JS framework required
- Responsive layout with Tailwind CSS
- Flash messages for all create/update/delete actions

---

## Tech Stack

| Layer       | Technology                              |
|-------------|-----------------------------------------|
| Backend     | Python 3.12, Flask 3.1                  |
| ORM         | Flask-SQLAlchemy 3.1, Flask-Migrate 4.0 |
| Frontend    | Jinja2, HTMX 2.0, Tailwind CSS (CDN)   |
| Charts      | Chart.js 4.4 (CDN)                      |
| Database    | SQLite (dev) / PostgreSQL (prod)        |
| Server      | Gunicorn 23.0                           |
| Deployment  | Railway                                 |
| Packaging   | uv                                      |

---

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — fast Python package manager

### Installation

```bash
git clone https://github.com/your-username/JobTracker.git
cd JobTracker
uv sync
```

### Environment Setup

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
ADMIN_PASSWORD=your-admin-password
DATABASE_URL=sqlite:///jobtracker.db
```

> See [Environment Variables](#environment-variables) for the full list.

### Run Locally

```bash
# Apply database migrations
uv run flask db upgrade

# Start the development server
uv run flask run
```

The app will be available at `http://localhost:5000`. Log in at `/login` with your `ADMIN_PASSWORD` to enable write access.

---

## Environment Variables

| Variable         | Required | Default              | Description                                      |
|------------------|----------|----------------------|--------------------------------------------------|
| `SECRET_KEY`     | Yes      | `dev-secret-...`     | Flask session signing key — change in production |
| `ADMIN_PASSWORD` | Yes      | `dev-admin`          | Password to unlock write access                  |
| `DATABASE_URL`   | No       | `sqlite:///jobtracker.db` | Database connection string                  |
| `FLASK_APP`      | No       | `app.py`             | Flask entry point (set in `.flaskenv`)           |
| `FLASK_DEBUG`    | No       | `0`                  | Enable debug mode locally                        |

> In production, Railway injects `DATABASE_URL` automatically when a PostgreSQL add-on is attached.

---

## Project Structure

```
JobTracker/
├── app.py                    # App factory, auth routes, blueprint registration
├── models.py                 # SQLAlchemy models: Application, StageEvent, enums
├── routes/
│   ├── applications.py       # CRUD routes (admin-protected writes)
│   └── analytics.py          # Analytics queries and Chart.js data
├── templates/
│   ├── base.html             # Master layout: nav, footer, flash messages
│   ├── login.html            # Admin login page
│   ├── applications/
│   │   ├── index.html        # Dashboard with filter table
│   │   ├── detail.html       # Application detail and stage timeline
│   │   ├── _form.html        # Shared create/edit form partial
│   │   ├── _row.html         # Table row partial (HTMX swap target)
│   │   ├── _table_body.html  # tbody partial returned on filter
│   │   └── _event_row.html   # Timeline entry partial
│   └── analytics/
│       └── index.html        # Analytics dashboard with Chart.js
├── migrations/               # Alembic migration history
├── pyproject.toml            # Project dependencies (uv)
├── Procfile                  # Heroku-style start command
└── railway.toml              # Railway deployment config
```

---

## Deployment

This project is configured for one-click deployment on [Railway](https://railway.app).

### Steps

1. Fork or push this repo to GitHub
2. Create a new Railway project and connect the repo
3. Add a **PostgreSQL** add-on — Railway will inject `DATABASE_URL` automatically
4. Set the required environment variables in Railway's settings:
   - `SECRET_KEY`
   - `ADMIN_PASSWORD`
5. Deploy — Railway runs `flask db upgrade && gunicorn app:app` on startup

The health check pings `GET /` to confirm the app is live.

---

## Roadmap

- [ ] CSV export of all applications
- [ ] Response rate breakdown by source channel (analytics)
- [ ] Email/notification reminders for stale applications
- [ ] ML-based application scoring using historical outcome data

---

## License

MIT — see [LICENSE](LICENSE) for details.
