# AI-Powered Business Enquiry Automation System

**Built for:** Curd Rice Business Studio – AI Intern Technical Assessment  
**Author:** Sakthisree  
**Stack:** Python · Streamlit · Google Gemini API · FastAPI · SQLite · Pydantic

---

## 1. Project Overview

The **AI-Powered Business Enquiry Automation System** automates the first-response workflow for customer and business enquiries.

A user can submit an enquiry, and the system:

1. Extracts important information using an LLM.
2. Classifies the enquiry.
3. Calculates a transparent lead score using deterministic Python rules.
4. Determines the lead priority.
5. Recommends a **Next Best Action**.
6. Identifies missing information.
7. Generates a safe, personalised response draft.
8. Checks the response for potentially invented business information.
9. Determines whether human review is required.
10. Stores the complete result in SQLite.

**Important:** Responses are always stored as drafts. The system does not automatically send messages to customers.

---

## 2. Problem Statement

Curd Rice Business Studio can receive enquiries related to:

- AI automation
- Website development
- Applications and ERP systems
- Operational systems
- Business intelligence
- Branding and design
- Digital marketing
- General questions
- Internships and job opportunities
- Partnerships
- Complaints and support

Manually processing every enquiry creates several problems:

- **Slow response:** High-value leads may wait too long.
- **Inconsistent prioritisation:** Different team members may evaluate enquiries differently.
- **Business risk:** Replies may accidentally promise prices, deadlines or guarantees.
- **Missed urgent issues:** Complaints and sensitive enquiries can be overlooked.
- **Repeated communication:** Sales teams may need multiple messages to collect basic information.

The goal of this project is to automate the repetitive first-response work while keeping important business decisions and customer communication under human control.

---

## 3. Solution

The system follows a hybrid architecture:

> **LLM for language understanding and generation + Python for deterministic business decisions.**

### Processing flow

1. **Input validation**
2. **AI analysis**
3. **Pydantic validation**
4. **Grounding check**
5. **Deterministic lead scoring**
6. **Next Best Action**
7. **Response generation**
8. **Response safety check**
9. **Human-review decision**
10. **SQLite storage**

The LLM does not decide the lead score, priority, review requirement or next action. These are determined by Python business rules.

This makes the system more predictable, testable and explainable.

---

## 4. Key Features

| Area | Feature |
|---|---|
| Input | Streamlit web form, CSV batch upload and REST API |
| AI | Google Gemini for extraction, classification and response generation |
| Structured output | JSON output validated using Pydantic |
| Reliability | Validation, retry handling and rule-based fallback |
| Grounding | Removes extracted values that are not supported by the enquiry |
| Response safety | Checks generated replies for unsafe/invented business information |
| Lead scoring | Six weighted, explainable factors |
| Priority | High / Medium / Low |
| Innovation | Next Best Action with owner, urgency and missing information |
| Human-in-the-loop | Review, edit, approve or reject response drafts |
| Storage | SQLite |
| UI | New Enquiry, Batch Processing, History & Approval, Dashboard |
| API | FastAPI REST API with Swagger documentation |
| Testing | 21 automated tests |

---

## 5. Architecture

```text
                  ┌──────────────────────────────┐
                  │       INPUT CHANNELS         │
                  │                              │
                  │ Streamlit │ CSV │ REST API   │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │     services/pipeline.py     │
                  │      process_enquiry()       │
                  └──────────────┬───────────────┘
                                 │
                    1. Validate input
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │      Gemini AI Analysis      │
                  │                              │
                  │ Extraction + Classification  │
                  │ Structured JSON output       │
                  └──────────────┬───────────────┘
                                 │
                    2. Pydantic validation
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │      Grounding Check         │
                  │                              │
                  │ Remove unsupported values    │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │      Lead Scoring            │
                  │                              │
                  │ Deterministic Python rules   │
                  │ Score: 0–100                 │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │      Next Best Action        │
                  │                              │
                  │ Action │ Owner │ Urgency     │
                  │ Missing information          │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │     Response Generation      │
                  │                              │
                  │ Gemini / Safe Template       │
                  └──────────────┬───────────────┘
                                 │
                    Response safety check
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │       Human Review           │
                  │                              │
                  │ Edit │ Approve │ Reject      │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │        SQLite Database        │
                  └──────────────────────────────┘
```

