# AI-Powered Business Enquiry Automation System

**Built for:** Curd Rice Business Studio – AI Intern Technical Assessment
**Author:** Mounika S S
**Stack:** Python · Streamlit · OpenAI API · FastAPI · SQLite · Pydantic

> Paste a customer enquiry, and the system extracts the key details, classifies it, scores the lead with transparent rules, recommends the next best action, drafts a safe reply and flags enquiries that need a human. It stores everything in SQLite. Replies are only ever drafts. Nothing is sent automatically.

---

## 1. Project Title

**AI-Powered Business Enquiry Automation System** with Lead Intelligence and Next Best Action.

## 2. Problem Statement

Curd Rice Business Studio receives enquiries through its website, email and other channels. They cover consulting, AI automation, websites, apps, branding, marketing, general questions, job requests, partnerships and complaints. Today someone has to read each one, work out what it is about, judge whether it is a real business opportunity, and write a reply. That approach has several problems:

- It is **slow**, and hot leads go cold while they wait in the inbox.
- It is **inconsistent**, because different people prioritise differently.
- It is **risky**, because a rushed reply can promise a price or a deadline the business cannot keep.
- **Unhappy customers** can be missed among routine messages.

## 3. Solution

A working application that runs the whole first-response workflow automatically and keeps a human in control:

1. **Understands** the enquiry with an LLM (OpenAI), returning strict JSON.
2. **Extracts** name, company, email, requirement, category, budget and timeline. Anything not mentioned is stored as `null`.
3. **Classifies** the enquiry into one of 13 configurable categories.
4. **Scores** the lead from 0 to 100 using **transparent Python rules**, not the LLM, and explains the score.
5. **Recommends a Next Best Action** (the innovation): what to do, who owns it, how urgent it is, why it matters, and what information is still missing.
6. **Drafts a personalised reply** under strict business rules, then **checks the draft automatically** for invented prices, guarantees or deadlines.
7. **Flags enquiries that need human review** and says why.
8. **Stores everything** in SQLite, with a history and approval screen, a dashboard, CSV batch upload and a REST API.

## 4. Features

| Area | Feature |
|---|---|
| Input | Web form, **CSV batch upload**, **REST API** (`POST /enquiries`), 14 built-in sample enquiries |
| AI | One OpenAI call for extraction, classification and signals (JSON mode), plus one call for the reply |
| Reliability | Pydantic validation, one self-repair retry on invalid JSON, a **rule-based fallback engine**, clear mock-mode banner |
| Anti-hallucination | **Grounding check** (extracted values must appear in the enquiry) and a **response guardrail** (no invented prices or dates) |
| Lead scoring | 6 weighted, explainable factors, deterministic, High/Medium/Low |
| Innovation | **Next Best Action**: action, owner, urgency, internal response target, why it matters, missing info, follow-up questions (fed into the reply) |
| Human-in-the-loop | Human-review rules with reasons; edit, **Approve** or **Reject** each draft; status tracking |
| Storage | SQLite created automatically; full JSON result plus queryable columns |
| UI | New Enquiry, Batch Processing, History & Approval, Dashboard (metrics, charts, review queue) |
| Testing | 21 automated tests (`unittest`), with no API key or network needed |

## 5. Architecture

```
            ┌──────────────── INPUT CHANNELS ────────────────┐
            │  Streamlit form   CSV upload   REST API (POST)  │
            └──────────────────────┬──────────────────────────┘
                                   ▼
                     services/pipeline.py  process_enquiry()
                                   │
  1. Validate input ───────────────┤ utils/validators.validate_enquiry_text
                                   ▼
  2. AI processing ──────► services/ai_service.analyse_enquiry
     (extraction +          ├─ OpenAI JSON mode → Pydantic EnquiryAnalysis
      classification)       ├─ invalid JSON → 1 self-repair retry
                            └─ API error / no key → services/mock_ai (rule engine)
                                   ▼
  3. Grounding check ──────► utils/validators.ground_analysis (drop invented values)
                                   ▼
  4. Lead scoring ─────────► services/scoring_service (6 factors → 0-100 → H/M/L + explanation)
                                   ▼
  5. Next Best Action ─────► services/next_action_service (action, urgency, owner, missing info)
                                   ▼
  6. Response draft ───────► services/response_service (LLM or template)
                            └─ utils/validators.check_response_safety → unsafe? use safe template
                                   ▼
  7. Human review ─────────► services/review_service (rules + reasons)
                                   ▼
  8. Database ─────────────► database/database.py (SQLite, status = "Draft")
                                   ▼
            History & Approval screen / API PATCH → Approved / Rejected (by a human)
```

