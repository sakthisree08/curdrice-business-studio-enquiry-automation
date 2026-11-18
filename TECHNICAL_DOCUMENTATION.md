# Technical Documentation

AI-Powered Business Enquiry Automation System, Curd Rice Business Studio.

## 1. Architecture

A layered, single-process application with one shared workflow function.

```
Presentation    app.py (Streamlit) · api.py (FastAPI) · ui/components.py
Workflow        services/pipeline.py  → process_enquiry()
Domain logic    scoring_service · next_action_service · review_service · response_service
AI layer        ai_service (OpenAI + validation + retry) · mock_ai (rule engine)
Validation      utils/validators.py · models/schemas.py (Pydantic)
Persistence     database/database.py (sqlite3)
Configuration   config.py · .env
```

Principle: **LLM for language, code for decisions.** The LLM extracts facts and writes text. Python computes the score, priority, review flag and next action.

## 2. Data Flow

```
text ─► validate_enquiry_text ─► analyse_enquiry ─► ground_analysis ─► calculate_lead_score
      (reject bad input)        (LLM | mock |      (drop values not    (6 factors → 0-100)
                                 fallback)          in the text)
   ─► build_next_action ─► generate_response ─► check_response_safety ─► assess_human_review
      (action, urgency,     (LLM | template)     (unsafe → template)     (rules + reasons)
       missing info, Qs)
   ─► ProcessedEnquiry (validated) ─► save_enquiry (status = Draft) ─► UI / API response
```

`processing_mode` is set to `openai` (live), `mock` (no key) or `fallback` (AI failed), and is carried through to the UI and the database.

## 3. Component Responsibilities

| File | Responsibility | Key functions |
|---|---|---|
| `config.py` | Env vars, business profile and rules, `CATEGORY_PROFILES`, thresholds, `is_mock_mode()` | |
| `models/schemas.py` | All data contracts and AI-output normalisation | `EnquiryAnalysis`, `LeadScore`, `NextBestAction`, `HumanReview`, `ResponseDraft`, `ProcessedEnquiry` |
| `utils/validators.py` | Input validation, grounding, response guardrail | `validate_enquiry_text`, `ground_analysis`, `check_response_safety` |
| `services/ai_service.py` | The only place OpenAI is called; JSON parsing; self-repair retry; error mapping | `call_llm_json`, `analyse_enquiry`, `extract_json` |
| `services/mock_ai.py` | Rule-based analyser with the same output schema | `mock_analyse` |
| `services/scoring_service.py` | Deterministic lead score and explanation | `calculate_lead_score`, `priority_for` |
| `services/next_action_service.py` | Innovation: action, urgency, owner, missing info, questions | `build_next_action` |
| `services/response_service.py` | LLM draft with guardrail, or a safe template | `generate_response`, `template_response` |
| `services/review_service.py` | Human-review rules | `assess_human_review` |
| `services/pipeline.py` | Orchestration and DB-failure tolerance | `process_enquiry` |
| `database/database.py` | Schema, CRUD, stats, approval | `init_db`, `save_enquiry`, `list_enquiries`, `get_enquiry`, `update_status`, `get_stats` |
| `app.py` / `ui/components.py` | 4-page UI | |
| `api.py` | REST endpoints | `POST /enquiries`, `GET /enquiries`, `GET /enquiries/{id}`, `PATCH /enquiries/{id}/status`, `GET /stats`, `GET /health` |

## 4. Database Schema

```sql
CREATE TABLE IF NOT EXISTS enquiries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, source TEXT NOT NULL,
  original_enquiry TEXT NOT NULL,
  customer_name TEXT, company_name TEXT, email TEXT, requirement TEXT,
  category TEXT NOT NULL, budget TEXT, timeline TEXT, sentiment TEXT, confidence REAL,
  extracted_json TEXT NOT NULL,
  lead_score INTEGER NOT NULL, priority TEXT NOT NULL, scoring_explanation TEXT NOT NULL,
  next_action TEXT, response_subject TEXT, response_draft TEXT NOT NULL,
  human_review_required INTEGER NOT NULL, human_review_reason TEXT,
  processing_mode TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Draft', reviewer_notes TEXT,
  result_json TEXT NOT NULL
);
CREATE INDEX idx_enquiries_priority ON enquiries(priority);
CREATE INDEX idx_enquiries_review   ON enquiries(human_review_required, status);
```

