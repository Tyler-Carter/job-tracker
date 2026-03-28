from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from app import db, require_admin
from models import (
    Application,
    AnalysisType,
    ApplicationSource,
    ApplicationStatus,
    CompanySize,
    CompanyType,
    StageEvent,
    StageOutcome,
)

bp = Blueprint("applications", __name__, url_prefix="/applications")

STATUS_BADGE = {
    ApplicationStatus.APPLIED:      "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
    ApplicationStatus.PHONE_SCREEN: "bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300",
    ApplicationStatus.TECHNICAL:    "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300",
    ApplicationStatus.FINAL_ROUND:  "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300",
    ApplicationStatus.OFFER:        "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300",
    ApplicationStatus.REJECTED:     "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
    ApplicationStatus.WITHDRAWN:    "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300",
}


def _parse_application_form(form):
    """Parse and validate application form data. Returns (data_dict, errors_dict)."""
    errors = {}
    data = {}

    company_name = form.get("company_name", "").strip()
    if not company_name:
        errors["company_name"] = "Company name is required."
    data["company_name"] = company_name

    role_title = form.get("role_title", "").strip()
    if not role_title:
        errors["role_title"] = "Role title is required."
    data["role_title"] = role_title

    raw_date = form.get("date_applied", "").strip()
    try:
        data["date_applied"] = datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        errors["date_applied"] = "Valid date required (YYYY-MM-DD)."
        data["date_applied"] = None

    status_val = form.get("current_status", "")
    valid_statuses = {e.value: e for e in ApplicationStatus}
    if status_val not in valid_statuses:
        errors["current_status"] = "Invalid status."
        data["current_status"] = ApplicationStatus.APPLIED
    else:
        data["current_status"] = valid_statuses[status_val]

    source_val = form.get("source", "")
    valid_sources = {e.value: e for e in ApplicationSource}
    if source_val not in valid_sources:
        errors["source"] = "Source is required."
        data["source"] = None
    else:
        data["source"] = valid_sources[source_val]

    size_val = form.get("company_size", "")
    valid_sizes = {e.value: e for e in CompanySize}
    if size_val not in valid_sizes:
        errors["company_size"] = "Company size is required."
        data["company_size"] = None
    else:
        data["company_size"] = valid_sizes[size_val]

    type_val = form.get("company_type", "")
    valid_types = {e.value: e for e in CompanyType}
    data["company_type"] = valid_types.get(type_val, CompanyType.UNKNOWN)

    for field in ("salary_min", "salary_max"):
        raw = form.get(field, "").strip()
        if raw:
            try:
                data[field] = int(raw)
            except ValueError:
                errors[field] = "Must be a whole number."
                data[field] = None
        else:
            data[field] = None

    data["notes"] = form.get("notes", "").strip() or None
    data["job_description"] = form.get("job_description", "").strip() or None

    return data, errors


def _parse_event_form(form):
    """Parse and validate stage event form. Returns (data_dict, errors_dict)."""
    errors = {}
    data = {}

    stage_val = form.get("stage", "")
    valid_statuses = {e.value: e for e in ApplicationStatus}
    if stage_val not in valid_statuses:
        errors["stage"] = "Stage is required."
        data["stage"] = None
    else:
        data["stage"] = valid_statuses[stage_val]

    raw_date = form.get("occurred_on", "").strip()
    try:
        data["occurred_on"] = datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        errors["occurred_on"] = "Valid date required (YYYY-MM-DD)."
        data["occurred_on"] = None

    outcome_val = form.get("outcome", "")
    valid_outcomes = {e.value: e for e in StageOutcome}
    data["outcome"] = valid_outcomes.get(outcome_val, StageOutcome.PENDING)

    data["notes"] = form.get("notes", "").strip() or None

    return data, errors


# ---------------------------------------------------------------------------
# List / Dashboard
# ---------------------------------------------------------------------------