**Customer enquiry → AI processing → information extraction → classification → lead scoring → next best action → response generation → human review → database**

Key design decision: **the LLM does the language work (understanding and writing). Python does the business decisions (score, priority, review, next action).** The decisions are therefore deterministic, testable and explainable, and the AI cannot "decide" to promise something.

## 6. Technology Stack

| Technology | Why |
|---|---|
| **Python 3.10+** | Best ecosystem for AI work; quick to build; easy to read in an interview |
| **Streamlit** | A full web UI in pure Python, so no React is needed; good for internal tools and demos |
| **OpenAI API** (Chat Completions, JSON mode) | Reliable language understanding and structured JSON output; `gpt-4o-mini` is cheap and fast. Works with any OpenAI-compatible endpoint (e.g. local Ollama) through `OPENAI_BASE_URL` |
| **FastAPI** | Gives the automation a real API, so website forms, email parsers, WhatsApp webhooks or n8n/Make can push enquiries in. Free Swagger docs at `/docs` |
| **SQLite** | Zero setup: one file, built into Python, created automatically. Ideal for an MVP |
| **Pydantic** | Validates every AI output against a schema, so the system never trusts raw LLM text |
| **python-dotenv** | Keeps the API key in `.env`, out of code and out of GitHub |
| **unittest** | Standard library, so the tests need no extra installs |

No LangChain/LangGraph: two well-defined LLM calls do not need an orchestration framework, and plain code is easier to debug and explain.

## 7. Project Structure

```
curd-rice-enquiry-automation/
├── app.py                        # Streamlit UI (4 pages)
├── api.py                        # FastAPI REST API (same pipeline)
├── config.py                     # env vars, business profile & rules, categories, thresholds
├── requirements.txt
├── .env.example                  # template – copy to .env
├── .gitignore                    # keeps .env and the database out of Git
├── models/
│   └── schemas.py                # Pydantic models: AI output, score, NBA, review, API bodies
├── services/
│   ├── pipeline.py               # the automation workflow (single entry point)
│   ├── ai_service.py             # OpenAI calls, JSON parsing, retry, error mapping
│   ├── mock_ai.py                # rule-based analyser (demo mode + fallback)
│   ├── scoring_service.py        # transparent lead-scoring algorithm
│   ├── next_action_service.py    # INNOVATION – Next Best Action & missing information
│   ├── response_service.py       # reply drafting + safe templates
│   └── review_service.py         # human-review rules
├── utils/
│   └── validators.py             # input validation, grounding check, response guardrail
├── database/
│   ├── database.py               # SQLite schema & queries
│   └── enquiries.db              # created automatically (git-ignored)
├── ui/
│   └── components.py             # reusable Streamlit display blocks
├── data/
│   ├── sample_enquiries.json     # 12 assessment samples + 2 extra
│   └── sample_enquiries.csv      # same data for the CSV upload demo
├── tests/
│   └── test_system.py            # 21 automated tests
├── TECHNICAL_DOCUMENTATION.md
├── DEMO_SCRIPT.md
└── AI_USAGE.md
```

## 8. Installation From Scratch (Windows)

### Step 1 – Install Python (skip this if `python --version` already shows 3.10 or newer)
1. Download Python 3.12 from <https://www.python.org/downloads/windows/>.
2. Run the installer and **tick "Add python.exe to PATH"** at the bottom of the first screen, then click *Install Now*.
3. Open a **new** Command Prompt and check:
```cmd
python --version
```

