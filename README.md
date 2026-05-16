# Finance Email Agent 📧

A sophisticated AI-powered debt recovery system that automatically generates and sends personalized financial follow-up emails using LangGraph and Google Generative AI.

## Project Overview

The Finance Email Agent is an intelligent automation platform designed to streamline debt recovery processes for financial institutions. It leverages cutting-edge LLM technology combined with a robust agentic framework to:

- **Automatically classify** invoice statuses and payment priority
- **Generate personalized** follow-up emails using contextual LLM analysis
- **Manage escalations** for high-risk or complex payment situations
- **Track communications** with comprehensive audit logging
- **Support scheduled** batch processing through APScheduler
- **Enable dry-run testing** for risk-free email generation and validation

### Key Features

✨ **AI-Powered Email Generation** — Context-aware emails tailored to invoice history and customer relationship  
🔄 **Agent-Based Workflow** — LangGraph state machine ensures consistent, auditable processing  
🛡️ **Security-First Design** — Environment-based secrets, audit trails, and HTML sanitization  
📊 **Data Ingestion** — Supports CSV/Excel uploads with validation and error handling  
🔍 **Audit Trail** — SQLite database logs all email attempts, failures, and escalations  
⏰ **Scheduling** — APScheduler integration for automated batch runs  
🎨 **Dual UI** — FastAPI backend + Streamlit dashboard for testing and monitoring  

---

## Demo Video

Watch the Finance Email Agent in action:

