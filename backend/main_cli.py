"""
main.py — CLI entry point for the Finance Credit Follow-Up Email Agent.

Usage:
    python main.py --file data/invoices.csv
    python main.py --file data/invoices.xlsx --dry-run true
    python main.py --file data/invoices.csv --dry-run false   # LIVE MODE — sends real emails!
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/agent.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Finance Credit Follow-Up Email Agent"
    )
    parser.add_argument(
        "--file",
        default="backend/data/invoices.csv",
        help="Path to CSV or Excel invoice file (default: backend/data/invoices.csv)",
    )
    parser.add_argument(
        "--dry-run",
        choices=["true", "false"],
        default=None,
        help="Override DRY_RUN env variable. true = log only, false = send real emails.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all records, including non-overdue ones.",
    )
    args = parser.parse_args()

    # Override dry-run from CLI if provided
    if args.dry_run is not None:
        os.environ["DRY_RUN"] = args.dry_run
        logger.info(f"DRY_RUN overridden to: {args.dry_run}")

    dry_run_mode = os.getenv("DRY_RUN", "true").lower() == "true"
    logger.info(f"{'🔵 DRY RUN MODE' if dry_run_mode else '🔴 LIVE MODE — EMAILS WILL BE SENT'}")

    if not dry_run_mode:
        confirm = input(
            "\n⚠️  WARNING: You are about to send REAL emails to clients.\n"
            "Type 'CONFIRM' to proceed: "
        ).strip()
        if confirm != "CONFIRM":
            logger.info("Aborted by user.")
            sys.exit(0)

    # Import here so env vars are set before any module initialises the LLM client
    from services.data_ingestion import load_invoices, summarise_invoice_batch
    from agents.email_agent import run_agent_on_batch
    from services import audit_logger

    # Ensure log dir exists
    Path("logs").mkdir(exist_ok=True)
    audit_logger.init_db()

    # Load data
    logger.info(f"Loading invoices from: {args.file}")
    invoices, skipped, errors = load_invoices(args.file, overdue_only=not args.all)
    if skipped > 0:
        logger.warning(f"Skipped {skipped} rows due to errors: {errors}")

    if not invoices:
        logger.warning("No overdue invoices found. Nothing to process.")
        sys.exit(0)

    summary = summarise_invoice_batch(invoices)
    logger.info(
        f"Summary — Total: {summary['total_invoices']} | "
        f"Total Overdue: {summary['total_overdue_amount']:,.0f} | "
        f"Stages: {summary['stage_breakdown']}"
    )

    # Run agent
    results = run_agent_on_batch(invoices)

    # Print final summary
    print("\n" + "=" * 60)
    print("AGENT RUN COMPLETE")
    print("=" * 60)
    for r in results:
        inv = r["invoice"]
        status = r.get("send_status") or "failed"
        emoji = {"sent": "✅", "dry_run": "📋", "escalated": "🚨", "failed": "❌"}.get(status, "❓")
        error = f" --- {r['error_message']}" if r.get("error_message") else ""
        print(f"{emoji} {inv.invoice_no} | {inv.client_name} | {inv.days_overdue}d overdue | {status.upper()}{error}")

    print("=" * 60)
    print(f"Check logs/ directory for full audit trail.")


if __name__ == "__main__":
    main()