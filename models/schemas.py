"""
Pydantic models = the contract between every part of the system.

The LLM's raw output is NEVER used directly. It must pass EnquiryAnalysis /
ResponseDraft validation first; anything that doesn't fit is rejected.
"""
import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

import config

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
NOT_MENTIONED = {"", "not mentioned", "none", "null", "n/a", "na", "unknown",
                 "not specified", "not provided", "-", "nil"}

Sentiment = Literal["positive", "neutral", "negative", "angry"]
Intent = Literal["buy_service", "information", "job_application", "partnership", "complaint", "other"]
Priority = Literal["High", "Medium", "Low"]
Urgency = Literal["Critical", "High", "Medium", "Low"]
ProcessingMode = Literal["gemini", "mock", "fallback"]
ReviewStatus = Literal["Draft", "Approved", "Rejected"]


def _to_optional_text(value) -> Optional[str]:
    """Normalise 'Not mentioned', '', 'null' etc. to None so we never store fake values."""
    if value is None:
        return None
    text = str(value).strip()
    return None if text.lower() in NOT_MENTIONED else text


# --------------------------------------------------------------------------
# 1. What the AI extracts from an enquiry
# --------------------------------------------------------------------------
class EnquiryAnalysis(BaseModel):
    customer_name: Optional[str] = None
    company_name: Optional[str] = None
    email: Optional[str] = None
    industry: Optional[str] = None
    requirement: Optional[str] = None
    service_category: str = "Other"
    budget: Optional[str] = None
    timeline: Optional[str] = None
    intent: Intent = "other"
    sentiment: Sentiment = "neutral"
    is_urgent: bool = False
    asks_for_pricing: bool = False
    is_sensitive: bool = False
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    summary: str = ""

    @field_validator("customer_name", "company_name", "email", "industry",
                     "requirement", "budget", "timeline", mode="before")
    @classmethod
    def _clean_optional(cls, value):
        return _to_optional_text(value)

    @field_validator("email")
    @classmethod
    def _valid_email_or_none(cls, value):
        return value if value and EMAIL_PATTERN.match(value) else None

    @field_validator("service_category", mode="before")
    @classmethod
    def _known_category(cls, value):
        """Map the LLM's label onto our configured categories; unknown labels become 'Other'."""
        text = str(value or "").strip().lower()
        for category in config.CATEGORIES:
            if text == category.lower():
                return category
        for category in config.CATEGORIES:  # tolerate "Internship" vs "Internship / Job Application"
            if text and (text in category.lower() or category.lower().split(" /")[0] in text):
                return category
        return "Other"

    @field_validator("intent", mode="before")
    @classmethod
    def _known_intent(cls, value):
        text = str(value or "").strip().lower().replace(" ", "_")
        return text if text in Intent.__args__ else "other"

    @field_validator("sentiment", mode="before")
    @classmethod
    def _known_sentiment(cls, value):
        text = str(value or "").strip().lower()
        return text if text in Sentiment.__args__ else "neutral"

    @field_validator("confidence", mode="before")
    @classmethod
    def _confidence_0_to_1(cls, value):
        number = float(value)
        if 1 < number <= 100:  # model answered as a percentage
            number /= 100
        return max(0.0, min(1.0, number))

    @field_validator("summary", mode="before")
    @classmethod
    def _summary_text(cls, value):
        return str(value or "").strip()


# --------------------------------------------------------------------------
# 2. Business logic outputs (computed by Python, not the LLM)
# --------------------------------------------------------------------------
class ScoreFactor(BaseModel):
    name: str
    points: int
    max_points: int
    reason: str


class LeadScore(BaseModel):
    score: int = Field(ge=0, le=100)
    priority: Priority
    factors: list[ScoreFactor]
    explanation: str


class NextBestAction(BaseModel):
    action: str
    urgency: Urgency
    respond_within: str          # internal SLA target - never shown to the customer
    assigned_team: str
    why_it_matters: str
    missing_information: list[str]
    questions_to_ask: list[str]


class HumanReview(BaseModel):
    required: bool
    reasons: list[str]


class ResponseDraft(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=20, max_length=4000)

    @field_validator("subject", "body", mode="before")
    @classmethod
    def _strip(cls, value):
        return str(value or "").strip()


# --------------------------------------------------------------------------
# 3. The complete processed enquiry (what we show and store)
# --------------------------------------------------------------------------
class ProcessedEnquiry(BaseModel):
    id: Optional[int] = None
    enquiry_text: str
    source: str = "form"
    analysis: EnquiryAnalysis
    lead_score: LeadScore
    next_action: NextBestAction
    response: ResponseDraft
    human_review: HumanReview
    processing_mode: ProcessingMode
    warnings: list[str] = []
    guardrail_violations: list[str] = []
    status: ReviewStatus = "Draft"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


# --------------------------------------------------------------------------
# 4. API request bodies
# --------------------------------------------------------------------------
class EnquiryRequest(BaseModel):
    text: str = Field(description="The customer's enquiry in natural language")
    source: str = Field(default="api", max_length=50, description="e.g. website, email, whatsapp")


class StatusUpdateRequest(BaseModel):
    status: ReviewStatus
    edited_response: Optional[str] = Field(default=None, max_length=4000)
    reviewer_notes: Optional[str] = Field(default=None, max_length=1000)
