"""
models.py — Pydantic schemas for the Finance Credit Follow-Up Email Agent.
All LLM outputs are validated through these models (hallucination guard).
"""

from __future__ import annotations
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import bleach


class FollowUpStage(str, Enum):
    STAGE_1 = "stage_1"   # 1-7 days overdue  — Warm & Friendly
    STAGE_2 = "stage_2"   # 8-14 days overdue  — Polite but Firm
    STAGE_3 = "stage_3"   # 15-21 days overdue — Formal & Serious
    STAGE_4 = "stage_4"   # 22-30 days overdue — Stern & Urgent
    ESCALATED = "escalated"  # 30+ days          — Flag for Legal


class ToneConfig(BaseModel):
    stage: FollowUpStage
    tone_label: str
    days_min: int
    days_max: Optional[int]   # None means unbounded
    key_message: str
    cta: str


# Tone escalation matrix — single source of truth
TONE_MATRIX: list[ToneConfig] = [
    ToneConfig(
        stage=FollowUpStage.STAGE_1,
        tone_label="Warm & Friendly",
        days_min=1, days_max=7,
        key_message="Gentle reminder, assume oversight",
        cta="Pay now link / bank details",
    ),
    ToneConfig(
        stage=FollowUpStage.STAGE_2,
        tone_label="Polite but Firm",
        days_min=8, days_max=14,
        key_message="Payment still pending; request confirmation",
        cta="Confirm payment date",
    ),
    ToneConfig(
        stage=FollowUpStage.STAGE_3,
        tone_label="Formal & Serious",
        days_min=15, days_max=21,
        key_message="Escalating concern; mention impact on credit terms",
        cta="Respond within 48 hours",
    ),
    ToneConfig(
        stage=FollowUpStage.STAGE_4,
        tone_label="Stern & Urgent",
        days_min=22, days_max=30,
        key_message="Final reminder before escalation to legal",
        cta="Pay immediately or call us",
    ),
    ToneConfig(
        stage=FollowUpStage.ESCALATED,
        tone_label="Escalated — Human Review",
        days_min=31, days_max=None,
        key_message="Flagged for legal/finance manager review",
        cta="Assign to finance manager",
    ),
]


class InvoiceRecord(BaseModel):
    """One row from the CSV / Excel data source."""
    invoice_no: str = Field(..., min_length=1, max_length=50)
    client_name: str = Field(..., min_length=1, max_length=200)
    client_email: str        # validated below
    amount: float = Field(..., gt=0)
    currency: str = Field(default="INR", max_length=10)
    due_date: date
    follow_up_count: int = Field(..., ge=0)
    contact_person: str = Field(..., max_length=200)
    payment_link: str = Field(..., max_length=500)

    @field_validator("client_name", "contact_person", mode="before")
    @classmethod
    def sanitise_text(cls, v: str) -> str:
        """Strip HTML/JS to prevent prompt injection via data fields."""
        return bleach.clean(str(v), tags=[], strip=True).strip()

    @field_validator("invoice_no", mode="before")
    @classmethod
    def sanitise_invoice_no(cls, v: str) -> str:
        import re
        cleaned = re.sub(r"[^A-Za-z0-9\-_]", "", str(v))
        return cleaned

    @field_validator("client_email", mode="before")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        import re
        pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, str(v)):
            raise ValueError(f"Invalid email address: {v}")
        return str(v).lower().strip()

    @property
    def days_overdue(self) -> int:
        return (date.today() - self.due_date).days

    @property
    def stage(self) -> FollowUpStage:
        d = self.days_overdue
        if d <= 0:
            return FollowUpStage.STAGE_1   # not yet overdue — shouldn't be processed
        elif d <= 7:
            return FollowUpStage.STAGE_1
        elif d <= 14:
            return FollowUpStage.STAGE_2
        elif d <= 21:
            return FollowUpStage.STAGE_3
        elif d <= 30:
            return FollowUpStage.STAGE_4
        else:
            return FollowUpStage.ESCALATED

    @property
    def formatted_amount(self) -> str:
        return f"₹{self.amount:,.0f}" if self.currency == "INR" else f"{self.currency} {self.amount:,.2f}"


class GeneratedEmail(BaseModel):
    """Validated LLM output — every field must be present and non-empty."""
    subject: str = Field(..., min_length=5, max_length=200)
    body: str = Field(..., min_length=50, max_length=5000)
    tone_used: str
    stage: FollowUpStage

    @field_validator("subject", "body", mode="before")
    @classmethod
    def no_empty_strings(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("LLM returned empty field — regeneration required.")
        return str(v).strip()


class AuditLogEntry(BaseModel):
    """Every email action is logged here for audit trail."""
    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    invoice_no: str
    client_name_masked: str   # PII masked in logs: "Rajesh K." not full name
    amount: float
    currency: str
    days_overdue: int
    stage: FollowUpStage
    tone_used: str
    subject: str
    body_preview: str         # First 120 chars only — no full PII in logs
    send_status: str          # "sent" | "dry_run" | "failed" | "escalated"
    error_message: Optional[str] = None
    override_reason: Optional[str] = None

    @classmethod
    def from_invoice_and_email(
        cls,
        invoice: InvoiceRecord,
        email: Optional[GeneratedEmail],
        send_status: str,
        error_message: Optional[str] = None,
    ) -> "AuditLogEntry":
        # Mask PII: keep first name + last initial only
        parts = invoice.client_name.split()
        masked = f"{parts[0]} {parts[-1][0]}." if len(parts) > 1 else parts[0]
        
        return cls(
            invoice_no=invoice.invoice_no,
            client_name_masked=masked,
            amount=invoice.amount,
            currency=invoice.currency,
            days_overdue=invoice.days_overdue,
            stage=email.stage if email else invoice.stage,
            tone_used=email.tone_used if email else "N/A",
            subject=email.subject if email else "N/A",
            body_preview=(email.body[:120] + "...") if email else (error_message or "No email generated"),
            send_status=send_status,
            error_message=error_message,
        )
