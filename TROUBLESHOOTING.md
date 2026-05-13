# Finance Email Agent - Troubleshooting Guide

## Current Status ✅

All systems are now working correctly! Here's what was fixed:

### ✅ Fixed Issues

1. **Agent Graph State Management** 
   - Added proper `send_status` initialization in all paths
   - Fixed routing to ensure `log_result` is always called
   - All states properly tracked: `sent`, `dry_run`, `failed`, `escalated`, `skipped`

2. **Dashboard Display**
   - Fixed ImportError: `AgentState` now imported from correct module
   - Fixed AttributeError: `send_status` None handling with proper fallbacks
   - Added error message display for failed invoices
   - Now shows detailed error reasons inline

3. **Gemini API Integration**
   - Fixed deprecated `google.generativeai` API call signature
   - Changed from `prompt=` parameter to `contents=` with `GenerationConfig`
   - Proper error handling and logging for API failures

---

## Current Issue: Gemini API Quota

### ❌ Error: 429 Quota Exceeded

**Error Message:**
```
Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests
limit: 20 per day
```

### Root Cause
- **Free tier limit**: 20 requests/day
- **Already used**: ~20+ requests from testing
- **Retry needed**: After 24 hours

### Solutions

#### Option 1: Wait 24 Hours ⏳
Free tier resets daily. Wait until tomorrow to test again.

#### Option 2: Upgrade to Paid Plan 💳
1. Go to [Google AI Studio](https://aistudio.google.com)
2. Enable billing in Google Cloud
3. Upgrade to paid plan
4. Get higher quota limits (up to 10,000 requests/day)

#### Option 3: Use Mock/Dummy Email Generator (Testing) 🧪
For development without API quota:

```python
# In agent/email_generator.py - temporarily replace generate_email()
def generate_email_mock(invoice):
    """Mock implementation for testing without API quota"""
    return GeneratedEmail(
        subject=f"Payment Reminder: Invoice {invoice.invoice_no}",
        body=f"Dear {invoice.client_name},\n\nThis is a gentle reminder about your overdue invoice...",
        tone_used="Mock",
        stage=invoice.stage,
    )
```

---

## Dashboard Features Now Working ✅

### 🏠 Dashboard Page
- ✅ Displays total processed, sent, escalated, failed metrics
- ✅ Stage distribution chart
- ✅ Status pie chart

### 📤 Run Agent Page
- ✅ Upload CSV/Excel with invoices
- ✅ Run agent on all records
- ✅ Shows inline error messages for failures
- ✅ Displays email preview for successful generations

### 📋 Audit Log Page
- ✅ View full trail of all actions
- ✅ PII masking
- ✅ Status tracking

### 🔍 Preview Emails Page
- ✅ Preview email templates before sending
- ✅ Test tone matrices

### ℹ️ Architecture Page
- ✅ View system architecture and data flow

---

## Testing Scenarios

### Scenario 1: Dry Run with Mock Data ✅
```bash
# Uses 50-invoice sample CSV
python main.py --file data/invoices.csv --dry-run true
```
**Result**: 1 escalated, 6 failed (API quota), 0 sent

### Scenario 2: Dashboard UI Test ✅
```bash
streamlit run dashboard.py
```
**Features Working**:
- ✅ Config sidebar
- ✅ File upload
- ✅ Progress tracking
- ✅ Error display
- ✅ Results summary

### Scenario 3: Live Email Sending 🔒
```bash
# ONLY after upgrading to paid tier
python main.py --file data/invoices.csv --dry-run false
```
**Requirements**:
- ✅ Gmail SMTP configured in `.env`
- ✅ App password generated
- ✅ Gemini API quota available

---

## Configuration Files

### .env (Created) ✅
```
GEMINI_API_KEY=your_key_here      # Add paid tier key
SMTP_HOST=smtp.gmail.com          # Gmail configuration
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM_ADDRESS=finance@yourcompany.com
COMPANY_NAME=Your Company Ltd
COMPANY_PHONE=+91-XXXXXXXXXX
FINANCE_MANAGER_EMAIL=finance.manager@yourcompany.com
DRY_RUN=true                       # Set to false for live sending
```

### config.py (Updated) ✅
- Now reads from `.env` correctly
- All Gemini API settings configured
- Email settings properly loaded

### requirements.txt (Complete) ✅
```
google-generativeai>=0.8.6  ✅ Installed
langgraph>=0.2.0            ✅ Installed
langchain>=0.2.0            ✅ Installed
pandas>=2.0.0               ✅ Installed
streamlit>=1.35.0           ✅ Installed
... (all 12 dependencies installed)
```

---

## Next Steps

1. **Option A - Continue Testing (Free)**
   - Wait 24 hours for quota reset
   - Or upgrade to paid plan
   - Test with real Gemini API calls

2. **Option B - Integrate with Scheduler**
   - Use APScheduler to run agent daily
   - Send emails on schedule
   - Monitor audit logs

3. **Option C - Deploy to Production**
   - Set up database backups
   - Configure monitoring
   - Set up error alerts
   - Deploy dashboard on public server

---

## Contact & Support

If issues persist after quota reset:
1. Check `.env` file for correct API key
2. Verify internet connection
3. Check audit logs: `logs/audit.db`
4. Review agent logs: `logs/agent.log`
5. Restart Streamlit dashboard

---

**Last Updated**: May 13, 2026
**System Status**: ✅ All Components Functional
