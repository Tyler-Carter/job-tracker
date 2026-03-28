import json
import os
import time

from flask import Blueprint, render_template, request, abort
from groq import Groq
from app import db, require_admin
from models import Application, AIAnalysis, AnalysisType
from prompts import SYSTEM_PROMPT as _SYSTEM_PROMPT, PROMPTS, CURRENT_VERSION

bp = Blueprint("ai", __name__, url_prefix="/applications")

# Active prompt set for this version
_PROMPTS = PROMPTS[CURRENT_VERSION]

# ------------------------------------------------------------------ #
# Rate limiter                                                         #
# In-process dict keyed by (app_id, analysis_type_value) → timestamp  #
# Resets on server restart — acceptable for a single-admin personal    #
# app running on one Railway dyno.                                     #
# ------------------------------------------------------------------ #
_rate_limit_store: dict[tuple, float] = {}
_RATE_LIMIT_SECONDS = 30


def _run_analysis(app_obj, analysis_type):
    """Call Groq API and upsert the result into AIAnalysis. Returns (result_dict, error_str)."""
    if not app_obj.job_description:
        return None, "No job description saved for this application."

    # Rate limiting: serve stale cache if available, else block with wait message
    rate_key = (app_obj.id, analysis_type.value)
    last_run = _rate_limit_store.get(rate_key)
    now = time.time()
    if last_run and (now - last_run) < _RATE_LIMIT_SECONDS:
        cached, _ = _get_cached(app_obj.id, analysis_type)
        if cached:
            return cached, None  # graceful degradation — serve stale cache silently
        wait = int(_RATE_LIMIT_SECONDS - (now - last_run))
        return None, f"Rate limited. Please wait {wait}s before re-running."

    prompt = _PROMPTS[analysis_type].format(
        role=app_obj.role_title,
        company=app_obj.company_name,
        jd=app_obj.job_description,
        size=app_obj.company_size.value,
        type=app_obj.company_type.value,
    )

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None, "GROQ_API_KEY is not configured."

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
    except Exception as e:
        return None, f"API error: {str(e)}"

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return None, "Model returned invalid JSON. Try again."

    # Upsert the cached result
    existing = AIAnalysis.query.filter_by(
        application_id=app_obj.id, analysis_type=analysis_type
    ).first()
    if existing:
        existing.result_json = raw
        from datetime import datetime, timezone
        existing.created_at = datetime.now(timezone.utc)
    else:
        db.session.add(AIAnalysis(
            application_id=app_obj.id,
            analysis_type=analysis_type,
            result_json=raw,
        ))
    db.session.commit()

    _rate_limit_store[rate_key] = time.time()
    return result, None


def _get_cached(app_id, analysis_type):
    """Return parsed result dict from cache, or None."""
    row = AIAnalysis.query.filter_by(
        application_id=app_id, analysis_type=analysis_type
    ).first()
    if row:
        try:
            return json.loads(row.result_json), row.created_at
        except json.JSONDecodeError:
            return None, None
    return None, None


_TYPE_MAP = {t.value: t for t in AnalysisType}
_TEMPLATE_MAP = {
    AnalysisType.SKILLS:      "applications/_ai_result_skills.html",
    AnalysisType.FIT_SUMMARY: "applications/_ai_result_fit.html",
    AnalysisType.INTERVIEW:   "applications/_ai_result_interview.html",
}


@bp.route("/<int:app_id>/analyze/<analysis_type>", methods=["POST"])
@require_admin
def run_analysis(app_id, analysis_type):
    app_obj = Application.query.get_or_404(app_id)
    atype = _TYPE_MAP.get(analysis_type)
    if not atype:
        abort(404)

    result, error = _run_analysis(app_obj, atype)
    cached_at = None
    if result:
        _, cached_at = _get_cached(app_id, atype)

    return render_template(
        _TEMPLATE_MAP[atype],
        result=result,
        error=error,
        cached_at=cached_at,
        app=app_obj,
    )


@bp.route("/<int:app_id>/analyze/<analysis_type>/delete", methods=["POST"])
@require_admin
def delete_analysis(app_id, analysis_type):
    atype = _TYPE_MAP.get(analysis_type)
    if not atype:
        abort(404)
    AIAnalysis.query.filter_by(application_id=app_id, analysis_type=atype).delete()
    db.session.commit()
    return render_template(
        _TEMPLATE_MAP[atype],
        result=None,
        error=None,
        cached_at=None,
        app=Application.query.get_or_404(app_id),
    )
