# JobTracker

> A personal job application tracker with pipeline management, analytics, and AI-powered job description analysis — built with Flask, HTMX, and Tailwind CSS.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-lightgrey?logo=flask)
![Deployed on Railway](https://img.shields.io/badge/Deployed%20on-Railway-blueviolet?logo=railway)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Overview

JobTracker helps you manage your job search from first application to final decision. Log every application, track each interview stage, surface analytics that reveal which channels and company sizes are actually converting, and use AI to extract insights from job descriptions.

The app runs in **public read-only mode** by default — any visitor can view the data. Write access (add, edit, delete, AI analysis) is protected behind a single admin password, making it easy to share your live pipeline without exposing controls.

---

## Features

### Application Tracker
- Add, edit, and delete job applications with company, role, salary, source, status, and job description fields
- Filter the dashboard table by status and source channel in real time (no page reload)
- View a full timeline of stage events per application (phone screen, technical, final round, etc.)
- Log stage outcomes (passed / failed / withdrew / pending) with dates and notes
- Current status auto-syncs to the latest logged stage event

### AI Analysis (powered by Groq + Llama 3.3 70B)
- **Skills & Keywords** — extracts required skills, technologies, nice-to-haves, experience level, and key responsibilities from the job posting
- **Job Fit Summary** — generates a narrative summary of what the role involves, role type (IC / manager / hybrid), seniority signals, and red/green flags
- **Interview Prep** — produces targeted behavioral, technical, and role-specific questions plus questions to ask the interviewer
- Results are cached in the database — subsequent page loads are instant with no repeat API calls
- Admin-only "Refresh" button to re-run analysis when a job description is updated

### Analytics Dashboard
- Summary cards: total applications, active pipeline, responded count, response rate
- Status breakdown doughnut chart
- Applications submitted over time (weekly bar chart)
- Company size and source channel breakdown charts
- Stage conversion funnel
- Salary range table and pipeline staleness tracker (days since last activity)

### Auth & UX
- Public read-only mode; all writes protected by `@require_admin` decorator
- Dark/light mode toggle with localStorage persistence
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
| AI          | Groq API, Llama 3.3 70B                 |
| Database    | SQLite (dev) / PostgreSQL (prod)        |
| Server      | Gunicorn 23.0                           |
| Deployment  | Railway                                 |
| Packaging   | uv                                      |

---

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — fast Python package manager
- A free [Groq API key](https://console.groq.com) for AI analysis features

### Installation

```bash
git clone https://github.com/your-username/JobTracker.git
cd JobTracker
uv sync
```

### Environment Setup

Create a `.flaskenv` file in the project root:

```env
FLASK_APP=app.py
SECRET_KEY=your-secret-key-here
ADMIN_PASSWORD=your-admin-password
GROQ_API_KEY=your-groq-api-key
```

> See [Environment Variables](#environment-variables) for the full list.

### Run Locally

```bash
# Apply database migrations
uv run flask db upgrade

# Start the development server
uv run flask run
```

The app will be available at `http://localhost:5000`. Log in at `/login` with your `ADMIN_PASSWORD` to enable write access and AI analysis.

---

## Environment Variables

| Variable              | Required | Default                   | Description                                      |
|-----------------------|----------|---------------------------|--------------------------------------------------|
| `SECRET_KEY`          | Yes      | `dev-secret-...`          | Flask session signing key — change in production |
| `ADMIN_PASSWORD`      | Yes      | `dev-admin`               | Password to unlock write access                  |
| `GROQ_API_KEY`        | Yes*     | —                         | Groq API key for AI analysis (free at console.groq.com) |
| `DATABASE_URL`        | No       | `sqlite:///jobtracker.db` | Database connection string                       |
| `FLASK_APP`           | No       | `app.py`                  | Flask entry point (set in `.flaskenv`)           |
| `FLASK_DEBUG`         | No       | `0`                       | Enable debug mode locally                        |

> \* Required only for AI analysis features. The rest of the app works without it.
>
> In production, Railway injects `DATABASE_URL` automatically when a PostgreSQL add-on is attached.

---

## Project Structure

```
JobTracker/
├── app.py                    # App factory, auth routes, blueprint registration
├── models.py                 # SQLAlchemy models: Application, StageEvent, AIAnalysis, enums
├── routes/
│   ├── applications.py       # CRUD routes (admin-protected writes)
│   ├── analytics.py          # Analytics queries and Chart.js data
│   └── ai.py                 # AI analysis routes (Groq API integration)
├── templates/
│   ├── base.html             # Master layout: nav, dark mode toggle, flash messages
│   ├── login.html            # Admin login page
│   ├── applications/
│   │   ├── index.html        # Dashboard with filter table
│   │   ├── detail.html       # Application detail, stage timeline, and AI panel
│   │   ├── _form.html        # Shared create/edit form partial
│   │   ├── _row.html         # Table row partial (HTMX swap target)
│   │   ├── _table_body.html  # tbody partial returned on filter
│   │   ├── _event_row.html   # Timeline entry partial
│   │   ├── _ai_panel.html    # AI analysis three-card panel
│   │   ├── _ai_result_skills.html    # Skills & keywords result partial
│   │   ├── _ai_result_fit.html       # Job fit summary result partial
│   │   └── _ai_result_interview.html # Interview prep result partial
│   └── analytics/
│       └── index.html        # Analytics dashboard with Chart.js
├── migrations/               # Alembic migration history
├── pyproject.toml            # Project dependencies (uv)
├── Procfile                  # Gunicorn start command
└── railway.toml              # Railway deployment config
```

---

## Supported Job Sources

LinkedIn, Indeed, Zip Recruiter, Dice, Wellfound, Kaggle, Washington Technology, Built In Seattle, GitHub Careers, Referral, Cold Outreach, Company Website, Job Board, Other.

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
   - `GROQ_API_KEY`
5. Deploy — Railway runs `flask db upgrade && gunicorn app:app` on startup

The health check pings `GET /` to confirm the app is live.

---

## Roadmap

- [ ] CSV export of all applications
- [ ] Resume upload and ATS match score against job description
- [ ] Response rate breakdown by source channel (analytics)
- [ ] Email/notification reminders for stale applications

---

## License

MIT — see [LICENSE](LICENSE) for details.
