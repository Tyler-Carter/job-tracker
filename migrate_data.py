"""
One-shot script to copy all data from local SQLite → Railway Postgres.

Usage:
    $env:DATABASE_PUBLIC_URL="postgresql://..."; uv run python migrate_data.py
"""
import os
import sqlite3
from datetime import date, datetime

from sqlalchemy import create_engine, text

SQLITE_PATH = "instance/jobtracker.db"
TARGET_URL = (
    os.environ.get("DATABASE_PUBLIC_URL")
    or os.environ.get("DATABASE_URL")
)

if not TARGET_URL:
    raise SystemExit("Set DATABASE_PUBLIC_URL before running this script.")

if TARGET_URL.startswith("postgres://"):
    TARGET_URL = TARGET_URL.replace("postgres://", "postgresql://", 1)

src = sqlite3.connect(SQLITE_PATH)
src.row_factory = sqlite3.Row
dst = create_engine(TARGET_URL)

apps = src.execute("SELECT * FROM application").fetchall()
events = src.execute("SELECT * FROM stage_event").fetchall()

with dst.begin() as conn:
    # Clear destination first (safe — fresh Postgres DB)
    conn.execute(text("DELETE FROM stage_event"))
    conn.execute(text("DELETE FROM application"))

    for a in apps:
        conn.execute(text("""
            INSERT INTO application
              (id, company_name, role_title, date_applied, current_status,
               source, salary_min, salary_max, company_size, company_type,
               notes, created_at, updated_at)
            VALUES
              (:id, :company_name, :role_title, :date_applied, :current_status,
               :source, :salary_min, :salary_max, :company_size, :company_type,
               :notes, :created_at, :updated_at)
        """), dict(a))

    for e in events:
        conn.execute(text("""
            INSERT INTO stage_event
              (id, application_id, stage, occurred_on, outcome, notes)
            VALUES
              (:id, :application_id, :stage, :occurred_on, :outcome, :notes)
        """), dict(e))

    # Reset sequences so future inserts don't collide with copied IDs
    conn.execute(text(
        "SELECT setval('application_id_seq', (SELECT MAX(id) FROM application))"
    ))
    conn.execute(text(
        "SELECT setval('stage_event_id_seq', (SELECT MAX(id) FROM stage_event))"
    ))

print(f"Migrated {len(apps)} applications and {len(events)} stage events.")
src.close()
