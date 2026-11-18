"""
Human-review rules.

EVERY draft needs human approval before sending (routine approval).
This module decides which enquiries ALSO need special human attention,
and records the exact reasons so the reviewer knows why.
"""
import config
from models.schemas import EnquiryAnalysis, HumanReview


def assess_human_review(analysis: EnquiryAnalysis, processing_mode: str,
                        guardrail_violations: list[str]) -> HumanReview:
    a = analysis
    reasons: list[str] = []

    if a.service_category == "Complaint / Support":
        reasons.append("Complaint or support issue - needs a personal response from the team.")
    if a.sentiment in ("angry", "negative"):
        reasons.append(f"Negative customer sentiment detected ({a.sentiment}).")
    if a.is_sensitive:
        reasons.append("Sensitive content (legal, financial, personal data or similar).")
    if a.service_category == "Partnership":
        reasons.append("Partnership request - requires a business decision by management.")
    if a.service_category == "Other":
        reasons.append("Unusual request that does not fit a standard service category.")
    if a.intent == "buy_service" and not a.requirement:
        reasons.append("Requirement is unclear - a person should clarify before replying.")
    if a.confidence < config.REVIEW_CONFIDENCE_THRESHOLD:
        reasons.append(f"Low AI confidence ({a.confidence:.2f} < {config.REVIEW_CONFIDENCE_THRESHOLD}).")
    if processing_mode == "fallback":
        reasons.append("The AI model failed; this enquiry was analysed by the rule-based fallback - verify the results.")
    if guardrail_violations:
        reasons.append("The AI draft broke a business rule and was replaced with a safe template - check the reply.")

    return HumanReview(required=bool(reasons), reasons=reasons)
