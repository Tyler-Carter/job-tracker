import json
from collections import defaultdict
from datetime import date, timedelta

from flask import Blueprint, render_template

from app import db
from models import Application, ApplicationSource, ApplicationStatus, CompanySize, StageEvent

bp = Blueprint("analytics", __name__, url_prefix="/analytics")

# Chart colour palettes
STATUS_COLORS = {
    ApplicationStatus.APPLIED:      "#3b82f6",  # blue
    ApplicationStatus.PHONE_SCREEN: "#eab308",  # yellow
    ApplicationStatus.TECHNICAL:    "#a855f7",  # purple
    ApplicationStatus.FINAL_ROUND:  "#f97316",  # orange
    ApplicationStatus.OFFER:        "#22c55e",  # green
    ApplicationStatus.REJECTED:     "#ef4444",  # red
    ApplicationStatus.WITHDRAWN:    "#6b7280",  # gray
}

SIZE_COLORS = {
    CompanySize.STARTUP:    "#6366f1",  # indigo
    CompanySize.MID_SIZE:   "#06b6d4",  # cyan
    CompanySize.ENTERPRISE: "#10b981",  # emerald
}

SOURCE_COLORS = {
    ApplicationSource.LINKEDIN:        "#0077b5",
    ApplicationSource.REFERRAL:        "#f59e0b",
    ApplicationSource.COLD_OUTREACH:   "#8b5cf6",
    ApplicationSource.COMPANY_WEBSITE: "#10b981",
    ApplicationSource.JOB_BOARD:       "#3b82f6",
    ApplicationSource.OTHER:           "#6b7280",
}


@bp.route("/")
def index():
    total = Application.query.count()

    if total == 0:
        return render_template("analytics/index.html", no_data=True)

    # ------------------------------------------------------------------ #
    # Summary cards                                                        #
    # ------------------------------------------------------------------ #
    active_statuses = [
        ApplicationStatus.APPLIED,
        ApplicationStatus.PHONE_SCREEN,
        ApplicationStatus.TECHNICAL,
        ApplicationStatus.FINAL_ROUND,
    ]
    active = Application.query.filter(
        Application.current_status.in_(active_statuses)
    ).count()

    offers = Application.query.filter_by(
        current_status=ApplicationStatus.OFFER
    ).count()

    # "Responded" = anything beyond initial APPLIED status
    responded = Application.query.filter(
        Application.current_status != ApplicationStatus.APPLIED
    ).count()
    response_rate = round(responded / total * 100) if total else 0

    # ------------------------------------------------------------------ #
    # Status breakdown (doughnut)                                         #
    # ------------------------------------------------------------------ #
    status_labels, status_data, status_colors = [], [], []
    for status in ApplicationStatus:
        count = Application.query.filter_by(current_status=status).count()
        if count:
            status_labels.append(status.value)
            status_data.append(count)
            status_colors.append(STATUS_COLORS[status])

    # ------------------------------------------------------------------ #
    # Source breakdown (horizontal bar)                                   #
    # ------------------------------------------------------------------ #
    source_labels, source_data, source_colors = [], [], []
    for source in ApplicationSource:
        count = Application.query.filter_by(source=source).count()
        if count:
            source_labels.append(source.value)
            source_data.append(count)
            source_colors.append(SOURCE_COLORS[source])

    # ------------------------------------------------------------------ #
    # Company size breakdown (bar)                                        #
    # ------------------------------------------------------------------ #
    size_labels, size_data, size_colors = [], [], []
    for size in CompanySize:
        count = Application.query.filter_by(company_size=size).count()
        if count:
            size_labels.append(size.value)
            size_data.append(count)
            size_colors.append(SIZE_COLORS[size])

    # ------------------------------------------------------------------ #
    # Applications over time (bar by week)                                #
    # ------------------------------------------------------------------ #
    apps_ordered = Application.query.order_by(Application.date_applied).all()
    weekly: dict[str, int] = defaultdict(int)
    for app in apps_ordered:
        d = app.date_applied
        monday = (d - timedelta(days=d.weekday())).isoformat()
        weekly[monday] += 1

    sorted_weeks = sorted(weekly.keys())
    timeline_labels = [
        f"{date.fromisoformat(w).day} {date.fromisoformat(w).strftime('%b')}"
        for w in sorted_weeks
    ]
    timeline_data = [weekly[w] for w in sorted_weeks]

    # ------------------------------------------------------------------ #
    # Stage funnel (count of apps that ever reached each stage)           #
    # ------------------------------------------------------------------ #
    funnel_stages = [
        ApplicationStatus.APPLIED,
        ApplicationStatus.PHONE_SCREEN,
        ApplicationStatus.TECHNICAL,
        ApplicationStatus.FINAL_ROUND,
        ApplicationStatus.OFFER,
    ]
    funnel_labels, funnel_data, funnel_colors = [], [], []
    for stage in funnel_stages:
        # Count unique applications that have a StageEvent at this stage
        count = (
            db.session.query(StageEvent.application_id)
            .filter(StageEvent.stage == stage)
            .distinct()
            .count()
        )
        funnel_labels.append(stage.value)
        funnel_data.append(count)
        funnel_colors.append(STATUS_COLORS[stage])

    # ------------------------------------------------------------------ #
    # Salary ranges (table for apps that have salary data)                #
    # ------------------------------------------------------------------ #
    salary_apps = Application.query.filter(
        Application.salary_min.isnot(None)
    ).order_by(Application.salary_min.desc()).all()

    salary_rows = []
    for app in salary_apps:
        mid = (app.salary_min + (app.salary_max or app.salary_min)) / 2
        salary_rows.append(
            {
                "company": app.company_name,
                "role": app.role_title,
                "display": app.salary_display(),
                "mid": int(mid),
                "status": app.current_status.value,
                "status_color": STATUS_COLORS[app.current_status],
            }
        )
    salary_rows.sort(key=lambda r: r["mid"], reverse=True)

    # ------------------------------------------------------------------ #
    # Days in pipeline (for active apps)                                  #
    # ------------------------------------------------------------------ #
    today = date.today()
    pipeline_apps = []
    for app in Application.query.filter(
        Application.current_status.in_(active_statuses)
    ).order_by(Application.date_applied).all():
        days = (today - app.date_applied).days
        pipeline_apps.append(
            {
                "company": app.company_name,
                "role": app.role_title,
                "days": days,
                "status": app.current_status.value,
                "status_color": STATUS_COLORS[app.current_status],
            }
        )

    return render_template(
        "analytics/index.html",
        no_data=False,
        # summary
        total=total,
        active=active,
        offers=offers,
        responded=responded,
        response_rate=response_rate,
        # status doughnut
        status_labels=json.dumps(status_labels),
        status_data=json.dumps(status_data),
        status_colors=json.dumps(status_colors),
        # source bar
        source_labels=json.dumps(source_labels),
        source_data=json.dumps(source_data),
        source_colors=json.dumps(source_colors),
        # size bar
        size_labels=json.dumps(size_labels),
        size_data=json.dumps(size_data),
        size_colors=json.dumps(size_colors),
        # timeline
        timeline_labels=json.dumps(timeline_labels),
        timeline_data=json.dumps(timeline_data),
        # funnel
        funnel_labels=json.dumps(funnel_labels),
        funnel_data=json.dumps(funnel_data),
        funnel_colors=json.dumps(funnel_colors),
        # salary table
        salary_rows=salary_rows,
        # pipeline staleness
        pipeline_apps=pipeline_apps,
    )