### Core design principle

**The LLM handles language. Python handles business decisions.**

This separation prevents the model from directly determining business-critical decisions such as lead priority or whether an enquiry requires human review.

---

## 6. Technology Stack

| Technology | Purpose |
|---|---|
| **Python 3.10+** | Core application and business logic |
| **Streamlit** | Web-based user interface |
| **Google Gemini API** | Enquiry understanding and response generation |
| **FastAPI** | REST API and automation integration |
| **Pydantic** | Validation of structured AI outputs |
| **SQLite** | Local persistent storage |
| **python-dotenv** | Environment variable management |
| **unittest** | Automated testing |

### Why this stack?

Python provides a strong ecosystem for AI and data processing.

Streamlit allows a functional web UI to be built without a separate frontend framework.

FastAPI provides a real API that can later receive enquiries from website forms, email systems, WhatsApp integrations or workflow automation platforms.

SQLite provides zero-configuration persistent storage and is suitable for an MVP.

Pydantic ensures that AI-generated structured data is validated before entering the business pipeline.

---

## 7. Project Structure

```text
curd-rice-enquiry-automation/
│
├── app.py
├── api.py
├── config.py
├── requirements.txt
├── .gitignore
│
├── models/
│   └── schemas.py
│
├── services/
│   ├── pipeline.py
│   ├── ai_service.py
│   ├── mock_ai.py
│   ├── scoring_service.py
│   ├── next_action_service.py
│   ├── response_service.py
│   └── review_service.py
│
├── utils/
│   └── validators.py
│
├── database/
│   └── database.py
│
├── ui/
│   └── components.py
│
├── data/
│   ├── sample_enquiries.json
│   └── sample_enquiries.csv
│
├── tests/
│   └── test_system.py
│
├── README.md
├── TECHNICAL_DOCUMENTATION.md
├── DEMO_SCRIPT.md
└── AI_USAGE.md
```

### Important

The following files are intentionally excluded from GitHub:

```text
.env
.venv/
*.db
```

The Gemini API key is stored locally in `.env` and is never committed to the repository.

---

## 8. Installation

### Step 1 – Install Python

Python 3.10 or newer is recommended.

Check the installed version:

```powershell
python --version
```

---

### Step 2 – Clone the repository

```powershell
git clone https://github.com/sakthisree08/curdrice-business-studio-enquiry-automation.git
```

Enter the project directory:

```powershell
cd curdrice-business-studio-enquiry-automation
```

---

### Step 3 – Create a virtual environment

```powershell
python -m venv .venv
```

Activate it in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

The terminal should now show:

```text
(.venv)
```

---

### Step 4 – Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 9. Gemini API Configuration

The application uses the **Google Gemini API** for live AI processing.

Create a local `.env` file in the project root.

Example:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_TIMEOUT_SECONDS=30

FORCE_MOCK_MODE=false
```

**Never commit `.env` to GitHub.**

The repository's `.gitignore` already excludes `.env`.

### Demo / Mock mode

The application can also operate without a Gemini API key.

If no key is available, the system uses the built-in rule-based mock/fallback engine.

This allows the application to be demonstrated without requiring an external API connection.

---

## 10. Running the Application

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run Streamlit:

```powershell
streamlit run app.py
```

The application normally opens at:

```text
http://localhost:8501
```

The Streamlit interface provides:

- New Enquiry
- Batch Processing
- Enquiry History & Approval
- Dashboard

---

## 11. Running the REST API

Open a second terminal and activate the virtual environment.

Run:

```powershell
uvicorn api:app --reload --port 8000
```

Open the Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

### Example API request

PowerShell:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/enquiries `
  -ContentType "application/json" `
  -Body '{"text":"We want to automate our inventory and dispatch operations.","source":"website"}'
```

