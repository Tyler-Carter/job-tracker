"""
Versioned prompt registry for all AI features.

Usage:
    from prompts import PROMPTS, CURRENT_VERSION, SYSTEM_PROMPT
    prompt = PROMPTS[CURRENT_VERSION][key].format(...)

Version history:
    v1.0 — Initial prompts (skills, fit_summary, interview with string behavioral list)
    v1.1 — Enhanced interview prompt: behavioral items now include STAR outline objects.
            Added JD_ANALYZER and STRATEGY_ADVISOR for analytics page AI features.
"""

from models import AnalysisType

CURRENT_VERSION = "v1.1"

SYSTEM_PROMPT = (
    "You are an expert job application analyst. Be concise and practical. "
    "Always respond with ONLY valid JSON matching the schema specified in each request. "
    "Do not include any text outside the JSON object."
)

PROMPTS: dict[str, dict] = {
    # ------------------------------------------------------------------ #
    # v1.0 — original prompts, preserved verbatim for audit / rollback    #
    # ------------------------------------------------------------------ #
    "v1.0": {
        AnalysisType.SKILLS: """\
Analyze this job description for the role of "{role}" at "{company}".

Job Description:
---
{jd}
---

Extract the key skills and requirements. Respond with ONLY valid JSON matching this exact schema:
{{
  "required_skills": ["skill1", "skill2"],
  "nice_to_have_skills": ["skill1", "skill2"],
  "technologies": ["tech1", "tech2"],
  "experience_level": "junior|mid|senior|staff",
  "key_responsibilities": ["responsibility1", "responsibility2"]
}}""",

        AnalysisType.FIT_SUMMARY: """\
Analyze this job description for the role of "{role}" at "{company}" (a {size} {type} company).

Job Description:
---
{jd}
---

Write a practical summary of what this role involves and what the company is looking for.
Respond with ONLY valid JSON matching this exact schema:
{{
  "summary": "3-5 sentence plain text narrative",
  "role_type": "IC|manager|hybrid",
  "seniority_signal": "brief note on seniority signals in the JD",
  "red_flags": ["optional red flag if any"],
  "green_flags": ["positive signal"]
}}""",

        AnalysisType.INTERVIEW: """\
Prepare interview questions for a candidate applying for "{role}" at "{company}".

Job Description:
---
{jd}
---

Generate targeted questions the candidate is likely to be asked, based specifically on this job description.
Respond with ONLY valid JSON matching this exact schema:
{{
  "behavioral": ["question1", "question2", "question3"],
  "technical": ["question1", "question2", "question3"],
  "role_specific": ["question1", "question2"],
  "questions_to_ask_them": ["question1", "question2"]
}}""",
    },

    # ------------------------------------------------------------------ #
    # v1.1 — current production prompts                                   #
    # ------------------------------------------------------------------ #
    "v1.1": {
        # Unchanged from v1.0
        AnalysisType.SKILLS: """\
Analyze this job description for the role of "{role}" at "{company}".

Job Description:
---
{jd}
---

Extract the key skills and requirements. Respond with ONLY valid JSON matching this exact schema:
{{
  "required_skills": ["skill1", "skill2"],
  "nice_to_have_skills": ["skill1", "skill2"],
  "technologies": ["tech1", "tech2"],
  "experience_level": "junior|mid|senior|staff",
  "key_responsibilities": ["responsibility1", "responsibility2"]
}}""",

        # Unchanged from v1.0
        AnalysisType.FIT_SUMMARY: """\
Analyze this job description for the role of "{role}" at "{company}" (a {size} {type} company).

Job Description:
---
{jd}
---

Write a practical summary of what this role involves and what the company is looking for.
Respond with ONLY valid JSON matching this exact schema:
{{
  "summary": "3-5 sentence plain text narrative",
  "role_type": "IC|manager|hybrid",
  "seniority_signal": "brief note on seniority signals in the JD",
  "red_flags": ["optional red flag if any"],
  "green_flags": ["positive signal"]
}}""",

        # Enhanced: behavioral items now include STAR outline objects
        AnalysisType.INTERVIEW: """\
Prepare interview questions for a candidate applying for "{role}" at "{company}".

Job Description:
---
{jd}
---

Generate 10 targeted questions based specifically on this job description.
For behavioral questions, include a STAR framework outline to help structure the answer.
Respond with ONLY valid JSON matching this exact schema:
{{
  "behavioral": [
    {{
      "question": "Tell me about a time you...",
      "star_outline": {{
        "situation": "brief prompt for setting up the context",
        "task": "what was expected or required of you",
        "action": "specific steps or skills to highlight",
        "result": "measurable outcome or impact to emphasize"
      }}
    }}
  ],
  "technical": ["question1", "question2", "question3"],
  "role_specific": ["question1", "question2"],
  "questions_to_ask_them": ["question1", "question2"]
}}
Include 3 behavioral entries, 3 technical, 2 role_specific, and 2 questions_to_ask_them.""",

        # New: analytics page JD paste-and-analyze tool
        "JD_ANALYZER": """\
Analyze the following job description and extract structured information.

Job Description:
---
{jd}
---

Identify skills, seniority, red flags (e.g. "wear many hats", "rockstar", "move fast and break things",
"family culture", "unlimited PTO", missing salary), green flags (e.g. explicit salary range, clear scope,
DEI metrics, transparent process), and culture signals.
Respond with ONLY valid JSON matching this exact schema:
{{
  "required_skills": ["skill1", "skill2"],
  "nice_to_haves": ["skill1", "skill2"],
  "seniority_level": "junior|mid|senior|staff|not specified",
  "red_flags": ["e.g. wear many hats — unclear role scope"],
  "green_flags": ["e.g. explicit salary range listed"],
  "company_culture_cues": ["e.g. async-first", "high ownership"],
  "role_type": "IC|manager|hybrid|unclear"
}}""",

        # New: analytics page strategy advisor (used with stream=True — no response_format)
        "STRATEGY_ADVISOR": """\
You are a career strategist analyzing a job seeker's complete application history.

Application data (JSON array, one object per application):
{applications_json}

Fields per application: source, status, company_size, date_applied, days_to_respond (null if no response yet).

Analyze the data and produce a concise strategy report. Look for:
- Which sources (LinkedIn, Referral, etc.) generate the highest callback rates
- Which company sizes show better outcomes
- Where the funnel is leaking (most applications stalling at a particular stage)
- Pacing patterns (volume vs. outcome timing)
- Specific, actionable recommendations

Respond with ONLY valid JSON matching this exact schema:
{{
  "headline": "One punchy sentence summarizing the single most important finding",
  "source_analysis": "2-3 sentences on which sources are working and which are not, with specific percentages if possible",
  "funnel_analysis": "2-3 sentences on where the pipeline is leaking and what stage is the bottleneck",
  "pacing_analysis": "1-2 sentences on application volume and timing patterns",
  "top_recommendations": [
    "Specific, actionable recommendation 1",
    "Specific, actionable recommendation 2",
    "Specific, actionable recommendation 3"
  ],
  "encouragement": "One motivating closing sentence grounded in the data"
}}""",
    },
}
