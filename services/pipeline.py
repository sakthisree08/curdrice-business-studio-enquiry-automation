"""
The automation workflow - one function the UI, the API and batch upload all share.

  validate -> AI analysis -> grounding check -> lead score -> next best action
           -> response draft (+ safety guardrail) -> human-review rules -> save
"""
import logging

import config
from database import database as db
from models.schemas import ProcessedEnquiry
from services.ai_service import analyse_enquiry
from services.next_action_service import build_next_action
from services.response_service import generate_response
from services.review_service import assess_human_review
from services.scoring_service import calculate_lead_score
from utils.validators import ground_analysis, validate_enquiry_text

logger = logging.getLogger(__name__)


def process_enquiry(text: str, source: str = "form", save: bool = True) -> ProcessedEnquiry:
    """
    Raises EnquiryValidationError for bad input. AI problems never raise:
    they fall back to the rule-based engine and are reported in `warnings`.
    A database failure is reported in `warnings` too, so the analysis is not lost.
    """
    enquiry_text = validate_enquiry_text(text)

    analysis, mode, warnings = analyse_enquiry(enquiry_text)
    analysis, grounding_notes = ground_analysis(analysis, enquiry_text)
    warnings += [f"Grounding check: {note}" for note in grounding_notes]

    lead_score = calculate_lead_score(analysis, enquiry_text)
    next_action = build_next_action(analysis, lead_score)

    use_ai = mode == "gemini" and not config.is_mock_mode()
    response, response_warnings, violations = generate_response(enquiry_text, analysis, next_action, use_ai)
    warnings += response_warnings

    review = assess_human_review(analysis, mode, violations)

    result = ProcessedEnquiry(
        enquiry_text=enquiry_text, source=source, analysis=analysis, lead_score=lead_score,
        next_action=next_action, response=response, human_review=review,
        processing_mode=mode, warnings=warnings, guardrail_violations=violations,
    )
    if save:
        try:
            result.id = db.save_enquiry(result)
        except db.DatabaseError as error:
            logger.error("Could not save enquiry: %s", error)
            result.warnings.append(f"The result could not be saved to the database: {error}")
    return result
