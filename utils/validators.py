"""
Validation and guardrails.

1. validate_enquiry_text   -> rejects empty / junk / oversized input before any AI call
2. ground_analysis         -> anti-hallucination: drops extracted values that are NOT in the enquiry
3. check_response_safety   -> scans the draft reply for invented prices, guarantees and commitments
"""
import re

import config
from models.schemas import EnquiryAnalysis, ResponseDraft


class EnquiryValidationError(ValueError):
    """Raised when the enquiry text is not usable."""


# --------------------------------------------------------------------------
# 1. Input validation
# --------------------------------------------------------------------------
def validate_enquiry_text(text: str | None) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        raise EnquiryValidationError("The enquiry is empty. Please enter the customer's message.")
    if len(cleaned) < config.MIN_ENQUIRY_CHARS:
        raise EnquiryValidationError(
            f"The enquiry is too short (minimum {config.MIN_ENQUIRY_CHARS} characters).")
    if len(cleaned) > config.MAX_ENQUIRY_CHARS:
        raise EnquiryValidationError(
            f"The enquiry is too long (maximum {config.MAX_ENQUIRY_CHARS} characters).")
    if len(re.findall(r"[A-Za-zऀ-෿]", cleaned)) < 3:
        raise EnquiryValidationError("The enquiry does not contain readable text.")
    return cleaned


# --------------------------------------------------------------------------
# 2. Grounding check (anti-hallucination for extracted fields)
# --------------------------------------------------------------------------
_STOPWORDS = {"the", "and", "for", "our", "with", "your", "from", "this", "that", "not"}


def _numbers_in(text: str) -> set[str]:
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def ground_analysis(analysis: EnquiryAnalysis, enquiry_text: str) -> tuple[EnquiryAnalysis, list[str]]:
    """
    Every extracted value must be traceable to the original enquiry.
    Values the customer never wrote are removed (set to None) and reported.
    """
    source = enquiry_text.lower()
    updates: dict[str, None] = {}
    notes: list[str] = []

    def drop(field: str, value: str, why: str) -> None:
        updates[field] = None
        notes.append(f"Removed {field.replace('_', ' ')} '{value}' - {why}.")

    for field in ("email", "customer_name", "company_name"):
        value = getattr(analysis, field)
        if value and value.lower() not in source:
            drop(field, value, "it does not appear in the enquiry")

    if analysis.budget:
        budget_numbers = _numbers_in(analysis.budget)
        if budget_numbers and not budget_numbers <= _numbers_in(enquiry_text):
            drop("budget", analysis.budget, "the amount is not in the enquiry")
        elif not budget_numbers and "budget" not in source:
            drop("budget", analysis.budget, "no budget is mentioned in the enquiry")

    if analysis.timeline:
        words = [w for w in re.findall(r"[a-z0-9]+", analysis.timeline.lower())
                 if len(w) >= 3 and w not in _STOPWORDS]
        if words and not any(w[:5] in source for w in words):
            drop("timeline", analysis.timeline, "no matching timeline wording in the enquiry")

    return (analysis.model_copy(update=updates) if updates else analysis), notes


# --------------------------------------------------------------------------
# 3. Response guardrail (business rules check on the generated draft)
# --------------------------------------------------------------------------
_MONEY = re.compile(
    r"(?:₹|rs\.?|inr|\$|usd|eur|€|£)\s?\d[\d,\.]*(?:\s?(?:lakhs?|lacs?|crores?|k|thousand))?"
    r"|\d[\d,\.]*\s?(?:lakhs?|lacs?|crores?|thousand rupees|rupees|dollars)",
    re.IGNORECASE,
)
_COMMITMENT_PATTERNS = {
    r"\bguarantee[ds]?\b": "contains a guarantee",
    r"\bwe promise\b|\bpromised?\s+(?:to|that)\b": "contains a promise",
    r"\b(?:within|in)\s+\d+\s*(?:business\s+|working\s+)?(?:hours?|days?|weeks?|months?)\b":
        "states a specific timeframe",
    r"\b(?:deliver|complete|launch|finish|ready)\w*\b[^.]{0,40}\b(?:by|before)\s+(?:monday|tuesday|wednesday|"
    r"thursday|friday|saturday|sunday|tomorrow|next|the end|\d)":
        "commits to a delivery date",
    r"\b(?:discount|free of cost|free trial|money[- ]back)\b": "offers a discount or free service",
    r"\bwe will (?:refund|compensate)\b": "commits to a refund/compensation",
    r"\b(?:fixed|starting|flat)\s+(?:price|fee|cost|rate)\b|\bcosts?\s+(?:only|just|around|approximately)\b":
        "quotes a price",
}


def check_response_safety(draft: ResponseDraft, enquiry_text: str) -> list[str]:
    """Return a list of business-rule violations found in the draft (empty list = safe)."""
    text = f"{draft.subject}\n{draft.body}"
    violations: list[str] = []

    enquiry_numbers = _numbers_in(enquiry_text)
    for match in _MONEY.finditer(text):
        # Repeating the customer's own budget back to them is fine; any other amount is invented.
        if not _numbers_in(match.group()) <= enquiry_numbers:
            violations.append(f"Mentions a price/amount not provided by the customer: '{match.group().strip()}'")

    for pattern, description in _COMMITMENT_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            violations.append(f"Draft {description}: '{match.group().strip()}'")
    return violations
