import json
import os
from collections import defaultdict
from datetime import date, timedelta

from flask import Blueprint, render_template, request, Response, stream_with_context
from groq import Groq

from app import db, require_admin
from models import (
    Application, ApplicationSource, ApplicationStatus, CompanySize, StageEvent,
)
from prompts import PROMPTS, CURRENT_VERSION, SYSTEM_PROMPT

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


def _generate_snapshot(total, response_rate, offers, active, source_performance):
    """Return a 1-2 sentence plain-text insight string. No AI — deterministic Python."""
    if total < 5:
        return (
            f"You have {total} application{'s' if total != 1 else ''} logged so far"
            " — keep building the pipeline."
        )

    best = source_performance[0] if source_performance else None

    if response_rate >= 30:
        rate_msg = f"a strong {response_rate}% response rate"
    elif response_rate >= 15:
        rate_msg = f"a {response_rate}% response rate (near the ~15% industry average)"
    else:
        rate_msg = (
            f"a below-average {response_rate}% response rate"
            " — volume or targeting may need attention"
        )

    parts = [f"Across {total} applications you're seeing {rate_msg}."]

    if offers:
        parts.append(f"You have {offers} offer{'s' if offers != 1 else ''} — excellent work.")
    elif best and best["callback_rate"] > 0:
        parts.append(
            f"{best['source']} is your top channel"
            f" at {best['callback_rate']}% callback rate."
        )
    elif active:
        parts.append(
            f"{active} application{'s are' if active != 1 else ' is'}"
            " still active in the pipeline."
        )

    return " ".join(parts)


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
            source_colors.append(SOURCE_COLORS.get(source, "#6b7280"))

    # ------------------------------------------------------------------ #
    # Source performance table (callback rates)                           #
    # Uses StageEvent to catch apps that progressed then were rejected.   #
    # ------------------------------------------------------------------ #
    source_performance = []
    for source in ApplicationSource:
        applied_count = Application.query.filter_by(source=source).count()
        if not applied_count:
            continue
        # Count unique applications from this source that ever reached Phone Screen
        progressed_count = (
            db.session.query(StageEvent.application_id)
            .join(Application, Application.id == StageEvent.application_id)
            .filter(
                Application.source == source,
                StageEvent.stage == ApplicationStatus.PHONE_SCREEN,
            )
            .distinct()
            .count()
        )
        callback_rate = round(progressed_count / applied_count * 100)
        source_performance.append({
            "source": source.value,
            "applied": applied_count,
            "responded": progressed_count,
            "callback_rate": callback_rate,
            "color": SOURCE_COLORS.get(source, "#6b7280"),
        })
    source_performance.sort(key=lambda r: r["callback_rate"], reverse=True)

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

    # ------------------------------------------------------------------ #
    # Narrative snapshot (deterministic Python — no AI cost)              #
    # ------------------------------------------------------------------ #
    snapshot = _generate_snapshot(total, response_rate, offers, active, source_performance)

    return render_template(
        "analytics/index.html",
        no_data=False,
        # summary
        total=total,
        active=active,
        offers=offers,
        responded=responded,
        response_rate=response_rate,
        snapshot=snapshot,
        # status doughnut
        status_labels=json.dumps(status_labels),
        status_data=json.dumps(status_data),
        status_colors=json.dumps(status_colors),
        # source bar
        source_labels=json.dumps(source_labels),
        source_data=json.dumps(source_data),
        source_colors=json.dumps(source_colors),
        # source performance table
        source_performance=source_performance,
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


# ------------------------------------------------------------------ #
# JD Analyzer — paste any job description, get structured extraction  #
# ------------------------------------------------------------------ #
@bp.route("/jd-analyze", methods=["POST"])
@require_admin
def jd_analyze():
    jd_text = request.form.get("jd_text", "").strip()
    if not jd_text or len(jd_text) < 50:
        return render_template(
            "analytics/_jd_result.html",
            result=None,
            error="Please paste a job description (at least 50 characters).",
        )

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return render_template(
            "analytics/_jd_result.html",
            result=None,
            error="GROQ_API_KEY is not configured.",
        )

    prompt = PROMPTS[CURRENT_VERSION]["JD_ANALYZER"].format(jd=jd_text)

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        result = json.loads(raw)
    except json.JSONDecodeError:
        return render_template(
            "analytics/_jd_result.html",
            result=None,
            error="Model returned invalid JSON. Try again.",
        )
    except Exception as e:
        return render_template(
            "analytics/_jd_result.html",
            result=None,
            error=f"API error: {str(e)}",
        )

    return render_template("analytics/_jd_result.html", result=result, error=None)


# ------------------------------------------------------------------ #
# Strategy Advisor — SSE streaming analysis of full application       #
# history. Uses Groq stream=True; response_format is incompatible     #
# with streaming so the prompt requests JSON in natural language.     #
# X-Accel-Buffering: no disables Railway nginx buffering for SSE.     #
# ------------------------------------------------------------------ #
@bp.route("/strategy/stream")
@require_admin
def strategy_stream():
    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        def _error_gen():
            yield "data: API key not configured.\n\n"
            yield "event: done\ndata: \n\n"
        return Response(
            stream_with_context(_error_gen()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    all_apps = Application.query.order_by(Application.date_applied).all()

    if not all_apps:
        def _no_data_gen():
            yield "data: No application data available yet.\n\n"
            yield "event: done\ndata: \n\n"
        return Response(
            stream_with_context(_no_data_gen()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Serialize applications compactly for prompt efficiency
    apps_data = []
    for app in all_apps:
        days_to_respond = None
        non_applied = [
            e for e in app.stage_events
            if e.stage != ApplicationStatus.APPLIED
        ]
        if non_applied:
            first = min(non_applied, key=lambda e: e.occurred_on)
            days_to_respond = (first.occurred_on - app.date_applied).days

        apps_data.append({
            "source": app.source.value,
            "status": app.current_status.value,
            "company_size": app.company_size.value,
            "date_applied": app.date_applied.isoformat(),
            "days_to_respond": days_to_respond,
        })

    prompt = PROMPTS[CURRENT_VERSION]["STRATEGY_ADVISOR"].format(
        applications_json=json.dumps(apps_data)
    )

    def generate():
        try:
            client = Groq(api_key=api_key)
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1500,
                stream=True,
                # Note: response_format is not compatible with stream=True in the Groq API.
                # The prompt instructs the model to return JSON; we parse it client-side
                # after the stream completes.
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    # Each SSE data line must be a single line; escape newlines in content
                    for line in delta.splitlines(keepends=True):
                        safe = line.rstrip("\n\r")
                        if safe:
                            yield f"data: {safe}\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"

        yield "event: done\ndata: \n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