The API uses the same processing pipeline as the Streamlit application.

---

## 12. AI Workflow

The system uses Gemini for language-related tasks.

### Step 1 – Enquiry analysis

The AI analyses the customer message and extracts structured information such as:

- Customer name
- Company
- Email
- Industry
- Requirement
- Service category
- Budget
- Timeline
- Intent
- Sentiment
- Urgency
- Pricing request
- Sensitive content
- Confidence
- Summary

Information that is not mentioned is represented as `null`.

The response is parsed and validated using the `EnquiryAnalysis` Pydantic model.

---

### Step 2 – Grounding

The extracted information is checked against the original enquiry.

If the AI introduces unsupported information, the validator removes or normalises it.

This reduces the risk of hallucinated customer details.

---

### Step 3 – Lead scoring

The validated information is passed to the deterministic Python scoring engine.

The AI does **not** assign the score.

---

### Step 4 – Next Best Action

The system determines:

- Recommended action
- Owner team
- Urgency
- Internal response target
- Why the action matters
- Missing information
- Follow-up questions

The follow-up questions can then be included in the response draft.

---

### Step 5 – Response generation

Gemini generates a customer-facing response based on:

- Business profile
- Validated enquiry information
- Business rules
- Next Best Action
- Required follow-up information

The generated response is then checked by the response safety layer.

If the response violates business rules, a safe template is used instead.

---

## 13. Lead Scoring

The lead score is calculated using six deterministic factors.

| Factor | Maximum |
|---|---:|
| Business intent | 25 |
| Requirement clarity | 20 |
| Business information | 15 |
| Budget | 15 |
| Timeline / urgency | 10 |
| Project value | 15 |
| **Total** | **100** |

### Priority thresholds

| Score | Priority |
|---:|---|
| 70–100 | High |
| 40–69 | Medium |
| 0–39 | Low |

### Important design decision

The score is calculated in Python rather than by the LLM.

This provides:

- Consistency
- Explainability
- Testability
- Easy tuning
- Auditability

---

## 14. Next Best Action

The **Next Best Action** is the main innovation in the system.

A lead score tells the team:

> "How valuable is this enquiry?"

It does not necessarily tell them:

> "What should we do next?"

The Next Best Action bridges this gap.

### Example

For a high-value AI automation enquiry:

```text
Lead Score: 70/100
Priority: High

Next Best Action:
Schedule a discovery call to confirm scope.

Owner:
Sales

Urgency:
High

Missing information:
- Company name
- Approximate budget
- Current tools
- Expected enquiry volume

Follow-up questions:
- Approximately how many enquiries do you currently receive per day?
- Which channels are currently used?
```

The questions can be included directly in the response draft.

This reduces unnecessary back-and-forth between the customer and sales team.

---

## 15. Human Review

The system follows a **human-in-the-loop** approach.

Every generated response is initially stored as:

```text
Draft
```

A human can:

```text
Edit → Approve
```

or:

```text
Reject
```

The system flags enquiries for human review when appropriate.

Examples include:

- Complaints
- Negative sentiment
- Sensitive content
- Partnership requests
- Unclear requirements
- Low AI confidence
- AI fallback processing
- Unsafe response drafts

### Core principle

> **AI prepares. Human decides.**

Nothing is automatically sent to a customer.

---

## 16. Error Handling and Reliability

| Situation | System behaviour |
|---|---|
| Missing Gemini API key | Uses mock/demo mode |
| Gemini API failure | Uses rule-based fallback |
| Invalid JSON | Parses defensively and attempts one repair |
| Pydantic validation failure | Retry, then fallback |
| Unsupported extracted values | Grounding validation removes them |
| Unsafe response | Safe template replaces the response |
| Invalid enquiry | Rejected before AI processing |
| Database failure | Error is reported without crashing the UI |
| Invalid CSV | Clear error with problematic rows |
| Unexpected exception | Logged and shown as a friendly error |

