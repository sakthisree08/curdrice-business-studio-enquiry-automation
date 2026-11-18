"""
Automated tests (standard-library unittest, no extra dependencies).

Run from the project folder:   python -m unittest discover -s tests -v

They run in mock mode against a temporary database, so no API key or network is needed.
The LLM path is tested with a fake OpenAI client that returns valid, malformed and rule-breaking output.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ["FORCE_MOCK_MODE"] = "true"
os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test_enquiries.db")

import config  # noqa: E402
from database import database as db  # noqa: E402
from models.schemas import EnquiryAnalysis, ResponseDraft  # noqa: E402
from services import ai_service  # noqa: E402
from services.pipeline import process_enquiry  # noqa: E402
from utils.validators import (EnquiryValidationError, check_response_safety,  # noqa: E402
                              ground_analysis, validate_enquiry_text)

SAMPLES = {s["id"]: s["enquiry"] for s in json.loads(config.SAMPLE_DATA_PATH.read_text(encoding="utf-8"))}


class FakeClient:
    """Mimics openai.OpenAI().chat.completions.create, returning queued replies."""

    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **_kwargs):
        self.calls += 1
        content = self.replies.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class InputValidationTests(unittest.TestCase):
    def test_empty_and_junk_enquiries_are_rejected(self):
        for bad in ["", "   ", "hi", "12345 678 !!!", "x" * (config.MAX_ENQUIRY_CHARS + 1)]:
            with self.assertRaises(EnquiryValidationError):
                validate_enquiry_text(bad)

    def test_valid_enquiry_is_trimmed(self):
        self.assertEqual(validate_enquiry_text("  What services do you offer?  "), "What services do you offer?")


class PipelineTests(unittest.TestCase):
    def test_all_assessment_samples_process(self):
        for sample_id, text in SAMPLES.items():
            result = process_enquiry(text, save=False)
            self.assertTrue(0 <= result.lead_score.score <= 100, sample_id)
            self.assertEqual(result.status, "Draft", sample_id)

    def test_expected_classifications_and_priorities(self):
        expectations = {
            "001": ("AI Automation", None), "002": ("Website Development", "High"),
            "003": ("General Enquiry", "Low"), "005": ("Internship / Job Application", "Low"),
            "007": ("General Enquiry", "Low"), "008": ("AI Automation", "High"),
            "011": ("Partnership", None), "012": ("Complaint / Support", None),
        }
        for sample_id, (category, priority) in expectations.items():
            result = process_enquiry(SAMPLES[sample_id], save=False)
            self.assertEqual(result.analysis.service_category, category, sample_id)
            if priority:
                self.assertEqual(result.lead_score.priority, priority, sample_id)

    def test_complaint_and_partnership_need_human_review(self):
        for sample_id in ("011", "012"):
            self.assertTrue(process_enquiry(SAMPLES[sample_id], save=False).human_review.required, sample_id)
        self.assertFalse(process_enquiry(SAMPLES["002"], save=False).human_review.required)

    def test_complaint_gets_critical_next_action(self):
        self.assertEqual(process_enquiry(SAMPLES["012"], save=False).next_action.urgency, "Critical")

    def test_pricing_request_does_not_invent_prices(self):
        result = process_enquiry(SAMPLES["007"], save=False)
        self.assertEqual(check_response_safety(result.response, SAMPLES["007"]), [])
        self.assertIn("pricing", result.response.body.lower())

    def test_scoring_is_deterministic(self):
        scores = {process_enquiry(SAMPLES["002"], save=False).lead_score.score for _ in range(3)}
        self.assertEqual(len(scores), 1)

    def test_missing_information_feeds_the_reply(self):
        result = process_enquiry(SAMPLES["001"], save=False)
        self.assertIn("Approximate budget range", result.next_action.missing_information)
        for question in result.next_action.questions_to_ask:
            self.assertIn(question, result.response.body)


class AntiHallucinationTests(unittest.TestCase):
    def test_grounding_removes_values_not_in_enquiry(self):
        text = "We are a jewellery business looking for a WhatsApp bot."
        invented = EnquiryAnalysis(company_name="Tanishq", email="info@tanishq.com", budget="₹5 lakh",
                                   timeline="next month", service_category="AI Automation")
        grounded, notes = ground_analysis(invented, text)
        self.assertIsNone(grounded.company_name)
        self.assertIsNone(grounded.email)
        self.assertIsNone(grounded.budget)
        self.assertIsNone(grounded.timeline)
        self.assertEqual(len(notes), 4)

    def test_grounding_keeps_real_values(self):
        text = "Need a website for our manufacturing company. Budget is ₹2 lakh. Can we discuss this week?"
        grounded, notes = ground_analysis(EnquiryAnalysis(budget="₹2 lakh", timeline="this week"), text)
        self.assertEqual((grounded.budget, grounded.timeline, notes), ("₹2 lakh", "this week", []))

    def test_not_mentioned_becomes_null(self):
        analysis = EnquiryAnalysis.model_validate({"customer_name": "Not mentioned", "budget": "N/A",
                                                   "service_category": "internship", "confidence": 85})
        self.assertIsNone(analysis.customer_name)
        self.assertIsNone(analysis.budget)
        self.assertEqual(analysis.service_category, "Internship / Job Application")
        self.assertEqual(analysis.confidence, 0.85)

    def test_safety_check_flags_invented_price_and_deadline(self):
        draft = ResponseDraft(subject="Quote", body="Our website package costs ₹50,000 and is guaranteed "
                                                    "to be delivered within 2 weeks.")
        self.assertGreaterEqual(len(check_response_safety(draft, "Need a website")), 3)

    def test_safety_check_allows_customers_own_budget(self):
        draft = ResponseDraft(subject="Re: website", body="Thank you for sharing your budget of ₹2 lakh. "
                                                          "Could you share the pages you need?")
        self.assertEqual(check_response_safety(draft, "Budget is ₹2 lakh"), [])


class LLMReliabilityTests(unittest.TestCase):
    VALID = json.dumps({"customer_name": None, "company_name": None, "email": None, "industry": "jewellery",
                        "requirement": "AI WhatsApp customer support system", "service_category": "AI Automation",
                        "budget": "Not mentioned", "timeline": None, "intent": "buy_service",
                        "sentiment": "neutral", "is_urgent": False, "asks_for_pricing": False,
                        "is_sensitive": False, "confidence": 0.9, "summary": "Wants a WhatsApp AI bot."})

    def test_valid_json_inside_code_fence_is_parsed(self):
        client = FakeClient([f"```json\n{self.VALID}\n```"])
        analysis = ai_service.call_llm_json("sys", "user", EnquiryAnalysis, client=client)
        self.assertEqual(analysis.service_category, "AI Automation")
        self.assertIsNone(analysis.budget)

    def test_malformed_json_triggers_one_repair_retry(self):
        client = FakeClient(["this is not json", self.VALID])
        analysis = ai_service.call_llm_json("sys", "user", EnquiryAnalysis, client=client)
        self.assertEqual(client.calls, 2)
        self.assertEqual(analysis.intent, "buy_service")

    def test_repeated_invalid_output_raises_ai_error(self):
        client = FakeClient(["nope", '{"confidence": "high"}'])
        with self.assertRaises(ai_service.AIServiceError):
            ai_service.call_llm_json("sys", "user", EnquiryAnalysis, client=client)

    def test_ai_failure_falls_back_to_rule_engine(self):
        with patch.object(config, "is_mock_mode", return_value=False), \
             patch.object(ai_service, "_get_client", return_value=FakeClient(["bad", "still bad"])):
            result = process_enquiry(SAMPLES["012"], save=False)
        self.assertEqual(result.processing_mode, "fallback")
        self.assertTrue(result.human_review.required)
        self.assertTrue(any("fallback" in w for w in result.warnings))

    def test_rule_breaking_ai_draft_is_replaced(self):
        bad_draft = json.dumps({"subject": "Pricing", "body": "Hello, our basic package costs ₹25,000 and we "
                                                              "guarantee delivery within 10 days. Regards"})
        with patch.object(config, "is_mock_mode", return_value=False), \
             patch.object(ai_service, "_get_client", return_value=FakeClient([self.VALID])), \
             patch("services.response_service.call_llm_json",
                   side_effect=lambda *a, **k: ResponseDraft.model_validate_json(bad_draft)):
            result = process_enquiry(SAMPLES["001"], save=False)
        self.assertTrue(result.guardrail_violations)
        self.assertNotIn("25,000", result.response.body)
        self.assertTrue(result.human_review.required)


class DatabaseTests(unittest.TestCase):
    def test_save_load_and_approve(self):
        result = process_enquiry(SAMPLES["002"], save=True)
        self.assertIsNotNone(result.id)
        loaded = db.get_enquiry(result.id)
        self.assertEqual(loaded.lead_score.score, result.lead_score.score)
        self.assertTrue(db.update_status(result.id, "Approved", edited_response="Edited reply text here.",
                                         reviewer_notes="ok"))
        loaded = db.get_enquiry(result.id)
        self.assertEqual((loaded.status, loaded.response.body), ("Approved", "Edited reply text here."))
        self.assertGreaterEqual(db.get_stats()["total"], 1)

    def test_unknown_id(self):
        self.assertIsNone(db.get_enquiry(999999))
        self.assertFalse(db.update_status(999999, "Approved"))


if __name__ == "__main__":
    unittest.main()