### Step 2 – Get the project folder
Either unzip the project to `C:\Projects\curd-rice-enquiry-automation`, or clone it from GitHub:
```cmd
mkdir C:\Projects
cd C:\Projects
git clone https://github.com/<your-username>/curd-rice-enquiry-automation.git
```

### Step 3 – Open a terminal in the project folder
Press **Win + R**, type `cmd`, press Enter, then:
```cmd
cd C:\Projects\curd-rice-enquiry-automation
```
(Or in File Explorer, open the folder, click the address bar, type `cmd` and press Enter.)

### Step 4 – Create and activate a virtual environment
```cmd
python -m venv .venv
.venv\Scripts\activate
```
Your prompt now starts with `(.venv)`.
*Using PowerShell instead?* Run `.\.venv\Scripts\Activate.ps1`. If you see a "running scripts is disabled" error, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, answer `Y`, and try again.

### Step 5 – Install the requirements
```cmd
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 6 – Create `.env` and add your API key
```cmd
copy .env.example .env
notepad .env
```
Replace `sk-your-key-here` with your real key, then save and close Notepad. *(No key? Leave it unchanged and the app runs in **demo mode**.)*

### Step 7 – Run the application
```cmd
streamlit run app.py
```
Your browser opens at <http://localhost:8501>. To stop the app, press **Ctrl + C** in the terminal.

### Optional – Run the REST API (second terminal, venv activated)
```cmd
uvicorn api:app --reload --port 8000
```
Open <http://127.0.0.1:8000/docs> to try the API interactively.

### Optional – Run the tests
```cmd
python -m unittest discover -s tests -v
```

## 9. API Key Setup

1. Create a key at <https://platform.openai.com/api-keys>.
2. Put it **only** in `.env`:
   ```
   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxx
   OPENAI_MODEL=gpt-4o-mini
   ```
3. `config.py` loads it with `python-dotenv`. The key never appears in the code.

**Keeping it out of GitHub:** `.gitignore` already lists `.env` and `*.db`. Before pushing, check:
```cmd
git status
git check-ignore .env
```
`git check-ignore .env` should print `.env`, which means Git ignores it. Only `.env.example` (with a placeholder) is committed. If a key is ever pushed by mistake, **revoke it** on the OpenAI dashboard immediately.

**Optional settings:** `OPENAI_BASE_URL` (any OpenAI-compatible server, e.g. a local Ollama at `http://localhost:11434/v1`), `FORCE_MOCK_MODE=true` (demo mode even with a key), `OPENAI_TIMEOUT_SECONDS`.

**Demo / mock mode** is used automatically when no key is set. The app shows a yellow **DEMO / MOCK MODE** banner, every result is labelled `mock`, and the built-in rule engine plus safe templates are used.

## 10. Database

- **Engine:** SQLite, through Python's built-in `sqlite3` (no server, no installation).
- **Location:** `database/enquiries.db` (change it with `DB_PATH` in `.env`).
- **Creation:** automatic. `init_db()` runs `CREATE TABLE IF NOT EXISTS` when the app or API starts and before every save.
- **Table `enquiries`:**

| Column | Purpose |
|---|---|
| `id` | Enquiry ID (auto-increment) |
| `created_at`, `updated_at` | Timestamps |
| `source` | website / email / csv / api … |
| `original_enquiry` | The customer's text |
| `customer_name`, `company_name`, `email`, `requirement`, `budget`, `timeline` | Extracted information (`NULL` = not mentioned) |
| `category`, `sentiment`, `confidence` | Classification |
| `extracted_json` | The full validated AI extraction |
| `lead_score`, `priority`, `scoring_explanation` | Lead intelligence |
| `next_action` | Recommended next best action |
| `response_subject`, `response_draft` | The reply draft (editable by the reviewer) |
| `human_review_required`, `human_review_reason` | Review flag and reasons |
| `processing_mode` | `openai` / `mock` / `fallback` |
| `status`, `reviewer_notes` | `Draft` → `Approved` / `Rejected` (set by a human) |
| `result_json` | The complete result, so any record can be re-displayed exactly |

