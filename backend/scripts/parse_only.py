#!/usr/bin/env python3
"""Parse and classify invoices WITHOUT email generation (API calls).
This tests the data flow: load → classify → escalate → log
Email generation comes later.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.data_loader import load_invoices, summarise_invoice_batch
from agent.models import FollowUpStage
from agent import audit_logger
import logging

logging.basicConfig(
    level="INFO",
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

print("=" * 70)
print("📋 INVOICE PARSER (No API Calls - Parse Only)")
print("=" * 70)

# Load invoices
print("\n🔄 Loading invoices from data/invoices.csv...")
try:
    invoices = load_invoices("data/invoices.csv", overdue_only=True)
    print(f"✅ Loaded {len(invoices)} overdue invoices\n")
except Exception as e:
    print(f"❌ Failed to load invoices: {e}")
    sys.exit(1)

# Initialize audit DB
audit_logger.init_db()

# Display summary
summary = summarise_invoice_batch(invoices)
print(f"📊 SUMMARY")
print(f"   Total invoices: {summary['total_invoices']}")
print(f"   Total overdue amount: ₹{summary['total_overdue_amount']:,.0f}")
print()

# Classify and display
print("=" * 70)
print("📌 INVOICE CLASSIFICATION")
print("=" * 70)
print()

stage_counts = {
    FollowUpStage.STAGE_1: 0,
    FollowUpStage.STAGE_2: 0,
    FollowUpStage.STAGE_3: 0,
    FollowUpStage.STAGE_4: 0,
    FollowUpStage.ESCALATED: 0,
}

for inv in invoices:
    stage_counts[inv.stage] += 1
    
    if inv.stage == FollowUpStage.ESCALATED:
        emoji = "🚨"
        action = "ESCALATE"
    else:
        emoji = "📧"
        action = "GENERATE EMAIL (later)"
    
    print(f"{emoji} {inv.invoice_no:15} | {inv.client_name:20} | {inv.days_overdue:3}d overdue | Stage: {inv.stage.value:12} | {action}")

print()
print("=" * 70)
print("📊 STAGE BREAKDOWN")
print("=" * 70)
print(f"Stage 1 (1-7d):     {stage_counts[FollowUpStage.STAGE_1]} invoices")
print(f"Stage 2 (8-14d):    {stage_counts[FollowUpStage.STAGE_2]} invoices")
print(f"Stage 3 (15-21d):   {stage_counts[FollowUpStage.STAGE_3]} invoices")
print(f"Stage 4 (22-30d):   {stage_counts[FollowUpStage.STAGE_4]} invoices")
print(f"ESCALATED (30+d):   {stage_counts[FollowUpStage.ESCALATED]} invoices")

print()
print("=" * 70)
print("✅ PARSING COMPLETE - No API calls made")
print("=" * 70)
print()
print("Next steps:")
print("1. ✅ Data parsed and classified")
print("2. ⏳ Email generation ready (when API quota available)")
print("3. 📤 Send emails in batches")
print()