Design: a **hybrid** of flat columns (for filtering, sorting and charts) and `result_json` (the full validated object, re-hydrated with `ProcessedEnquiry.model_validate`). One table keeps the MVP simple. A normalised design (separate `reviews` and `actions` tables) would suit a multi-user system. All SQL is parameterised, and connections are opened per operation with commit/rollback.

## 5. AI Prompt Strategy

- **Two focused calls** instead of one large one: *analysis* (temperature 0.2) and *reply* (temperature 0.4). Each has a clear schema, so each is easier to validate.
- **JSON mode** (`response_format={"type": "json_object"}`) together with the explicit key list and allowed values in the system prompt.
- **Extraction rules:** "extract only what is explicitly written; otherwise null", "company name only if a proper name is written", "copy budget/timeline wording exactly" (the last one makes grounding possible). The prompt also tells the model how to handle ambiguous cases (students → Internship, unhappy → Complaint, generic pricing → General Enquiry).
- **Reply prompt:** the business profile, the closed list of services, the business rules, explicit "no price / no dates / no response times", a complaint tone instruction, a length limit, and the **follow-up questions computed by the Next Best Action**. The model receives only the validated analysis, not raw prior output.
- The user text is wrapped in delimiters (`"""…"""`) to reduce prompt-injection influence. Even if the model is manipulated, its output still passes the schema, grounding and guardrail checks and a human approval step.

## 6. Structured Output Schema (`EnquiryAnalysis`)

```json
{
  "customer_name": "string|null", "company_name": "string|null", "email": "string|null",
  "industry": "string|null", "requirement": "string|null",
  "service_category": "one of 13 configured categories",
  "budget": "string|null", "timeline": "string|null",
  "intent": "buy_service|information|job_application|partnership|complaint|other",
  "sentiment": "positive|neutral|negative|angry",
  "is_urgent": "bool", "asks_for_pricing": "bool", "is_sensitive": "bool",
  "confidence": "0..1", "summary": "string"
}
```
`ResponseDraft`: `{"subject": 3–200 chars, "body": 20–4000 chars}`.

## 7. Validation

1. **Input:** not empty, 8–5000 characters, contains letters.
2. **Schema (Pydantic):** types, enums and ranges. Normalisers turn "Not mentioned"/"N/A"/"" into `null`, map unknown or partial category labels to configured ones or "Other", map unknown intent/sentiment to safe defaults, turn invalid emails into `null`, and convert confidence 85 to 0.85 (clamped).
3. **Grounding:** email, name and company must appear verbatim in the enquiry; budget numbers must be a subset of the numbers in the enquiry; timeline words must appear. Any violation sets the value to `null` and adds a visible warning.
4. **Response guardrail:** regular expressions find currency amounts (allowed only if the customer wrote that amount), "guarantee", "promise", "within N days/weeks", "deliver… by…", discounts and refunds. Any hit replaces the draft with the template, records the violations and forces human review.

## 8. Scoring Algorithm

```
score = intent(25) + clarity(20) + business_info(15) + budget(15) + timeline(10) + value(15)
priority = High if score >= 70 else Medium if score >= 40 else Low
```
- intent: buy_service 25, partnership 12, information 8, other 4, job_application/complaint 0
- clarity: requirement 8, + deliverable keyword 6, + ≥ 5 words 6
- business_info: company 6, industry 5, name/email 4
- budget: 15 if present
- timeline: urgent 10, otherwise any timeline 6
- value: `CATEGORY_PROFILES[cat].value_points` (0–12), + 3 if a scale regex matches (sales categories only), capped at 15