- **Retrieval:** `list_enquiries()` (filter by priority, category, status, review flag), `get_enquiry(id)`, `get_stats()` for the dashboard, `update_status()` for approvals. All queries are parameterised, which prevents SQL injection.

## 11. AI Workflow

The system makes two LLM calls per enquiry, both in **JSON mode** at a low temperature:

1. **Analysis call:** the system prompt contains the business's services, the exact JSON schema, the allowed categories and strict extraction rules ("extract only what is written; otherwise null"). The output is validated by the `EnquiryAnalysis` Pydantic model.
2. **Response call:** the prompt contains the business profile, the business rules, the validated analysis and the **follow-up questions from the Next Best Action**. The output is validated by `ResponseDraft` and then by the safety guardrail.

The LLM **never** decides the score, priority, human-review flag or next action. Those come from Python rules.

## 12. Lead Scoring Logic

Implemented in `services/scoring_service.py`. The score is the sum of six factors (maximum 100):

| Factor | Max | Rule |
|---|---|---|
| Business intent | 25 | buy a service = 25 · partnership = 12 · information = 8 · other = 4 · job/complaint = 0 |
| Requirement clarity | 20 | requirement stated = 8, + concrete deliverable named (system, website, ERP, chatbot…) = 6, + ≥ 5 words of detail = 6 |
| Business information | 15 | company name = 6 · industry = 5 · contact name/email = 4 |
| Budget | 15 | any budget stated = 15 |
| Timeline / urgency | 10 | urgent ("immediately", "this week") = 10 · other timeline = 6 |
| Project value | 15 | category value 0–12 (from `config.CATEGORY_PROFILES`) + 3 for a scale/complexity signal ("500 enquiries per day", "ERP", "12 stores") |

**Priority thresholds:** **High ≥ 70**, **Medium 40–69**, **Low < 40** (in `config.py`).

**Explanation:** generated from the factors. Factors scoring at least 60% of their maximum become reasons ("…because the customer shows clear intent to buy a service, a budget has been specified (₹2 lakh) and the customer wants to start soon"). Factors scoring 0 are listed as "Score held back by: no budget mentioned…".

Complaints and job applications score low **on purpose**. The score measures *sales potential*. Their urgency is handled by the Next Best Action (a complaint gets **Critical** urgency) and by human review.

## 13. Human Review Logic

`services/review_service.py`. Every draft needs a human's approval before it is sent. On top of that, an enquiry is flagged **HUMAN REVIEW REQUIRED** if any of these apply:

| Rule | Example |
|---|---|
| Category is Complaint / Support | "I am unhappy with the service…" |
| Sentiment is negative or angry | "This is unacceptable…" |
| Sensitive content | legal threats, data issues, medical, harassment |
| Partnership request | needs a management decision |
| Category "Other" | unusual request |
| Buying intent but no clear requirement | unclear requirement |
| AI confidence < 0.6 | the model is unsure |
| Processed by the fallback engine | the AI failed, so the analysis should be verified |
| The AI draft broke a business rule | the draft was replaced by a template, so the reply should be checked |

Each triggered rule adds a plain-English reason, shown in the UI and stored in `human_review_reason`. Otherwise the app shows *"No human review required."*

## 14. Innovation – Next Best Action & Missing-Information Detection

**The problem:** a lead score tells the team *how good* a lead is. It does not tell them *what to do*. In practice, most first replies are a slow back-and-forth to collect basics like budget, timeline or company name.

**What it does** (`services/next_action_service.py`). For every enquiry it produces:

