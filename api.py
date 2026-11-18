"""
REST API (FastAPI) - lets other systems push enquiries in automatically:
website contact forms, email parsers, WhatsApp webhooks, n8n / Make / Zapier flows.

Run:   uvicorn api:app --reload --port 8000
Docs:  http://127.0.0.1:8000/docs   (interactive Swagger UI)

It reuses exactly the same pipeline and database as the Streamlit app.
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

import config
from database import database as db
from models.schemas import EnquiryRequest, ProcessedEnquiry, StatusUpdateRequest
from services.pipeline import process_enquiry
from utils.validators import EnquiryValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Curd Rice Business Studio - Enquiry Automation API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {
    "status": "ok",
    "ai_mode": "mock" if config.is_mock_mode() else "gemini",
    "model": config.GEMINI_MODEL,
}


@app.post("/enquiries", response_model=ProcessedEnquiry, status_code=201)
def create_enquiry(request: EnquiryRequest) -> ProcessedEnquiry:
    """Process a new enquiry end-to-end and store it. The reply is returned as a DRAFT, never sent."""
    try:
        return process_enquiry(request.text, source=request.source)
    except EnquiryValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        logger.exception("Unexpected error in POST /enquiries")
        raise HTTPException(status_code=500, detail="Unexpected error while processing the enquiry.") from error


@app.get("/enquiries")
def list_enquiries(priority: Optional[str] = Query(None, pattern="^(High|Medium|Low)$"),
                   category: Optional[str] = None,
                   status: Optional[str] = Query(None, pattern="^(Draft|Approved|Rejected)$"),
                   review_only: bool = False, limit: int = Query(100, ge=1, le=500)) -> list[dict]:
    try:
        return db.list_enquiries(priority=priority, category=category, status=status,
                                 review_only=review_only, limit=limit)
    except db.DatabaseError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/enquiries/{enquiry_id}", response_model=ProcessedEnquiry)
def get_enquiry(enquiry_id: int) -> ProcessedEnquiry:
    result = db.get_enquiry(enquiry_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return result


@app.patch("/enquiries/{enquiry_id}/status")
def update_status(enquiry_id: int, update: StatusUpdateRequest) -> dict:
    """The human-approval step: Approve / Reject / back to Draft, optionally with an edited reply."""
    if not db.update_status(enquiry_id, update.status, update.edited_response, update.reviewer_notes):
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return {"id": enquiry_id, "status": update.status}


@app.get("/stats")
def stats() -> dict:
    return db.get_stats()
