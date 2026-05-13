"""
audit_logger.py — SQLite audit trail for every email action.

Security mitigations:
  - PII masking: only first name + last initial stored in DB
  - Body preview only (120 chars) — no full email content with PII stored
  - Parameterised queries — no SQL injection possible
  - Timestamps in UTC
"""

from __future__ import annotations
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from models.schemas import AuditLogEntry, InvoiceRecord, GeneratedEmail

logger = logging.getLogger(__name__)

DB_PATH = Path(os.getenv("AUDIT_DB_PATH", "logs/audit.db"))


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create audit table if it doesn't exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_audit (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp           TEXT NOT NULL,
                invoice_no          TEXT NOT NULL,
                client_name_masked  TEXT NOT NULL,
                amount              REAL NOT NULL,
                currency            TEXT NOT NULL,
                days_overdue        INTEGER NOT NULL,
                stage               TEXT NOT NULL,
                tone_used           TEXT NOT NULL,
                subject             TEXT NOT NULL,
                body_preview        TEXT NOT NULL,
                send_status         TEXT NOT NULL,
                error_message       TEXT,
                override_reason     TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_invoice_no ON email_audit (invoice_no)
        """)
        conn.commit()
    logger.info(f"Audit DB initialised at {DB_PATH}")


def log_action(
    invoice: InvoiceRecord,
    email: Optional[GeneratedEmail],
    send_status: str,
    error_message: Optional[str] = None,
    override_reason: Optional[str] = None,
) -> int:
    """
    Insert an audit log row. Returns the new row id.
    """
    entry = AuditLogEntry.from_invoice_and_email(invoice, email, send_status, error_message)
    entry.override_reason = override_reason

    with _get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO email_audit
                (timestamp, invoice_no, client_name_masked, amount, currency,
                 days_overdue, stage, tone_used, subject, body_preview,
                 send_status, error_message, override_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                entry.invoice_no,
                entry.client_name_masked,
                entry.amount,
                entry.currency,
                entry.days_overdue,
                entry.stage.value,
                entry.tone_used,
                entry.subject,
                entry.body_preview,
                entry.send_status,
                entry.error_message,
                entry.override_reason,
            ),
        )
        conn.commit()
        row_id = cursor.lastrowid

    logger.info(f"Audit logged: {entry.invoice_no} | Status: {send_status} | Row ID: {row_id}")
    return row_id


def log_escalation(invoice: InvoiceRecord) -> int:
    """Log an escalated record (no email sent — flagged for manual review)."""
    with _get_conn() as conn:
        parts = invoice.client_name.split()
        masked = f"{parts[0]} {parts[-1][0]}." if len(parts) > 1 else parts[0]

        cursor = conn.execute(
            """
            INSERT INTO email_audit
                (timestamp, invoice_no, client_name_masked, amount, currency,
                 days_overdue, stage, tone_used, subject, body_preview,
                 send_status, error_message, override_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                invoice.invoice_no,
                masked,
                invoice.amount,
                invoice.currency,
                invoice.days_overdue,
                "escalated",
                "N/A — Escalated",
                "ESCALATION FLAG",
                f"Invoice {invoice.days_overdue} days overdue. Flagged for legal/finance review.",
                "escalated",
                None,
                "Auto-escalated: 30+ days overdue",
            ),
        )
        conn.commit()
        row_id = cursor.lastrowid

    logger.warning(f"ESCALATION logged: {invoice.invoice_no} | {invoice.days_overdue} days overdue")
    return row_id


def get_all_logs(limit: int = 500) -> list[dict]:
    """Fetch recent audit logs for the dashboard."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM email_audit ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    """Aggregate stats for the dashboard overview."""
    with _get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM email_audit").fetchone()[0]
        sent = conn.execute(
            "SELECT COUNT(*) FROM email_audit WHERE send_status IN ('sent','dry_run')"
        ).fetchone()[0]
        escalated = conn.execute(
            "SELECT COUNT(*) FROM email_audit WHERE send_status = 'escalated'"
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM email_audit WHERE send_status = 'failed'"
        ).fetchone()[0]
        stage_rows = conn.execute(
            "SELECT stage, COUNT(*) as cnt FROM email_audit GROUP BY stage"
        ).fetchall()

    return {
        "total": total,
        "sent": sent,
        "escalated": escalated,
        "failed": failed,
        "by_stage": {r["stage"]: r["cnt"] for r in stage_rows},
    }


def was_sent_for_stage(invoice_no: str, stage: str) -> bool:
    """Check if an email was already sent for this invoice and stage."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM email_audit WHERE invoice_no = ? AND stage = ? AND send_status IN ('sent', 'dry_run')",
            (invoice_no, stage),
        ).fetchone()
    return row is not None
