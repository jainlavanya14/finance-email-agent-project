"""
scheduler.py — Automated scheduling for the Finance Credit Follow-Up Email Agent.
Uses APScheduler to run the agent on a configurable interval.

Usage:
    python scheduler.py                        # runs daily at 9:00 AM
    python scheduler.py --interval hours --every 6   # runs every 6 hours
    python scheduler.py --interval minutes --every 30 # runs every 30 minutes (testing)

Security:
    - Credentials loaded from .env only
    - DRY_RUN respected from environment
    - Logs every run with timestamp to logs/scheduler.log
"""

from __future__ import annotations
import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

# ── Logging setup ──────────────────────────────────────────────────────────────
Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/scheduler.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── Invoice file path ──────────────────────────────────────────────────────────
INVOICE_FILE = os.getenv("INVOICE_FILE", "backend/data/invoices.csv")


# ── Core job function ──────────────────────────────────────────────────────────

def run_agent_job():
    """
    The scheduled job — loads invoices and runs the full agent pipeline.
    Called automatically by APScheduler on the configured trigger.
    """
    logger.info("=" * 60)
    logger.info(f"SCHEDULED RUN STARTED — {datetime.now(timezone.utc).isoformat()} UTC")
    logger.info(f"DRY_RUN = {os.getenv('DRY_RUN', 'true')}")
    logger.info("=" * 60)

    try:
        from services.data_ingestion import load_invoices, summarise_invoice_batch
        from agents.email_agent import run_agent_on_batch
        from services import audit_logger

        audit_logger.init_db()

        # Load overdue invoices
        invoices, skipped, errors = load_invoices(INVOICE_FILE, overdue_only=True)
        if skipped > 0:
            logger.warning(f"Scheduler skipped {skipped} rows in {INVOICE_FILE}")

        if not invoices:
            logger.info("No overdue invoices found — nothing to process.")
            return

        summary = summarise_invoice_batch(invoices)
        logger.info(
            f"Loaded {summary['total_invoices']} invoices | "
            f"Total overdue: ₹{summary['total_overdue_amount']:,.0f} | "
            f"Stages: {summary['stage_breakdown']}"
        )

        # Run agent
        results = run_agent_on_batch(invoices)

        # Summary log
        sent     = sum(1 for r in results if r.get("send_status") in ("sent", "dry_run"))
        escalated = sum(1 for r in results if r.get("send_status") == "escalated")
        failed   = sum(1 for r in results if r.get("send_status") == "failed")

        logger.info(
            f"SCHEDULED RUN COMPLETE — "
            f"Sent/DryRun: {sent} | Escalated: {escalated} | Failed: {failed}"
        )

    except Exception as e:
        logger.error(f"SCHEDULED RUN FAILED: {e}", exc_info=True)
        raise   # Re-raise so APScheduler logs it as a job error


# ── APScheduler event listeners ────────────────────────────────────────────────

def on_job_executed(event):
    logger.info(f"✅ Job '{event.job_id}' executed successfully.")


def on_job_error(event):
    logger.error(f"❌ Job '{event.job_id}' raised an exception: {event.exception}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Finance Email Agent Scheduler")
    parser.add_argument(
        "--interval",
        choices=["daily", "hours", "minutes"],
        default="daily",
        help="Schedule type: daily (cron 9AM), hours, or minutes (default: daily)",
    )
    parser.add_argument(
        "--every",
        type=int,
        default=1,
        help="How often to run when interval=hours or minutes (default: 1)",
    )
    parser.add_argument(
        "--hour",
        type=int,
        default=9,
        help="Hour to run daily job (24hr format, default: 9 = 9:00 AM)",
    )
    parser.add_argument(
        "--file",
        default="data/invoices.csv",
        help="Invoice file to process (default: data/invoices.csv)",
    )
    args = parser.parse_args()

    global INVOICE_FILE
    INVOICE_FILE = args.file

    scheduler = BlockingScheduler(timezone="Asia/Kolkata")
    scheduler.add_listener(on_job_executed, EVENT_JOB_EXECUTED)
    scheduler.add_listener(on_job_error, EVENT_JOB_ERROR)

    # Configure trigger
    if args.interval == "daily":
        trigger = CronTrigger(hour=args.hour, minute=0)
        schedule_desc = f"daily at {args.hour:02d}:00 IST"
    elif args.interval == "hours":
        trigger = IntervalTrigger(hours=args.every)
        schedule_desc = f"every {args.every} hour(s)"
    else:  # minutes
        trigger = IntervalTrigger(minutes=args.every)
        schedule_desc = f"every {args.every} minute(s)"

    scheduler.add_job(
        run_agent_job,
        trigger=trigger,
        id="finance_email_agent",
        name="Finance Credit Follow-Up Email Agent",
        max_instances=1,        # Prevent overlapping runs
        misfire_grace_time=300, # 5 min grace if job missed its slot
        replace_existing=True,
    )

    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    logger.info("=" * 60)
    logger.info("FINANCE EMAIL AGENT SCHEDULER STARTED")
    logger.info(f"Schedule   : {schedule_desc}")
    logger.info(f"Invoice file: {INVOICE_FILE}")
    logger.info(f"Mode       : {'🔵 DRY RUN' if dry_run else '🔴 LIVE — real emails will be sent'}")
    logger.info("Press Ctrl+C to stop.")
    logger.info("=" * 60)

    # Run once immediately on startup
    logger.info("Running agent immediately on startup...")
    run_agent_job()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user.")


if __name__ == "__main__":
    main()