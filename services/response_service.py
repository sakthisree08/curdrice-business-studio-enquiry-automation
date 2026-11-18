"""
Response draft generation.

1. The LLM writes a personalised draft under strict business rules (live mode),
   or a category template is used (mock mode / AI failure).
2. EVERY draft passes check_response_safety(). If the AI broke a rule
   (invented price, guarantee, deadline...), the draft is replaced by the safe
   template and the violation is recorded for the human reviewer.
3. Drafts are never sent. They are stored with status "Draft".
"""
import json
import logging
import re

import config
from models.schemas import EnquiryAnalysis, NextBestAction, ResponseDraft
from services.ai_service import AIServiceError, call_llm_json
from utils.validators import check_response_safety

logger = logging.getLogger(__name__)
BUSINESS = config.BUSINESS_PROFILE
SIGN_OFF = f"Warm regards,\nTeam {BUSINESS['name']}"

RESPONSE_SYSTEM_PROMPT = f"""You write first-reply email DRAFTS for {BUSINESS['name']}.
About us: {BUSINESS['description']} Focus areas: {BUSINESS['tagline']}.
Services we offer (ONLY these): {", ".join(BUSINESS['services'])}.

BUSINESS RULES - follow strictly:
{chr(10).join("- " + rule for rule in config.BUSINESS_RULES)}
- Do NOT mention any price, amount, discount or cost estimate (you may repeat the customer's own budget).
- Do NOT promise dates, durations or response times (no "within 24 hours", no "by Friday").
- If pricing is requested, explain that pricing depends on the scope and can be discussed once the requirement is understood.
- For complaints: apologise sincerely, say the message has been flagged for priority attention by the team; promise nothing else.
- Use the customer's name only if it is given; otherwise greet with "Hello,".
- Ask the provided follow-up questions naturally (as a short bullet list).
- Never mention lead scores, priorities or internal processes.
- 90-180 words, warm and professional. End with: "{SIGN_OFF.replace(chr(10), ' / ')}" (on two lines).

Return ONLY JSON: {{"subject": "...", "body": "..."}}"""


def _greeting(a: EnquiryAnalysis) -> str:
    return f"Dear {a.customer_name}," if a.customer_name else "Hello,"


def _bullets(questions: list[str]) -> str:
    return "\n".join(f"- {q}" for q in questions)


def template_response(a: EnquiryAnalysis, nba: NextBestAction) -> ResponseDraft:
    """Safe, rule-compliant reply used in mock mode and whenever the AI draft fails validation."""
    questions = _bullets(nba.questions_to_ask)
    services = ", ".join(BUSINESS["services"])
    category = a.service_category

    if category == "Complaint / Support":
        subject = "We're sorry - your concern has been escalated"
        body = ("We are sorry to hear that your experience has not met your expectations, and thank you for "
                "letting us know. Your message has been flagged for priority attention by our team, and a "
                "senior team member will reach out to you personally.\n\nTo help us look into this quickly, "
                f"could you share:\n{questions}")
    elif category == "Internship / Job Application":
        subject = "Thank you for your interest in Curd Rice Business Studio"
        body = ("Thank you for your interest in working with us. We have shared your message with our team. "
                "We cannot confirm any openings or opportunities at this stage, but we will keep your details "
                f"on record.\n\nTo help us consider your request:\n{questions}")
    elif category == "Partnership":
        subject = "Re: Partnership opportunity"
        body = ("Thank you for your interest in partnering with Curd Rice Business Studio. Partnership requests "
                "are reviewed by our leadership team, so we would appreciate a little more information first.\n\n"
                f"{questions}")
    elif category in ("General Enquiry", "Other"):
        subject = "Re: Your enquiry to Curd Rice Business Studio"
        pricing = ("Our pricing depends on the scope of each project, so we do not have fixed packages. We would "
                   "be happy to discuss pricing once we understand your requirement.\n\n") if a.asks_for_pricing else ""
        body = (f"Thank you for reaching out. {BUSINESS['description']} Our services include {services}.\n\n"
                f"{pricing}To point you to the right solution, could you tell us:\n{questions}")
    else:
        # requirement is in the customer's voice ("our company") -> address them ("your company")
        topic = re.sub(r"\bour\b", "your", a.requirement or category.lower(), flags=re.I)
        topic = re.sub(r"\bus\b", "you", topic, flags=re.I)
        industry = f" for your {a.industry} business" if a.industry and a.industry.lower() not in topic.lower() else ""
        budget = f" Thank you also for sharing your budget of {a.budget}." if a.budget else ""
        pricing = (" Pricing depends on the final scope, which we can discuss once we understand the details."
                   if a.asks_for_pricing else "")
        subject = f"Re: Your {category} enquiry"
        body = (f"Thank you for contacting Curd Rice Business Studio about {topic}{industry}. "
                f"{category} is one of the areas we work in, and we would be glad to understand your needs "
                f"in more detail.{budget}{pricing}\n\nTo help us prepare, could you share:\n{questions}\n\n"
                "Once we have these details, our team will get in touch to discuss the next steps.")
    return ResponseDraft(subject=subject, body=f"{_greeting(a)}\n\n{body}\n\n{SIGN_OFF}")


def generate_response(enquiry_text: str, analysis: EnquiryAnalysis, nba: NextBestAction,
                      use_ai: bool) -> tuple[ResponseDraft, list[str], list[str]]:
    """Returns (draft, warnings, guardrail_violations)."""
    warnings: list[str] = []
    if not use_ai:
        return template_response(analysis, nba), warnings, []

    context = {
        "customer_enquiry": enquiry_text,
        "analysis": analysis.model_dump(include={"customer_name", "company_name", "industry", "requirement",
                                                 "service_category", "budget", "timeline", "sentiment",
                                                 "asks_for_pricing"}),
        "follow_up_questions": nba.questions_to_ask,
    }
    try:
        draft = call_llm_json(RESPONSE_SYSTEM_PROMPT, json.dumps(context, ensure_ascii=False), ResponseDraft,
                              temperature=0.4)
    except AIServiceError as error:
        logger.error("AI response generation failed: %s", error)
        warnings.append(f"AI response generation failed ({error}). A safe template reply was used.")
        return template_response(analysis, nba), warnings, []

    violations = check_response_safety(draft, enquiry_text)
    if violations:
        logger.warning("AI draft violated business rules: %s", violations)
        return template_response(analysis, nba), warnings, violations
    return draft, warnings, []
