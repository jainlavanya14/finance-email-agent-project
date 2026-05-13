"""
main.py — FastAPI entry point for the Debt Recovery System.
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import List

from models.schemas import InvoiceRecord
from services.data_ingestion import load_invoices, summarise_invoice_batch
from services import audit_logger
from agents.email_agent import run_agent_on_batch

app = FastAPI(title="Debt Recovery API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("backend/data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.on_event("startup")
def startup_event():
    audit_logger.init_db()

@app.get("/")
def read_root():
    return {"message": "Debt Recovery API is running"}

@app.post("/api/upload")
async def upload_invoices(file: UploadFile = File(...)):
    """Upload a CSV/Excel file and return enriched invoice data."""
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    try:
        invoices, skipped, errors = load_invoices(file_path, overdue_only=False)
        summary = summarise_invoice_batch(invoices)
        return {
            "filename": file.filename,
            "count": len(invoices),
            "skipped": skipped,
            "errors": errors,
            "summary": summary,
            "invoices": [inv.dict() for inv in invoices]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/process-email")
async def process_email(invoice: InvoiceRecord):
    """Process a single invoice through the Email Agent."""
    try:
        results = run_agent_on_batch([invoice])
        result = results[0]
        return {
            "invoice_no": result["invoice"].invoice_no,
            "status": result["send_status"],
            "error": result.get("error_message")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audit-logs")
async def get_audit_logs(limit: int = 100):
    """Fetch recent audit logs."""
    return audit_logger.get_all_logs(limit=limit)

@app.get("/api/stats")
async def get_stats():
    """Fetch dashboard statistics."""
    return audit_logger.get_stats()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