The fallback engine ensures that the application remains demonstrable even when the external AI service is unavailable.

---

## 17. Database

The application uses SQLite.

The database is created automatically when the application starts.

The database stores:

- Original enquiry
- Extracted customer information
- Classification
- Sentiment
- AI confidence
- Lead score
- Priority
- Scoring explanation
- Next Best Action
- Response subject
- Response draft
- Human-review requirement
- Human-review reason
- Processing mode
- Approval status
- Reviewer notes
- Complete result JSON

The database file is ignored by Git and is not included in the repository.

---

## 18. Testing

Run the automated tests using:

```powershell
python -m unittest discover -s tests -v
```

The project contains **21 automated tests** covering:

- Input validation
- Enquiry classification
- Lead scoring
- Priority calculation
- Human-review rules
- Pricing request handling
- Grounding validation
- Response safety guardrails
- Invalid AI output
- AI failure fallback
- Safe response replacement
- Database storage
- Approval workflow

The tests do not require a live Gemini API connection.

---

## 19. Sample Enquiries

The project includes sample enquiries covering different business scenarios.

### 1. AI Automation

```text
We are a jewellery business looking for an AI-powered WhatsApp customer support system.
```

### 2. Website Development

```text
Need a website for our manufacturing company. Budget is ₹2 lakh. Can we discuss this week?
```

### 3. General Enquiry

```text
What services do you offer?
```

### 4. Operational Automation

```text
We want to automate our inventory and dispatch process. We currently use Excel and have 3 warehouses.
```

### 5. Internship

```text
Hi, I am looking for a digital marketing internship. Do you have any openings?
```

### 6. ERP

```text
We are a silver jewellery business and need a custom ERP application to manage inventory, sales, and accounting.
```

### 7. Pricing

```text
Can you send me your pricing details?
```

### 8. Urgent AI Automation

```text
We need an AI automation solution for handling around 500 customer enquiries per day. This is urgent and we want to start immediately.
```

### 9. Student Project

```text
I am a college student looking for a project/internship opportunity. Can you help me with a final-year project?
```

### 10. Internal AI Assistant

```text
We need an AI assistant that can read documents and answer questions from our internal company data.
```

### 11. Partnership

```text
We are interested in partnering with your company for technology projects. Can we discuss a possible partnership?
```

### 12. Complaint

```text
I am unhappy with the service we received. The issue has not been resolved despite multiple follow-ups. Please have someone call me urgently.
```

These can be processed individually through **New Enquiry** or together through **Batch Processing**.

---

## 20. API and Automation

The FastAPI layer allows external systems to submit enquiries.

Potential integrations include:

```text
Website Form
     │
     ▼
FastAPI
     │
     ▼
Enquiry Pipeline
     │
     ├── AI Analysis
     ├── Lead Scoring
     ├── Next Best Action
     ├── Response Draft
     └── Human Review
```

This architecture can later be connected to:

- Website enquiry forms
- Email ingestion
- WhatsApp webhooks
- CRM systems
- n8n
- Make
- Zapier
- Other internal systems

---

## 21. Why the Architecture?

The project uses one central pipeline:

```text
process_enquiry()
```

The Streamlit UI, CSV processing and FastAPI endpoint all use the same pipeline.

This avoids duplicated business logic.

Each responsibility is separated into its own service:

```text
ai_service.py
scoring_service.py
next_action_service.py
response_service.py
review_service.py
database.py
```

This makes the system easier to:

- Test
- Debug
- Explain
- Maintain
- Extend

---

## 22. Why Not Let the LLM Decide the Score?

LLM-generated scores can vary between runs.