Explanation: factors at ≥ 60% of their maximum become "because…" clauses, and zero-point gap factors become "held back by…". There are special texts for complaint, job and partnership intents. The score is deterministic: same input, same score (this is tested).

## 9. Human Review Logic

Rules are OR-ed (any one triggers a review): complaint category · negative/angry sentiment · sensitive · partnership · "Other" · buying intent without a requirement · confidence < 0.6 · fallback mode · guardrail violation. Each rule appends a reason. Routine approval is always required regardless; the flag marks *special attention*.

## 10. Error Handling

| Layer | Mechanism |
|---|---|
| Input | `EnquiryValidationError` → UI warning / HTTP 422 |
| OpenAI | `openai.OpenAIError` subclasses → `AIServiceError` with a friendly message; SDK `max_retries=1`, configurable timeout |
| Output | `extract_json` + Pydantic → 1 self-repair retry → `AIServiceError` |
| Pipeline | `AIServiceError` → `mock_analyse` / `template_response`, mode `fallback`, warning, review forced |
| Database | `sqlite3.Error`/`OSError` → `DatabaseError`; the pipeline keeps the result and adds a warning; API → 503 |
| UI/API | Catch-all logs the traceback; the user gets a friendly message / HTTP 500 |

## 11. Security Considerations

- Secrets only in `.env` (git-ignored); `.env.example` has a placeholder. No keys in code, logs or the database.
- Parameterised SQL (no injection); the input length cap limits cost and abuse.
- Prompt-injection impact is limited by delimiters, schema validation, grounding, the guardrail and human approval. The system has no tools or actions the LLM can trigger, and it never sends email.
- Personal data (names, emails) is stored locally only. A production version would need a retention policy and access control.
- The API has no authentication (local MVP). In production: API keys or OAuth, HTTPS, rate limiting and CORS restrictions.

## 12. Scalability (target: 10,000 enquiries/day, about 7/min on average with peaks of maybe 10×)

1. API → **message queue** (Redis/RQ, Celery, SQS) → horizontally scaled **async workers** (`AsyncOpenAI`).
2. **PostgreSQL** with the same schema plus JSONB; connection pooling.
3. Backoff retries, a rate-limit-aware concurrency limit and a dead-letter queue for repeated failures.
4. Cost control: a small model for classification, deduplication of identical texts, the Batch API for non-urgent items, and the rule engine as a pre-filter for obvious spam.
5. Observability: structured logs, metrics (latency, fallback rate, guardrail hits, reviewer edit rate, cost/enquiry), alerts.
6. Stateless app servers behind a load balancer; the Streamlit UI becomes an internal reviewer console.

## 13. Limitations

- The rule-based fallback is less accurate than the LLM on unusual wording; the regex guardrail cannot catch every paraphrased commitment (mitigated by human approval).
- Grounding is literal matching: a correctly *paraphrased* timeline (e.g. "ASAP" → "as soon as possible") may be dropped. This errs on the safe side.
- Scoring weights are hand-tuned, not learned. A budget's *size* is not yet considered.
- Single-user, no auth, SQLite. No email ingestion or sending.
- I could not run live OpenAI calls in my build environment. The LLM path is covered by tests with a fake client, so the first live run should be checked manually.

## 14. Future Improvements

- Email/IMAP and website-form webhooks; send approved drafts through an email provider *after* approval.
- Learn scoring weights from outcomes (won/lost) and reviewer overrides; parse budget size.
- RAG over the studio's actual service, case-study and FAQ documents for richer grounded replies.
- An evaluation dataset with accuracy metrics per category, plus prompt regression tests.
- Auth and roles (sales, support, admin), audit log, PostgreSQL, queue workers, Docker, CI.
- Multilingual enquiries (Tamil/Hindi) and WhatsApp channel integration.