- **Recommended action:** e.g. *"Schedule a discovery call to confirm scope"* (High lead), *"Escalate to the account manager and call the customer personally"* (complaint), *"Forward to the founders/management"* (partnership), *"Forward to the hiring team"* (internship).
- **Urgency** (Critical / High / Medium / Low), **owner team** (Sales, Customer Success, Management, HR) and an **internal response target** (2 h / 24 h / 48 h…). The target is internal only and is never promised to the customer.
- **Why it matters:** built from the scoring signals.
- **Missing information:** the standard fields (budget, timeline, company, contact) plus **category-specific discovery questions** (e.g. AI Automation → *"Roughly how many requests per day?"*, Website → *"Do you already have a domain?"*).
- **Closing the loop:** the questions are **inserted into the reply draft automatically**, so the first reply already collects what sales needs. That saves a full email round-trip.

**Why it is useful:** it turns raw AI analysis into a playbook step a sales team can follow, keeps the separation between *how valuable a lead is* (score) and *how urgent it is* (a complaint is low value but critical), and shortens the time to a qualified discovery call. It is rule-based, so it is explainable and testable, and adding a category with its own questions only needs one entry in `config.py`.

Example (sample 008):
```
Lead Score: 70/100   Priority: HIGH
Next Best Action: Schedule a discovery call to confirm scope; prepare relevant case examples.
Urgency: High · Owner: Sales · Internal target: 24 hours
Missing information: Approximate budget range, Company name, Contact name / phone number,
                     Which channels or tools you currently use for this process
```

## 15. Error Handling

| Situation | What happens |
|---|---|
| **API key missing** | Demo/mock mode switches on automatically, with a banner in the UI; `/health` reports `"ai_mode": "mock"` |
| **API fails** (bad key, quota, network, timeout, unknown model) | The OpenAI exception becomes a readable `AIServiceError`; the rule-based fallback analyses the enquiry and a safe template reply is used; mode is `fallback`, a warning is shown, and **human review is forced** |
| **AI output invalid / malformed JSON** | The JSON is parsed defensively (code fences and extra text stripped), then validated by Pydantic. If it fails, the model gets **one self-repair retry** with the error message. If that also fails, the fallback is used |
| **AI output has wrong values** | Validators normalise "Not mentioned" to `null`, map unknown categories to "Other", clamp confidence to 0–1, and drop invalid emails |
| **AI invents facts** | The grounding check removes extracted values that are not in the enquiry; the response guardrail replaces drafts with invented prices, guarantees or timeframes |
| **Invalid enquiry** (empty, too short, no letters, over 5000 characters) | Rejected before any AI call with a clear message (UI warning / HTTP 422) |
| **Database fails** | `DatabaseError` with a readable message. The analysis is still shown, with a "could not be saved" warning. The API returns HTTP 503 |
| **Bad CSV** | Unreadable file or missing column → clear error; bad rows are skipped and listed |
| **Unexpected exception** | Logged with a full traceback in the terminal; the user sees a friendly message (UI) or HTTP 500 (API) |

## 16. Testing

**Automated:** `python -m unittest discover -s tests -v` runs **21 tests** covering input validation, all 12 samples, classification and priority expectations, human-review rules, deterministic scoring, the pricing-request rule, the grounding check, the response guardrail, malformed-JSON retry, AI-failure fallback, replacement of a rule-breaking draft, and the database round-trip with approval. The LLM paths are tested with a fake OpenAI client, so no API key is needed.

**Manual test cases (expected results in demo mode; live AI should match on category and review status, while extracted wording may differ slightly):**

