"""
agent_graph.py — LangGraph-based orchestration agent for the Finance Email workflow.

Agent Flow (nodes):
  load_data → classify_invoice → [escalate | generate_email] → send_email → log_result → END

The graph processes each invoice independently through a stateful node pipeline.
"""

from __future__ import annotations
import logging
import time
from typing import TypedDict, Optional, Literal

from langgraph.graph import StateGraph, END

from models.schemas import InvoiceRecord, GeneratedEmail, FollowUpStage
from services.email_generator import generate_email
from services.email_sender import send_email
from services import audit_logger

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# State schema — passed between graph nodes
# ─────────────────────────────────────────────

class AgentState(TypedDict):
    invoice: InvoiceRecord
    email: Optional[GeneratedEmail]
    send_status: Optional[str]
    error_message: Optional[str]
    action: Optional[Literal["send_email", "escalate", "skip"]]
    override_reason: Optional[str]


# ─────────────────────────────────────────────
# Node functions
# ─────────────────────────────────────────────

def classify_node(state: AgentState) -> AgentState:
    """Determine what action to take based on the invoice stage."""
    invoice = state["invoice"]

    if invoice.days_overdue <= 0:
        logger.info(f"{invoice.invoice_no}: Not overdue — skipping.")
        state["action"] = "skip"
        state["send_status"] = "skipped"
    elif audit_logger.was_sent_for_stage(invoice.invoice_no, invoice.stage.value):
        logger.info(f"{invoice.invoice_no}: Already sent for stage {invoice.stage.value} — skipping.")
        state["action"] = "skip"
        state["send_status"] = "already_processed"
    elif invoice.stage == FollowUpStage.ESCALATED:
        logger.warning(f"{invoice.invoice_no}: ESCALATED — flagging for human review.")
        state["action"] = "escalate"
    else:
        logger.info(f"{invoice.invoice_no}: Stage {invoice.stage} — generating email.")
        state["action"] = "send_email"

    return state


def generate_email_node(state: AgentState) -> AgentState:
    """Call LLM to generate the personalised email."""
    try:
        email = generate_email(state["invoice"])
        state["email"] = email
    except Exception as e:
        logger.error(f"Email generation failed for {state['invoice'].invoice_no}: {e}")
        state["error_message"] = str(e)
        state["action"] = "skip"
        state["send_status"] = "failed"
    return state


def send_email_node(state: AgentState) -> AgentState:
    """Send or dry-run log the email."""
    if not state.get("email"):
        state["send_status"] = "failed"
        state["error_message"] = "No email generated."
        return state

    try:
        status = send_email(state["invoice"], state["email"])
        state["send_status"] = status
    except Exception as e:
        logger.error(f"Send failed for {state['invoice'].invoice_no}: {e}")
        state["send_status"] = "failed"
        state["error_message"] = str(e)

    return state


def escalate_node(state: AgentState) -> AgentState:
    """Log escalation and mark for human review — no email sent."""
    audit_logger.log_escalation(state["invoice"])
    state["send_status"] = "escalated"
    return state


def log_result_node(state: AgentState) -> AgentState:
    """Write final result to the audit trail."""
    status = state.get("send_status")
    if status in ("sent", "dry_run", "failed", "skipped", "escalated"):
        # We log everything except 'skipped' if we want a clean audit trail.
        # But 'failed' and 'escalated' must definitely be logged.
        # Note: log_escalation is already called in escalate_node,
        # so we only call log_action if it's not already escalated.
        if status != "escalated":
            audit_logger.log_action(
                invoice=state["invoice"],
                email=state.get("email"),
                send_status=status,
                error_message=state.get("error_message"),
                override_reason=state.get("override_reason"),
            )
    return state


# ─────────────────────────────────────────────
# Routing logic
# ─────────────────────────────────────────────

def route_after_classify(state: AgentState) -> str:
    action = state.get("action", "skip")
    if action == "send_email":
        return "generate_email"
    elif action == "escalate":
        return "escalate"
    else:
        return "log_result"  # Log skipped/not overdue invoices


def route_after_generate(state: AgentState) -> str:
    if state.get("action") == "skip" or state.get("error_message"):
        return "log_result"  # Log failed email generations
    return "send_email"


# ─────────────────────────────────────────────
# Build the graph
# ─────────────────────────────────────────────

def build_agent() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("classify", classify_node)
    graph.add_node("generate_email", generate_email_node)
    graph.add_node("send_email", send_email_node)
    graph.add_node("escalate", escalate_node)
    graph.add_node("log_result", log_result_node)

    graph.set_entry_point("classify")

    graph.add_conditional_edges("classify", route_after_classify)
    graph.add_conditional_edges("generate_email", route_after_generate)

    graph.add_edge("send_email", "log_result")
    graph.add_edge("escalate", "log_result")
    graph.add_edge("log_result", END)

    return graph.compile()


# ─────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────

def run_agent_on_batch(invoices: list[InvoiceRecord]) -> list[AgentState]:
    """
    Process a list of invoices through the LangGraph agent.
    Returns list of final states (one per invoice).
    """
    audit_logger.init_db()
    agent = build_agent()
    results = []

    for i, invoice in enumerate(invoices):
        logger.info(f"Processing: {invoice.invoice_no}")
        initial_state: AgentState = {
            "invoice": invoice,
            "email": None,
            "send_status": None,
            "error_message": None,
            "action": None,
            "override_reason": None,
        }
        final_state = agent.invoke(initial_state)
        results.append(final_state)

        # Rate limit mitigation: 5 RPM limit on free tier Gemini. 
        # Add delay if we have more invoices to process and this one required (or might have required) an LLM call.
        if i < len(invoices) - 1:
            # Only sleep if we didn't skip/escalate without LLM
            if final_state.get("action") == "send_email":
                logger.info("Sleeping 15s to respect API rate limits...")
                time.sleep(15)

    sent = sum(1 for r in results if r.get("send_status") in ("sent", "dry_run"))
    escalated = sum(1 for r in results if r.get("send_status") == "escalated")
    failed = sum(1 for r in results if r.get("send_status") == "failed")

    logger.info(
        f"Batch complete — Total: {len(invoices)} | Sent/DryRun: {sent} | "
        f"Escalated: {escalated} | Failed: {failed}"
    )
    return results
