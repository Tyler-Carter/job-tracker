import os
from functools import wraps

from flask import Flask, redirect, render_template, request, session, url_for
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# ── Database ────────────────────────────────────────────────────────────────
# DATABASE_PUBLIC_URL is Railway's externally-reachable URL (used when running
# commands locally via `railway run`). Fall back to internal DATABASE_URL
# (used by the deployed app inside Railway's private network), then SQLite.
_db_url = (
    os.environ.get("DATABASE_PUBLIC_URL")
    or os.environ.get("DATABASE_URL")
    or "sqlite:///jobtracker.db"
)
# Railway provides postgres:// URIs; SQLAlchemy requires postgresql://
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = _db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ── Import models so Flask-Migrate can detect them ──────────────────────────
import models  # noqa: F401, E402

# ── Auth ─────────────────────────────────────────────────────────────────────
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "dev-admin")


def require_admin(f):
    """Redirect to /login if the visitor is not an authenticated admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["is_admin"] = True
            next_url = request.form.get("next") or url_for("applications.list_applications")
            return redirect(next_url)
        error = "Incorrect password — try again."
    return render_template(
        "login.html",
        error=error,
        next=request.args.get("next", ""),
    )


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("is_admin", None)
    return redirect(url_for("applications.list_applications"))


# ── Blueprints ───────────────────────────────────────────────────────────────
from routes.applications import bp as applications_bp  # noqa: E402
from routes.analytics import bp as analytics_bp  # noqa: E402

app.register_blueprint(applications_bp)
app.register_blueprint(analytics_bp)


@app.route("/")
def index():
    return redirect(url_for("applications.list_applications"))


if __name__ == "__main__":
    app.run()