| ID | Enquiry (short) | Category | Score | Priority | Human review | Next-action urgency |
|---|---|---|---|---|---|---|
| 001 | Jewellery – AI WhatsApp support | AI Automation | 62 | Medium | No | Medium |
| 002 | Website, ₹2 lakh, this week | Website Development | 83 | **High** | No | High |
| 003 | What services do you offer? | General Enquiry | 11 | Low | No | Low |
| 004 | Automate inventory & dispatch | Operational Systems | 57 | Medium | No | Medium |
| 005 | Digital marketing internship | Internship / Job Application | 8 | Low | No | Low |
| 006 | ERP for silver jewellery | Operational Systems | 65 | Medium | No | Medium |
| 007 | Send your pricing | General Enquiry | 11 | Low | No | Medium (no price invented) |
| 008 | AI for 500 enquiries/day, immediately | AI Automation | 70 | **High** | No | High |
| 009 | Student – college project | Internship / Job Application | 8 | Low | No | Low |
| 010 | AI assistant on internal documents | AI Automation | 60 | Medium | No | Medium |
| 011 | Partnership opportunity | Partnership | 31 | Low | **Yes** | Medium |
| 012 | Unhappy, call me urgently | Complaint / Support | 24 | Low | **Yes** | **Critical** |
| X01 | Full details: name, company, email, ₹5 lakh, 12 stores | Business Intelligence | 96 | **High** | No | High |
| X02 | Angry, data leak, lawyer | Complaint / Support | 0 | Low | **Yes** (3 reasons) | **Critical** |

**Edge cases to try:** an empty enquiry (warning), `hi` (too short), `12345 !!!` (no readable text), a CSV without an `enquiry` column (clear error), and an invalid API key (the fallback banner appears and review is forced).

## 17. Sample Enquiries

All are in `data/sample_enquiries.json` / `.csv`. Load them from the dropdown on the **New Enquiry** page, or process them all at once on **Batch Processing**.

| ID | Enquiry |
|---|---|
| 001 | We are a jewellery business looking for an AI-powered WhatsApp customer support system. |
| 002 | Need a website for our manufacturing company. Budget is ₹2 lakh. Can we discuss this week? |
| 003 | What services do you offer? |
| 004 | We want to automate our inventory and dispatch operations. |
| 005 | Looking for a digital marketing internship. |
| 006 | We are interested in developing an ERP system for our silver jewellery business. |
| 007 | Your services look interesting. Please send your pricing details. |
| 008 | Need AI automation for handling 500 customer enquiries per day. We want to start immediately. |
| 009 | I am a student looking for a college project opportunity. |
| 010 | We need an AI assistant that can read documents and answer questions from our internal company data. |
| 011 | I want to partner with your company for a business opportunity. |
| 012 | I am unhappy with the service received and need someone to call me urgently. |
| X01 | Hi, I'm Priya Sharma from Lakshmi Textiles (priya@lakshmitextiles.in). We need a Power BI sales dashboard connected to our ERP for 12 stores. Budget around ₹5 lakh, we'd like to start next month. *(extra: full-detail lead)* |
| X02 | This is unacceptable. Your team shared our confidential sales data with another client. Our lawyer will contact you. *(extra: angry + sensitive)* |

All names and companies in the extra samples are fictional.

## 18. How to Run

```cmd
.venv\Scripts\activate
streamlit run app.py
```
Optional API: `uvicorn api:app --reload --port 8000` → <http://127.0.0.1:8000/docs>

Example API call (PowerShell):
```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/enquiries -ContentType "application/json" -Body '{"text":"We want to automate our inventory and dispatch operations.","source":"website"}'
```

## 19. Technical Interview Questions

**Why did you choose this architecture?**
A single pipeline function (`process_enquiry`) with one small service per responsibility: AI, scoring, next action, response, review, storage. The UI, the API and the CSV batch all call the same function, so there is no duplicated logic and each step can be tested on its own. It is simple enough to explain, and each service could become a separate worker later.

**Why this technology stack?**
Python for its AI ecosystem; Streamlit for a full UI without frontend work; FastAPI so other systems can push enquiries automatically; OpenAI JSON mode for reliable structured output; Pydantic to validate it; SQLite for zero-setup storage. Everything is free to run locally.

**Why SQLite?**
It needs no server, is built into Python, is one file and is created automatically, which is enough for hundreds of thousands of rows. Queries are plain SQL, so moving to PostgreSQL later only means changing the connection layer.

