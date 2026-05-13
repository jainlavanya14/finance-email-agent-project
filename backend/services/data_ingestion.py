"""
data_loader.py — Ingest and validate invoice records from CSV / Excel.
Applies Pydantic validation + sanitisation on every row before agent processing.
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional
import pandas as pd
from datetime import date

from models.schemas import InvoiceRecord, FollowUpStage

logger = logging.getLogger(__name__)


def load_invoices(filepath: str | Path, overdue_only: bool = True) -> tuple[list[InvoiceRecord], int, list[str]]:
    """
    Load invoice records from a CSV or Excel file.
    Returns: (records, skipped_count, error_messages)
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Invoice file not found: {filepath}")

    if filepath.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(filepath, dtype=str)
    elif filepath.suffix.lower() == ".csv":
        df = pd.read_csv(filepath, dtype=str)
    else:
        raise ValueError(f"Unsupported file format: {filepath.suffix}")

    records: list[InvoiceRecord] = []
    skipped = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            # Clean amount: remove currency symbols and commas
            raw_amount = str(row.get("amount", "0"))
            import re
            clean_amount = re.sub(r"[^\d.]", "", raw_amount)
            
            record = InvoiceRecord(
                invoice_no=row.get("invoice_no", row.get("Invoice Number", "")),
                client_name=row.get("client_name", row.get("Client Name", "")),
                client_email=row.get("client_email", row.get("Email", "")),
                amount=float(clean_amount) if clean_amount else 0.0,
                currency=row.get("currency", "INR"),
                due_date=pd.to_datetime(row.get("due_date", row.get("Due Date"))).date(),
                follow_up_count=int(row.get("follow_up_count", 0)),
                contact_person=row.get("contact_person", row.get("client_name", "")),
                payment_link=row.get("payment_link", "https://pay.example.com"),
            )

            if overdue_only and record.due_date >= date.today():
                continue

            if record.stage == FollowUpStage.ESCALATED and record.follow_up_count > 4:
                continue

            records.append(record)

        except Exception as e:
            skipped += 1
            errors.append(f"Row {idx + 2}: {str(e)}")

    return records, skipped, errors


def summarise_invoice_batch(records: list[InvoiceRecord]) -> dict:
    """Return a summary dict for dashboard display."""
    from collections import Counter
    stage_counts = Counter(r.stage.value for r in records)
    total_overdue_amount = sum(r.amount for r in records)
    return {
        "total_invoices": len(records),
        "total_overdue_amount": total_overdue_amount,
        "stage_breakdown": dict(stage_counts),
        "currencies": list({r.currency for r in records}),
    }