📹 [**View Demo Video**](https://drive.google.com/file/d/1bbAzkkJpcGtzGULZIVExfcY1z_Nt4fTI/view?usp=sharing)

---

## Repository

🔗 [**GitHub Repository**](https://github.com/jainlavanya14/finance-email-agent-project.git)

---

## Setup Instructions

### Prerequisites

- Python 3.9+
- Virtual environment (venv/conda)
- Google Generative AI API Key
- SMTP credentials (Gmail or other provider)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jainlavanya14/finance-email-agent-project.git
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   Create a `.env` file in the project root with:
   ```env
   # LLM Configuration
   GEMINI_API_KEY=your_google_api_key_here
   
   # SMTP Configuration
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=your_app_password
   EMAIL_FROM_NAME=Finance Team
   EMAIL_FROM_ADDRESS=finance@yourcompany.com
   
   # Agent Behaviour
   DRY_RUN=true  # Set to false to actually send emails
   LOG_LEVEL=INFO
   
   # Database
   AUDIT_DB_PATH=logs/audit.db
   
   # Company Information
   COMPANY_NAME=Your Company Ltd
   COMPANY_PHONE=+1-XXXXXXXXXX
   FINANCE_MANAGER_EMAIL=manager@yourcompany.com
   ```

5. **Verify installation**:
   ```bash
   python backend/main.py
   ```

### Running the Application

**FastAPI Server** (REST API):
```bash
uvicorn backend.main:app --reload --port 8000
```
Access at `http://localhost:8000` and view docs at `http://localhost:8000/docs`

**Streamlit Dashboard** (UI for testing):
```bash
streamlit run backend/streamlit_app.py
```
Access at `http://localhost:8501`

**CLI Mode** (batch processing):
```bash
python backend/main_cli.py --input data/invoices.csv --dry-run
```

---

## Agent Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                      Finance Email Agent                         │
│                    (LangGraph Orchestration)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
          ┌─────▼────┐  ┌─────▼────┐  ┌───▼──────┐
          │   INPUT  │  │  CLASSIFY│  │ ESCALATE │
          │  DATA    │  │ INVOICE  │  │ CHECK    │
          └─────┬────┘  └────┬─────┘  └────┬─────┘
                │             │             │
                └─────────────┼─────────────┘
                              │
                    ┌─────────▼─────────┐
                    │ LLM EMAIL         │
                    │ GENERATION        │
                    │ (Gemini API)      │
                    └────────┬──────────┘
                             │
                    ┌────────▼────────┐
                    │ SEND EMAIL      │
                    │ (SMTP) or DRY   │
                    │ RUN             │
                    └────────┬────────┘
                             │
                    ┌────────▼─────────┐
                    │ AUDIT LOG        │
                    │ (SQLite DB)      │
                    └──────────────────┘
```

### Workflow Nodes

| Node | Purpose | Output |
|------|---------|--------|
| **load_data** | Parse invoice CSV/Excel files | Validated invoice records |
| **classify_invoice** | Determine action (send/escalate/skip) | Action decision |
| **generate_email** | Call Gemini LLM for personalized content | Email object (subject + body) |
| **send_email** | SMTP dispatch or dry-run logging | Send status & tracking ID |
| **log_result** | Record in audit database | Audit trail entry |

### State Management

The agent uses a `TypedDict` state schema passed between nodes:

```python
class AgentState(TypedDict):
    invoice: InvoiceRecord        # Current invoice being processed
    email: Optional[GeneratedEmail]  # Generated email content
    send_status: Optional[str]    # "sent", "skipped", "failed", "escalated"
    error_message: Optional[str]  # Error details if failed
    action: Optional[Literal["send_email", "escalate", "skip"]]
    override_reason: Optional[str]  # Human override notes
```

---

## LLM & Framework Choices

### Why Google Generative AI (Gemini)?

✅ **Cost-Effective** — Competitive pricing with generous free tier for development  
✅ **Fast Inference** — Low-latency responses suitable for batch processing  
✅ **Reliable** — Production-grade stability and uptime SLAs  
✅ **Easy Integration** — Simple Python API with minimal boilerplate  
✅ **Context Window** — Sufficient context for invoice history and personalization  

**Alternative Considered**: OpenAI GPT-4 (rejected due to higher cost at scale for batch operations)

### Why LangGraph for Orchestration?

✅ **Deterministic Workflows** — State machines ensure reproducible, auditable agent behavior  
✅ **Scalability** — Built-in support for parallel node execution and retries  
✅ **Observability** — Native integration with LangSmith for monitoring and debugging  
✅ **Type Safety** — TypedDict enforces strict state contracts between nodes  
✅ **Resilience** — Built-in error handling and fallback mechanisms  
✅ **Human-in-the-Loop** — Supports interrupts for manual review nodes (escalation handling)  

**Alternative Considered**: CrewAI (rejected due to tighter coupling and less transparent control flow)

### Why FastAPI + Streamlit?

- **FastAPI**: Production-ready REST API with automatic OpenAPI documentation
- **Streamlit**: Rapid prototyping and business user dashboards without frontend complexity

---

## Security Mitigations

### 🔐 **Secrets Management**
- All credentials stored in environment variables (`.env` file)
- Never hardcoded API keys, passwords, or tokens
- `.env` file excluded from version control via `.gitignore`

### 🧹 **Input Sanitization**
- HTML content sanitized using `bleach` library to prevent injection attacks
- User-supplied email bodies escaped before SMTP dispatch
- CSV uploads validated for structure and content

### 🔐 **Authentication & Authorization**
- SMTP credentials encrypted via app-specific passwords (Gmail)
- API endpoints can be secured with JWT tokens (future enhancement)
- Audit logs track all operations with timestamps and user context

### 🛡️ **Email Security**
- SMTP over TLS (port 587) for encrypted email transmission
- Sender validation to prevent spoofing
- Email headers sanitized to prevent header injection attacks

### 📊 **Audit & Compliance**
- **Immutable Audit Trail**: SQLite database logs every email attempt with:
  - Invoice ID, recipient, timestamp
  - Email content hash (for verification)
  - Send status and any errors
  - User/agent identifier
- **DRY RUN MODE**: Default safe mode logs emails without sending
  - Enables testing without risking accidental outreach
  - Validates LLM output before production deployment

### 🚨 **Error Handling**
- Failed emails don't crash the system; logged for manual review
- Escalation node prevents sending to high-risk accounts
- Rate limiting on Gemini API calls to prevent quota exhaustion

### 📝 **Data Privacy**
- Invoice data stored securely with minimal personally identifiable information
- Logs purged after configurable retention period (future feature)
- GDPR compliance ready with data deletion endpoints (future feature)

---

## Project Structure

```
finance-email-agent/
├── backend/
│   ├── agents/
│   │   └── email_agent.py          # LangGraph agent orchestration
│   ├── services/
│   │   ├── email_generator.py      # LLM email composition
│   │   ├── email_sender.py         # SMTP dispatch
│   │   ├── data_ingestion.py       # CSV/Excel parsing
│   │   └── audit_logger.py         # Audit trail database
│   ├── models/
│   │   └── schemas.py              # Pydantic models (InvoiceRecord, etc.)
│   ├── prompts/
│   │   └── email_prompts.py        # LLM system/user prompts
│   ├── config.py                   # Environment configuration
│   ├── main.py                     # FastAPI application
│   ├── main_cli.py                 # CLI entry point
│   ├── streamlit_app.py            # Streamlit dashboard
│   └── scheduler.py                # APScheduler integration
├── data/
│   ├── invoices.csv                # Sample invoice data
│   └── uploads/                    # User-uploaded files
├── logs/
│   ├── audit.db                    # SQLite audit trail
│   └── dry_run_emails.txt          # Dry-run output log
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

---

## Testing & Validation

### Manual Testing (CLI)
```bash
# Test with dry-run mode (emails not sent)
python backend/main_cli.py --input data/invoices.csv --dry-run

# Review dry-run output
cat logs/dry_run_emails.txt
```

### API Testing
```bash
# Upload and process invoices via API
curl -X POST "http://localhost:8000/api/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@data/invoices.csv"

# Fetch audit logs
curl "http://localhost:8000/api/audit-logs"
```

### Unit Tests
```bash
pytest backend/tests/ -v
```

---

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes and test locally with dry-run mode
3. Commit with clear messages: `git commit -m "feat: add escalation thresholds"`
4. Push and open a Pull Request

---

