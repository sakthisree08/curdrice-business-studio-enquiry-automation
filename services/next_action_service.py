"""
INNOVATION: Next Best Action + Missing-Information detection.

A lead score says how good a lead is. It does not say what to do about it.
This module turns the analysis into a sales/ops playbook step:

  * what the team should do next, who owns it and how urgently (an internal target)
  * why the lead matters
  * which facts are still missing, plus the exact questions to ask

The questions also go into the drafted reply, so the first reply to the customer
collects the missing details and saves a round of back-and-forth emails.
Everything here is deterministic rules, so it is explainable and testable.
"""
import re

import config
from models.schemas import EnquiryAnalysis, LeadScore, NextBestAction

MAX_QUESTIONS = 4

_FIELD_QUESTIONS = {  # missing field -> (label shown to team, question asked to customer)
    "requirement": ("Clear description of the requirement", "Could you describe what you would like us to help with?"),
    "budget": ("Approximate budget range", "Do you have an approximate budget range in mind?"),
    "timeline": ("Expected timeline / start date", "When would you ideally like to get started?"),
    "company_name": ("Company name", "Could you share your company name?"),
    "contact": ("Contact name / phone number", "What is the best way and time to reach you for a short call?"),
}


def _as_label(question: str) -> str:
    """'Could you share your CV and your availability?' -> 'Your CV and your availability'"""
    label = re.sub(r"^(could you (share|tell us)( a little more about)?|do you (already )?have)\s+", "",
                   question.rstrip("?"), flags=re.I)
    return label[:1].upper() + label[1:]


def _missing_information(a: EnquiryAnalysis, profile: dict) -> tuple[list[str], list[str]]:
    labels: list[str] = []
    questions: list[str] = []

    if profile["is_sales"] or a.intent == "buy_service":
        missing_fields = [f for f in ("requirement", "budget", "timeline", "company_name")
                          if not getattr(a, f)]
        if not (a.customer_name or a.email):
            missing_fields.append("contact")
        for field in missing_fields:
            label, question = _FIELD_QUESTIONS[field]
            labels.append(label)
            questions.append(question)
        discovery = profile["discovery_questions"]
        if a.requirement and re.search(r"\d", a.requirement):  # volume already given, e.g. "500 enquiries/day"
            discovery = [q for q in discovery if "how many" not in q.lower()]
        # category-specific discovery questions go first in the reply: they are the most useful
        questions = discovery + questions
        labels += [_as_label(q) for q in discovery]
    else:
        questions = list(profile["discovery_questions"])
        labels = [_as_label(q) for q in questions]
        if a.asks_for_pricing and not a.requirement:
            labels.insert(0, "The customer's actual requirement (needed before pricing can be discussed)")
            questions.insert(0, _FIELD_QUESTIONS["requirement"][1])

    return labels, questions[:MAX_QUESTIONS]


def _plan(a: EnquiryAnalysis, score: LeadScore) -> tuple[str, str, str, str]:
    """Returns (action, urgency, respond_within, assigned_team)."""
    category = a.service_category
    if category == "Complaint / Support" or a.sentiment in ("angry", "negative"):
        return ("Escalate to the account manager and call the customer personally; "
                "do not send an automated reply without approval.", "Critical", "2 hours", "Customer Success")
    if category == "Partnership":
        return ("Forward to the founders/management to evaluate the partnership; "
                "reply asking for a short proposal.", "Medium", "3 business days", "Management")
    if category == "Internship / Job Application":
        return ("Forward to the hiring team and request the candidate's CV/portfolio.",
                "Low", "5 business days", "HR / Hiring")
    if score.priority == "High":
        return ("Schedule a discovery call to confirm scope; prepare relevant case examples.",
                "High", "24 hours", "Sales")
    if score.priority == "Medium":
        return ("Send a requirement-gathering reply with the questions below and offer a discovery call.",
                "Medium", "48 hours", "Sales")
    if a.asks_for_pricing:
        return ("Explain that pricing depends on scope and ask for the requirement before any quote.",
                "Medium", "48 hours", "Sales")
    return ("Send the service overview and invite the customer to share their requirement.",
            "Low", "3 business days", "Sales")


def _why_it_matters(a: EnquiryAnalysis, score: LeadScore) -> str:
    category = a.service_category
    if category == "Complaint / Support" or a.sentiment in ("angry", "negative"):
        return "An unhappy customer is a reputation and retention risk; a fast personal response can recover the relationship."
    if category == "Partnership":
        return "A partnership could open a new channel or capability, but it needs a strategic decision by management."
    if category == "Internship / Job Application":
        return "Not a sales lead, but a potential addition to the talent pipeline."
    strong = [f.reason for f in score.factors if f.points >= 0.6 * f.max_points]
    detail = "; ".join(strong) if strong else "early-stage interest with limited detail"
    return f"Lead score {score.score}/100 ({score.priority}). Signals: {detail}."


def build_next_action(analysis: EnquiryAnalysis, score: LeadScore) -> NextBestAction:
    profile = config.CATEGORY_PROFILES.get(analysis.service_category, config.CATEGORY_PROFILES["Other"])
    action, urgency, respond_within, team = _plan(analysis, score)
    missing, questions = _missing_information(analysis, profile)
    return NextBestAction(
        action=action, urgency=urgency, respond_within=respond_within, assigned_team=team,
        why_it_matters=_why_it_matters(analysis, score),
        missing_information=missing, questions_to_ask=questions,
    )
