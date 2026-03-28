import enum
from datetime import datetime, timezone

from app import db


class ApplicationStatus(enum.Enum):
    APPLIED = "Applied"
    PHONE_SCREEN = "Phone Screen"
    TECHNICAL = "Technical"
    FINAL_ROUND = "Final Round"
    OFFER = "Offer"
    REJECTED = "Rejected"
    WITHDRAWN = "Withdrawn"


class ApplicationSource(enum.Enum):
    LINKEDIN = "LinkedIn"
    REFERRAL = "Referral"
    COLD_OUTREACH = "Cold Outreach"
    COMPANY_WEBSITE = "Company Website"
    JOB_BOARD = "Job Board"
    OTHER = "Other"


class CompanySize(enum.Enum):
    STARTUP = "Startup <50"
    MID_SIZE = "Mid-size 50-500"
    ENTERPRISE = "Enterprise 500+"


class CompanyType(enum.Enum):
    PUBLIC = "Public"
    PRIVATE = "Private"
    NONPROFIT = "Nonprofit"
    UNKNOWN = "Unknown"


class StageOutcome(enum.Enum):
    PENDING = "Pending"
    PASSED = "Passed"
    FAILED = "Failed"
    WITHDREW = "Withdrew"


def _now():
    return datetime.now(timezone.utc)


class Application(db.Model):
    __tablename__ = "application"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200), nullable=False)
    role_title = db.Column(db.String(200), nullable=False)
    date_applied = db.Column(db.Date, nullable=False)
    current_status = db.Column(
        db.Enum(ApplicationStatus, native_enum=False),
        nullable=False,
        default=ApplicationStatus.APPLIED,
    )
    source = db.Column(db.Enum(ApplicationSource, native_enum=False), nullable=False)
    salary_min = db.Column(db.Integer, nullable=True)
    salary_max = db.Column(db.Integer, nullable=True)
    company_size = db.Column(db.Enum(CompanySize, native_enum=False), nullable=False)
    company_type = db.Column(
        db.Enum(CompanyType, native_enum=False),
        nullable=False,
        default=CompanyType.UNKNOWN,
    )
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now)
    updated_at = db.Column(db.DateTime(timezone=True), default=_now, onupdate=_now)

    stage_events = db.relationship(
        "StageEvent",
        backref="application",
        lazy="select",
        order_by="StageEvent.occurred_on",
        cascade="all, delete-orphan",
    )

    def salary_display(self):
        if self.salary_min and self.salary_max:
            return f"${self.salary_min:,} – ${self.salary_max:,}"
        if self.salary_min:
            return f"${self.salary_min:,}+"
        if self.salary_max:
            return f"up to ${self.salary_max:,}"
        return "—"


class StageEvent(db.Model):
    __tablename__ = "stage_event"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer, db.ForeignKey("application.id"), nullable=False
    )
    stage = db.Column(db.Enum(ApplicationStatus, native_enum=False), nullable=False)
    occurred_on = db.Column(db.Date, nullable=False)
    outcome = db.Column(
        db.Enum(StageOutcome, native_enum=False),
        nullable=False,
        default=StageOutcome.PENDING,
    )
    notes = db.Column(db.Text, nullable=True)