@bp.route("/")
def list_applications():
    query = Application.query

    status_filter = request.args.get("status", "")
    source_filter = request.args.get("source", "")

    valid_statuses = {e.value: e for e in ApplicationStatus}
    valid_sources = {e.value: e for e in ApplicationSource}

    if status_filter and status_filter in valid_statuses:
        query = query.filter(Application.current_status == valid_statuses[status_filter])
    if source_filter and source_filter in valid_sources:
        query = query.filter(Application.source == valid_sources[source_filter])

    apps = query.order_by(Application.date_applied.desc()).all()

    ctx = dict(
        apps=apps,
        status_filter=status_filter,
        source_filter=source_filter,
        statuses=ApplicationStatus,
        sources=ApplicationSource,
        status_badge=STATUS_BADGE,
    )

    if request.headers.get("HX-Request"):
        return render_template("applications/_table_body.html", **ctx)
    return render_template("applications/index.html", **ctx)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@bp.route("/new")
@require_admin
def new_application():
    return render_template(
        "applications/_form.html",
        application=None,
        errors={},
        statuses=ApplicationStatus,
        sources=ApplicationSource,
        sizes=CompanySize,
        types=CompanyType,
        today=date.today().isoformat(),
    )


@bp.route("/", methods=["POST"])
@require_admin
def create_application():
    data, errors = _parse_application_form(request.form)
    if errors:
        return render_template(
            "applications/_form.html",
            application=None,
            errors=errors,
            form=request.form,
            statuses=ApplicationStatus,
            sources=ApplicationSource,
            sizes=CompanySize,
            types=CompanyType,
            today=date.today().isoformat(),
        ), 422

    app_obj = Application(**data)
    db.session.add(app_obj)
    db.session.commit()

    # Also create the initial "Applied" stage event
    event = StageEvent(
        application_id=app_obj.id,
        stage=ApplicationStatus.APPLIED,
        occurred_on=app_obj.date_applied,
        outcome=StageOutcome.PENDING,
    )
    db.session.add(event)
    db.session.commit()

    return render_template(
        "applications/_row.html",
        app=app_obj,
        status_badge=STATUS_BADGE,
    )


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

@bp.route("/<int:app_id>")
def get_application(app_id):
    app_obj = Application.query.get_or_404(app_id)
    return render_template(
        "applications/detail.html",
        app=app_obj,
        status_badge=STATUS_BADGE,
        statuses=ApplicationStatus,
        outcomes=StageOutcome,
        analysis_types=AnalysisType,
        today=date.today().isoformat(),
        event_errors={},
    )


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------

@bp.route("/<int:app_id>/edit")
@require_admin
def edit_application(app_id):
    app_obj = Application.query.get_or_404(app_id)
    return render_template(
        "applications/_form.html",
        application=app_obj,
        errors={},
        statuses=ApplicationStatus,
        sources=ApplicationSource,
        sizes=CompanySize,
        types=CompanyType,
        today=date.today().isoformat(),
    )


@bp.route("/<int:app_id>/edit", methods=["POST"])
@require_admin
def update_application(app_id):
    app_obj = Application.query.get_or_404(app_id)
    data, errors = _parse_application_form(request.form)
    if errors:
        return render_template(
            "applications/_form.html",
            application=app_obj,
            errors=errors,
            form=request.form,
            statuses=ApplicationStatus,
            sources=ApplicationSource,
            sizes=CompanySize,
            types=CompanyType,
            today=date.today().isoformat(),
        ), 422

    for key, value in data.items():
        setattr(app_obj, key, value)
    db.session.commit()

    return render_template(
        "applications/_row.html",
        app=app_obj,
        status_badge=STATUS_BADGE,
    )


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@bp.route("/<int:app_id>/delete", methods=["POST"])
@require_admin
def delete_application(app_id):
    app_obj = Application.query.get_or_404(app_id)
    db.session.delete(app_obj)
    db.session.commit()
    return "", 200


# ---------------------------------------------------------------------------
# Stage Events
# ---------------------------------------------------------------------------

@bp.route("/<int:app_id>/events", methods=["POST"])
@require_admin
def add_stage_event(app_id):
    app_obj = Application.query.get_or_404(app_id)
    data, errors = _parse_event_form(request.form)

    if errors:
        return render_template(
            "applications/detail.html",
            app=app_obj,
            status_badge=STATUS_BADGE,
            statuses=ApplicationStatus,
            outcomes=StageOutcome,
            today=date.today().isoformat(),
            event_errors=errors,
        ), 422

    event = StageEvent(application_id=app_obj.id, **data)
    db.session.add(event)

    # Keep current_status in sync with the latest stage
    app_obj.current_status = data["stage"]
    db.session.commit()

    return render_template(
        "applications/_event_row.html",
        event=event,
        status_badge=STATUS_BADGE,
    )
