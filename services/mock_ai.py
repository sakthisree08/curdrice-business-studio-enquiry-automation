"""
Rule-based "mock" analyser.

Used when (a) no OpenAI API key is configured (demo mode) or
(b) the real AI call fails (fallback mode). It returns the SAME
EnquiryAnalysis structure as the LLM, so the rest of the pipeline
does not care which engine produced it.
"""
import re

from models.schemas import EnquiryAnalysis

# Categories checked first: if any of their keywords appear, they win.
_OVERRIDE_CATEGORIES = {
    "Complaint / Support": [r"unhappy", r"complain", r"disappoint", r"dissatisf", r"not working",
                            r"poor service", r"terrible", r"worst", r"refund", r"problem with",
                            r"issue with", r"unacceptable", r"lawyer"],
    "Internship / Job Application": [r"internship", r"\bintern\b", r"\bjob\b", r"career", r"resume",
                                     r"\bcv\b", r"vacanc", r"fresher", r"\bstudent\b", r"college project"],
    "Partnership": [r"\bpartner", r"collaborat", r"joint venture", r"reseller", r"alliance"],
}
# Otherwise the category with the most keyword hits wins (ties -> order below).
_SERVICE_CATEGORIES = {
    "Operational Systems": [r"inventory", r"dispatch", r"\berp\b", r"operations?\b", r"logistic",
                            r"supply chain", r"warehouse", r"\bcrm\b", r"workflow", r"billing"],
    "AI Automation": [r"\bai\b", r"artificial intelligence", r"chatbot", r"\bbot\b", r"assistant",
                      r"whatsapp", r"\bgpt\b", r"\bllm\b", r"machine learning", r"automat"],
    "Business Intelligence": [r"dashboard", r"analytics", r"\breports?\b", r"reporting", r"insight",
                              r"\bkpi", r"power bi", r"tableau", r"\bbi\b"],
    "Website Development": [r"website", r"web site", r"landing page", r"web ?page", r"e-?commerce",
                            r"online store"],
    "Application Development": [r"\bapp\b", r"mobile app", r"android", r"\bios\b", r"software",
                                r"\bportal\b", r"application"],
    "Branding": [r"\bbrand", r"\blogo\b", r"brand identity", r"rebrand"],
    "Digital Marketing": [r"marketing", r"\bseo\b", r"social media", r"\bads\b", r"advertis",
                          r"campaign", r"instagram", r"lead generation"],
    "Business Consulting": [r"consult", r"strategy", r"advice", r"business plan", r"grow our business"],
    "General Enquiry": [r"what services", r"services do you", r"more information", r"tell me about",
                        r"pric", r"\bquote\b", r"\bcost"],
}
_INTENT_BY_CATEGORY = {
    "Complaint / Support": "complaint",
    "Internship / Job Application": "job_application",
    "Partnership": "partnership",
    "General Enquiry": "information",
    "Other": "other",
}
_INDUSTRIES = ["silver jewellery", "jewellery", "jewelry", "manufacturing", "retail", "restaurant",
               "healthcare", "hospital", "clinic", "education", "school", "real estate", "logistics",
               "textile", "e-commerce", "ecommerce", "finance", "fintech", "hotel", "pharma",
               "automobile", "construction", "agriculture"]
_URGENCY = re.compile(r"\b(urgent(?:ly)?|immediately|asap|as soon as possible|right away|this week|today|tomorrow)\b", re.I)
_TIMELINE = re.compile(
    r"\b(immediately|asap|as soon as possible|right away|this week|next week|this month|next month|today|"
    r"tomorrow|(?:within|in) \d+ (?:days?|weeks?|months?)|by (?:end of )?[A-Z][a-z]+|q[1-4](?: \d{4})?)\b", re.I)
_BUDGET = re.compile(
    r"(?:₹|rs\.?|inr|\$)\s?\d[\d,\.]*\s?(?:lakhs?|lacs?|crores?|k|thousand)?"
    r"|\d[\d,\.]*\s?(?:lakhs?|lacs?|crores?)(?:\s?rupees)?", re.I)
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_NAME = re.compile(r"\b(?:[Mm]y name is|I am|I'm|[Tt]his is)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)")
_COMPANY = re.compile(r"\b(?:from|at|of)\s+([A-Z][\w&]*(?:\s+[A-Z][\w&.]*){0,4})")
_REQUIREMENT = re.compile(
    r"\b(?:looking for|need|needs|want to|want|interested in|require|requires|planning to)\s+(.+?)(?:[.!?]|$)", re.I)
_SENSITIVE = re.compile(r"\b(legal|lawsuit|lawyer|police|court|fraud|harass\w*|data breach|confidential|medical)\b", re.I)
_ANGRY = re.compile(r"\b(angry|furious|worst|ridiculous|unacceptable|terrible|scam|pathetic)\b", re.I)
_NEGATIVE = re.compile(r"\b(unhappy|disappointed|dissatisfied|poor|bad|problem|issue|complaint|not working)\b", re.I)
_POSITIVE = re.compile(r"\b(interesting|great|love|excited|impressed|happy to|looks good)\b", re.I)


def _hits(patterns: list[str], text: str) -> int:
    return sum(1 for p in patterns if re.search(p, text, re.I))


def _classify(text: str) -> tuple[str, int]:
    for category, patterns in _OVERRIDE_CATEGORIES.items():
        hits = _hits(patterns, text)
        if hits:
            return category, hits
    best, best_hits = "Other", 0
    for category, patterns in _SERVICE_CATEGORIES.items():
        hits = _hits(patterns, text)
        if hits > best_hits:
            best, best_hits = category, hits
    return best, best_hits


def _first(pattern: re.Pattern, text: str, group: int = 0) -> str | None:
    match = pattern.search(text)
    return match.group(group).strip() if match else None


def mock_analyse(text: str) -> EnquiryAnalysis:
    category, hits = _classify(text)
    intent = _INTENT_BY_CATEGORY.get(category, "buy_service")

    sentiment = ("angry" if _ANGRY.search(text) else
                 "negative" if _NEGATIVE.search(text) else
                 "positive" if _POSITIVE.search(text) else "neutral")
    industry = next((i for i in _INDUSTRIES if i in text.lower()), None)
    requirement = _first(_REQUIREMENT, text, 1) if intent != "information" else None
    confidence = 0.8 if hits >= 2 else 0.65 if hits == 1 else 0.35

    return EnquiryAnalysis(
        customer_name=_first(_NAME, text, 1),
        company_name=_first(_COMPANY, text, 1),
        email=_first(_EMAIL, text),
        industry=industry,
        requirement=requirement,
        service_category=category,
        budget=_first(_BUDGET, text),
        timeline=_first(_TIMELINE, text),
        intent=intent,
        sentiment=sentiment,
        is_urgent=bool(_URGENCY.search(text)),
        asks_for_pricing=bool(re.search(r"pric|\bquote\b|\bcost", text, re.I)),
        is_sensitive=bool(_SENSITIVE.search(text)),
        confidence=confidence,
        summary=f"{category} enquiry" + (f" from the {industry} industry" if industry else "") + ".",
    )