For example, the same enquiry could receive different scores depending on model behaviour.

Instead:

```text
LLM
 ↓
Extract facts
 ↓
Python rules
 ↓
Deterministic score
 ↓
Priority
```

This makes the scoring logic transparent and auditable.

---

## 23. Preventing Incorrect Business Information

The system uses multiple protection layers:

### 1. Prompt constraints

The model receives the actual business profile and instructions to avoid unsupported information.

### 2. Structured output

AI output is validated using Pydantic.

### 3. Grounding check

Extracted information is checked against the original enquiry.

### 4. Response guardrail

The generated response is checked for potentially invented:

- Prices
- Discounts
- Guarantees
- Deadlines
- Commitments

### 5. Human approval

Every response remains a draft until reviewed by a person.

---

## 24. Scaling to 10,000 Enquiries per Day

The current application is designed as an MVP and runs locally.

For approximately 10,000 enquiries per day, the architecture could be extended to:

1. Put a queue between the API and processing workers.
2. Replace SQLite with PostgreSQL.
3. Run multiple asynchronous workers.
4. Add retry and exponential backoff handling.
5. Add rate-limit management.
6. Add deduplication and caching.
7. Monitor latency, AI cost, fallback rate and reviewer overrides.
8. Add API authentication.
9. Add structured logging and monitoring.
10. Separate urgent enquiries from batch processing.

The current separation between API, pipeline and individual services makes this migration easier.

---

## 25. Improvements With Two More Days

Possible improvements include:

- Gmail/IMAP enquiry ingestion
- Website-form webhook
- Approved-response email integration
- CRM integration
- PostgreSQL
- Background job queue
- Role-based authentication
- RAG over the company's real service and FAQ documents
- Evaluation dataset for classification accuracy
- Reviewer-feedback loop for scoring improvements
- Docker deployment
- Production monitoring
- Automated model evaluation

---

## 26. Known Limitations

- The mock/fallback engine is rule-based and may be less accurate than Gemini for unusual wording.
- The response guardrail uses pattern-based checks and may not detect every possible paraphrase.
- The application is currently designed for local/single-user use.
- SQLite is not intended for heavy concurrent production workloads.
- Responses are drafted but not automatically sent.
- Scoring weights are currently expert-defined and are not learned from historical conversion data.
- Production deployment would require authentication, monitoring, stronger secret management and scalable infrastructure.

---

## 27. AI Usage Disclosure

AI tools were used as development assistants for coding, debugging, architecture discussion, testing and documentation.

The final application uses **Google Gemini API** as its runtime AI component.

The main architectural decision is:

> **LLM for language understanding and generation; Python for deterministic business decisions.**

The AI-generated code was locally installed, executed, tested and verified before submission.

See [`AI_USAGE.md`](AI_USAGE.md) for the detailed AI usage disclosure.

---

## 28. Demonstration

The project includes:

- `DEMO_SCRIPT.md` – demonstration flow
- `TECHNICAL_DOCUMENTATION.md` – detailed technical explanation
- `AI_USAGE.md` – AI usage disclosure

The recommended demonstration shows:

1. Project architecture
2. Live enquiry processing
3. AI classification
4. Lead scoring
5. Next Best Action
6. Response generation
7. Human-review decision
8. Database/history
9. Batch processing
10. REST API
11. Automated tests

---

## 29. Repository

GitHub:

https://github.com/sakthisree08/curdrice-business-studio-enquiry-automation

---

## 30. Conclusion

This project demonstrates a practical AI-powered business enquiry automation workflow where AI handles unstructured language while deterministic business rules control important decisions.

The system combines:

```text
AI Understanding
       +
Deterministic Business Logic
       +
Lead Intelligence
       +
Next Best Action
       +
Response Guardrails
       +
Human Approval
       +
Persistent Storage
       =
Reliable Enquiry Automation
```

The design focuses on practical business value rather than allowing the LLM to make uncontrolled business decisions.