**Why use an LLM?**
Enquiries are free text with endless phrasing. Keyword rules break on wording like "need folks to handle our WhatsApp chats". An LLM understands intent, extracts entities and writes natural, personalised replies. I use it only for language tasks, and the business decisions stay in code.

**How does the system decide the lead priority?**
Six transparent factors: intent 25, requirement clarity 20, business info 15, budget 15, timeline 10 and project value 15, for a total out of 100. High is 70 or more, Medium is 40 or more, otherwise Low. The LLM only provides facts. The points come from Python, and the explanation is generated from the same factors, so the reasoning is always shown.

**How do you prevent the AI from generating incorrect business information?**
Five layers: (1) strict prompts that list only the real services and rules; (2) "null if not mentioned" plus Pydantic normalisation; (3) a **grounding check** that removes any extracted name, email, company, budget or timeline not found in the enquiry; (4) a **response guardrail** that scans drafts for prices, guarantees, timeframes and discounts and replaces unsafe drafts with a safe template; (5) **human approval**: nothing is ever sent automatically.

**What happens if the LLM returns invalid JSON or the AI model fails?**
The JSON is parsed defensively and validated by Pydantic. If it is invalid, the model gets one retry with the validation error ("self-repair"). If that also fails, or the API errors, the rule-based engine processes the enquiry, the mode is marked `fallback`, a warning is shown and human review is forced. The user never sees a crash.

**How do you handle API failure?**
All OpenAI exceptions (authentication, rate limit, timeout, connection, model not found) are mapped to a readable `AIServiceError`. The pipeline catches it and falls back. The client also uses a timeout and the SDK's built-in retry.

**How would you scale to 10,000 enquiries per day?**
10,000 a day is only about 7 per minute on average, so the main issues are reliability and cost rather than raw throughput. (1) Put the FastAPI endpoint in front of a **queue** (Redis/RQ, Celery or SQS) and process with several **async workers**. (2) Move from SQLite to **PostgreSQL**. (3) Add **retries with exponential backoff** and rate-limit handling, plus a dead-letter queue. (4) **Cache or deduplicate** repeated enquiries and use a small, cheap model for classification. Consider the **OpenAI Batch API** for non-urgent items. (5) Monitor latency, cost per enquiry, fallback rate and reviewer overrides. (6) Add authentication and API keys on the endpoint.

**What would you improve with another two days?**
Gmail/IMAP ingestion and a website-form webhook; sending approved drafts through the email API after approval; a feedback loop where reviewer edits and won/lost deals tune the scoring weights; RAG over the studio's real service and FAQ documents so replies are richer but still grounded; role-based login; PostgreSQL and a queue; an evaluation set to measure classification accuracy; and Docker for deployment.

**What is the role of human approval?**
The AI prepares; a human decides. Every draft is stored as `Draft` and only a person can mark it `Approved` or `Rejected`, optionally after editing it. Risky cases (complaints, partnerships, sensitive or unclear enquiries, low confidence, AI failures) are highlighted with reasons, so reviewers spend their time where it matters.

**How is your innovative feature useful?**
It turns analysis into action. The team immediately knows what to do, who owns it and how urgently. The missing-information questions are built into the first reply, which removes an email round-trip and gets a qualified lead to a discovery call faster. It also separates value from urgency: a complaint is low value but critical.

**Why not let the LLM give the score?**
LLM scores are inconsistent (the same enquiry can score 72 one time and 85 the next), cannot be audited and are hard to tune. Rules are deterministic, explainable to the business and adjustable in `config.py`.

## Known Limitations

- The mock/fallback engine is keyword-based, so it is less accurate than the LLM on unusual phrasing.
- The response guardrail uses regular expressions, so it catches common price and date patterns but not every possible paraphrase. Human approval is the final safety net.
- Single-user local app: no authentication, and SQLite is not intended for heavy concurrent writes.
- The email is drafted but deliberately not sent; there is no inbox integration yet.
- Scoring weights are expert-chosen, not yet learned from real conversion data.
