"""
email_prompts.py — System and User prompts for the AI Email Generation service.
"""

SYSTEM_PROMPT = """You are a professional finance email writer. Your job is to generate payment follow-up emails.

STRICT RULES:
1. Use ONLY the provided data.
2. Include: client name, invoice number, amount, due date, days overdue, and payment link.
3. Match the tone EXACTLY as specified.
4. Return ONLY a valid JSON object.
5. IMPORTANT: In the JSON "body" field, use '\\n' for newlines. Ensure the JSON is properly escaped and valid.

OUTPUT FORMAT:
{"subject": "...", "body": "...", "tone_used": "..."}"""

USER_PROMPT_TEMPLATE = """Generate a payment follow-up email with the following parameters:

TONE: {tone_label}
KEY MESSAGE: {key_message}
CALL TO ACTION: {cta}

INVOICE DATA:
- Client Name: {client_name}
- Invoice Number: {invoice_no}
- Amount Due: {formatted_amount}
- Original Due Date: {due_date}
- Days Overdue: {days_overdue} days
- Payment Link: {payment_link}
- Follow-Up Number: {follow_up_count}

SENDER:
- Company: {company_name}
- Phone: {company_phone}
- Finance Email: {finance_email}

Generate the email now. Return ONLY the JSON object."""
