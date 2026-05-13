"""
email_generator.py — LLM-powered email generation using Google Gemini.
"""

from __future__ import annotations
import json
import logging
import os
import re
import time
from typing import Optional

import google.generativeai as genai
from google.api_core import exceptions
from dotenv import load_dotenv

from models.schemas import (
    InvoiceRecord,
    GeneratedEmail,
    FollowUpStage,
    TONE_MATRIX,
    ToneConfig,
)
from prompts.email_prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

load_dotenv()
logger = logging.getLogger(__name__)

# Initialise Gemini client once
_client: Optional[genai.GenerativeModel] = None


def get_client() -> genai.GenerativeModel:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("gemini_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY not set. Copy .env.example to .env and add your key."
            )
        genai.configure(api_key=api_key)
        _client = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPT
        )
    return _client


def _get_tone_config(stage: FollowUpStage) -> ToneConfig:
    for tc in TONE_MATRIX:
        if tc.stage == stage:
            return tc
    raise ValueError(f"No tone config found for stage: {stage}")


def _build_user_prompt(invoice: InvoiceRecord, tone: ToneConfig) -> str:
    """Build the user prompt using the template and sanitised fields."""
    return USER_PROMPT_TEMPLATE.format(
        tone_label=tone.tone_label,
        key_message=tone.key_message,
        cta=tone.cta,
        client_name=invoice.client_name,
        invoice_no=invoice.invoice_no,
        formatted_amount=invoice.formatted_amount,
        due_date=invoice.due_date.strftime('%d %b %Y'),
        days_overdue=invoice.days_overdue,
        payment_link=invoice.payment_link,
        follow_up_count=invoice.follow_up_count + 1,
        company_name=os.getenv("COMPANY_NAME", "Our Company"),
        company_phone=os.getenv("COMPANY_PHONE", "our office"),
        finance_email=os.getenv("FINANCE_MANAGER_EMAIL", "finance@company.com")
    )


def generate_email(invoice: InvoiceRecord, max_retries: int = 2) -> GeneratedEmail:
    """
    Call Gemini to generate a follow-up email for the given invoice.
    """
    if invoice.stage == FollowUpStage.ESCALATED:
        raise ValueError(
            f"Invoice {invoice.invoice_no} is ESCALATED — no email should be sent."
        )

    tone = _get_tone_config(invoice.stage)
    client = get_client()

    for attempt in range(max_retries + 1):
        try:
            from google.generativeai.types import GenerationConfig
            response = client.generate_content(
                contents=_build_user_prompt(invoice, tone),
                generation_config=GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=1000,
                    response_mime_type="application/json"
                )
            )

            raw_text = response.text
            match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
            json_str = match.group(1) if match else raw_text.strip()
            parsed = json.loads(json_str)

            return GeneratedEmail(
                subject=parsed["subject"],
                body=parsed["body"],
                tone_used=parsed.get("tone_used", tone.tone_label),
                stage=invoice.stage,
            )

        except exceptions.ResourceExhausted as e:
            wait_time = (attempt + 1) * 10
            if attempt == max_retries:
                raise RuntimeError(f"Quota exceeded after {max_retries + 1} attempts.") from e
            time.sleep(wait_time)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            if attempt == max_retries:
                raise RuntimeError(f"Failed to generate valid email: {e}") from e

