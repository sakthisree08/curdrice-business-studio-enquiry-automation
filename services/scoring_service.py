"""
Transparent, deterministic lead scoring (0-100).

The LLM never picks the score. It only extracts facts; this module turns those
facts into points using six explainable business factors:

    Factor                     Max   What earns points
    -------------------------  ---   ------------------------------------------------
    Business intent             25   wants to buy a service (25), partnership (12), info (8)
    Requirement clarity         20   requirement stated (8) + concrete deliverable (6) + detail (6)
    Business information        15   company name (6) + industry (5) + contact details (4)
    Budget                      15   any budget stated (15)
    Timeline / urgency          10   urgent (10) or any timeline (6)
    Project value               15   category value (0-12) + scale/complexity signal (3)
                               ---
                               100

Priority: High >= 70, Medium >= 40, otherwise Low (thresholds in config.py).
"""
import re

import config
from models.schemas import EnquiryAnalysis, LeadScore, ScoreFactor

_INTENT_POINTS = {"buy_service": 25, "partnership": 12, "information": 8,
                  "other": 4, "job_application": 0, "complaint": 0}
_DELIVERABLE = re.compile(r"\b(system|website|app|application|assistant|chatbot|bot|erp|crm|dashboard|"
                          r"automat\w*|platform|portal|software|integration|store)\b", re.I)
_SCALE = re.compile(
    r"\b\d[\d,]*\+?\s*(?:customer\s+)?(?:customers?|enquiries|inquiries|orders|users|employees|stores|"
    r"branches|locations|messages|calls|transactions)\b|\b(erp|enterprise|end-to-end|multiple|company-wide|"
    r"internal company data|integrat\w+)\b", re.I)


def _intent_factor(a: EnquiryAnalysis) -> ScoreFactor:
    points = _INTENT_POINTS.get(a.intent, 0)
    reasons = {
        "buy_service": "clear intent to buy a service",
        "partnership": "partnership interest (not a direct sale)",
        "information": "information request only, no concrete buying intent yet",
        "job_application": "job/internship request - not a sales lead",
        "complaint": "complaint/support issue - not a sales lead",
        "other": "intent unclear",
    }
    return ScoreFactor(name="Business intent", points=points, max_points=25, reason=reasons[a.intent])


def _clarity_factor(a: EnquiryAnalysis) -> ScoreFactor:
    if not a.requirement:
        return ScoreFactor(name="Requirement clarity", points=0, max_points=20, reason="no specific requirement stated")
    points, notes = 8, ["requirement stated"]
    if _DELIVERABLE.search(a.requirement):
        points += 6
        notes.append("concrete deliverable named")
    if len(a.requirement.split()) >= 5:
        points += 6
        notes.append("described in some detail")
    return ScoreFactor(name="Requirement clarity", points=points, max_points=20, reason=", ".join(notes))


def _business_info_factor(a: EnquiryAnalysis) -> ScoreFactor:
    points, notes = 0, []
    if a.company_name:
        points += 6
        notes.append(f"company: {a.company_name}")
    if a.industry:
        points += 5
        notes.append(f"industry: {a.industry}")
    if a.email or a.customer_name:
        points += 4
        notes.append("contact details given")
    return ScoreFactor(name="Business information", points=points, max_points=15,
                       reason=", ".join(notes) or "no company, industry or contact details")


def _budget_factor(a: EnquiryAnalysis) -> ScoreFactor:
    if a.budget:
        return ScoreFactor(name="Budget", points=15, max_points=15, reason=f"budget specified ({a.budget})")
    return ScoreFactor(name="Budget", points=0, max_points=15, reason="no budget mentioned")


def _timeline_factor(a: EnquiryAnalysis) -> ScoreFactor:
    if a.is_urgent:
        return ScoreFactor(name="Timeline / urgency", points=10, max_points=10,
                           reason=f"wants to start soon ({a.timeline or 'urgent'})")
    if a.timeline:
        return ScoreFactor(name="Timeline / urgency", points=6, max_points=10, reason=f"timeline given ({a.timeline})")
    return ScoreFactor(name="Timeline / urgency", points=0, max_points=10, reason="no timeline mentioned")


def _value_factor(a: EnquiryAnalysis, enquiry_text: str) -> ScoreFactor:
    profile = config.CATEGORY_PROFILES.get(a.service_category, config.CATEGORY_PROFILES["Other"])
    points = profile["value_points"]
    reason = f"{a.service_category} ({points}/12 category value)"
    scale = _SCALE.search(enquiry_text) if profile["is_sales"] else None
    if scale:
        points += 3
        reason += f", scale/complexity signal: '{scale.group().strip()}'"
    return ScoreFactor(name="Project value", points=min(points, 15), max_points=15, reason=reason)


def priority_for(score: int) -> str:
    if score >= config.HIGH_PRIORITY_MIN_SCORE:
        return "High"
    if score >= config.MEDIUM_PRIORITY_MIN_SCORE:
        return "Medium"
    return "Low"


def _explain(priority: str, score: int, factors: list[ScoreFactor], a: EnquiryAnalysis) -> str:
    strengths = {
        "Business intent": "the customer shows clear intent to buy a service",
        "Requirement clarity": "the business requirement is clearly defined",
        "Business information": "business details were provided",
        "Budget": f"a budget has been specified ({a.budget})",
        "Timeline / urgency": "the customer wants to start soon",
        "Project value": f"it is a high-value {a.service_category} opportunity",
    }
    gaps = {
        "Requirement clarity": "the requirement is not yet clear",
        "Business information": "no company/business details",
        "Budget": "no budget mentioned",
        "Timeline / urgency": "no timeline mentioned",
    }
    positives = [strengths[f.name] for f in factors if f.points >= 0.6 * f.max_points]
    negatives = [gaps[f.name] for f in factors if f.points == 0 and f.name in gaps]

    if a.intent in ("complaint", "job_application"):
        text = (f"{priority} priority ({score}/100) because this is not a sales opportunity "
                f"({a.service_category}). It is routed by the Next Best Action instead of by score")
    elif a.intent == "partnership":
        text = (f"{priority} priority ({score}/100) because a partnership request is not a direct sales lead; "
                "it is flagged for a management decision instead")
    elif positives:
        text = f"{priority} priority ({score}/100) because " + _join(positives)
    else:
        text = f"{priority} priority ({score}/100) because the enquiry has little detail about a concrete business need"
    if negatives and a.intent not in ("complaint", "job_application", "partnership"):
        text += ". Score held back by: " + _join(negatives)
    return text + "."


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def calculate_lead_score(analysis: EnquiryAnalysis, enquiry_text: str) -> LeadScore:
    factors = [
        _intent_factor(analysis),
        _clarity_factor(analysis),
        _business_info_factor(analysis),
        _budget_factor(analysis),
        _timeline_factor(analysis),
        _value_factor(analysis, enquiry_text),
    ]
    score = max(0, min(100, sum(f.points for f in factors)))
    priority = priority_for(score)
    return LeadScore(score=score, priority=priority, factors=factors,
                     explanation=_explain(priority, score, factors, analysis))
