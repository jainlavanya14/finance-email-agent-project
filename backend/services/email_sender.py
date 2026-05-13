"""
email_sender.py — Send emails via SMTP or log in dry-run mode.

Security mitigations:
  - DRY_RUN=true by default — prevents accidental sends during development
  - Credentials loaded from environment variables only (never hardcoded)
  - TLS enforced (STARTTLS on port 587)
  - SPF/DKIM note: configure at DNS level for your domain (see README)
"""

from __future__ import annotations
import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

from models.schemas import GeneratedEmail, InvoiceRecord

load_dotenv()
logger = logging.getLogger(__name__)

DRY_RUN_LOG = Path("logs/dry_run_emails.txt")


def send_email(invoice: InvoiceRecord, email: GeneratedEmail) -> str:
    """
    Send an email or log it in dry-run mode.

    Returns:
        "sent" | "dry_run" | "failed"
    """
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"

    if dry_run:
        return _dry_run_log(invoice, email)
    else:
        return _smtp_send(invoice, email)


def _dry_run_log(invoice: InvoiceRecord, email: GeneratedEmail) -> str:
    """Log email to file instead of sending — safe for development & testing."""
    DRY_RUN_LOG.parent.mkdir(parents=True, exist_ok=True)

    separator = "=" * 70
    log_entry = f"""
{separator}
DRY RUN — {datetime.now(timezone.utc).isoformat()} UTC
TO: {invoice.client_email}
INVOICE: {invoice.invoice_no}
STAGE: {email.stage.value} | TONE: {email.tone_used}
SUBJECT: {email.subject}
{separator}
{email.body}
{separator}

"""
    with open(DRY_RUN_LOG, "a", encoding="utf-8") as f:
        f.write(log_entry)

    logger.info(f"[DRY RUN] Email logged for {invoice.invoice_no} → {invoice.client_email}")
    return "dry_run"


def _smtp_send(invoice: InvoiceRecord, email: GeneratedEmail) -> str:
    """Send via SMTP with TLS. Raises on failure."""
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_name = os.getenv("EMAIL_FROM_NAME", "Finance Team")
    from_addr = os.getenv("EMAIL_FROM_ADDRESS", username)

    if not username or not password:
        raise EnvironmentError("SMTP_USERNAME and SMTP_PASSWORD must be set in .env")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = email.subject
    msg["From"] = f"{from_name} <{from_addr}>"
    msg["To"] = invoice.client_email
    msg["X-Invoice-ID"] = invoice.invoice_no   # Custom header for tracking

    # Plain text body
    msg.attach(MIMEText(email.body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls()          # TLS enforced
            server.ehlo()
            server.login(username, password)
            server.sendmail(from_addr, [invoice.client_email], msg.as_string())

        logger.info(f"Email sent: {invoice.invoice_no} → {invoice.client_email}")
        return "sent"

    except smtplib.SMTPException as e:
        logger.error(f"SMTP error for {invoice.invoice_no}: {e}")
        return "failed"
