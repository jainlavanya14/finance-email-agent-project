from dotenv import load_dotenv
import os

load_dotenv()

# LLM Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Email Configuration (SMTP)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Finance Team")
EMAIL_FROM_ADDRESS = os.getenv("EMAIL_FROM_ADDRESS")

# Agent Behaviour
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Database
AUDIT_DB_PATH = os.getenv("AUDIT_DB_PATH", "logs/audit.db")

# Company Info
COMPANY_NAME = os.getenv("COMPANY_NAME", "Your Company Ltd")
COMPANY_PHONE = os.getenv("COMPANY_PHONE", "+91-XXXXXXXXXX")
FINANCE_MANAGER_EMAIL = os.getenv("FINANCE_MANAGER_EMAIL")