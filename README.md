# AI-Powered Business Enquiry Automation System

An AI-powered system developed for **Curd Rice Business Studio** to automate customer enquiry analysis, lead prioritization, response generation, and human review.

## Features

- AI-based enquiry classification using **Google Gemini**
- Structured information extraction using **Pydantic**
- Deterministic **lead scoring (0–100)**
- **High / Medium / Low** priority classification
- Next Best Action recommendation
- AI-generated response drafts
- Response safety and grounding checks
- Human approval workflow
- SQLite database storage
- Streamlit web interface
- FastAPI REST API
- Batch enquiry processing
- Mock/fallback mode for AI failures
- Automated test suite

## Workflow

```text
Customer Enquiry
       ↓
Input Validation
       ↓
Gemini AI Analysis
       ↓
Pydantic Validation
       ↓
Grounding Check
       ↓
Lead Scoring
       ↓
Next Best Action
       ↓
Response Generation
       ↓
Safety Check
       ↓
Human Review
       ↓
SQLite Storage
```

## Technology Stack

- **Python**
- **Google Gemini API**
- **Streamlit**
- **FastAPI**
- **Pydantic**
- **SQLite**
- **Pytest**

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

For the REST API:

```bash
uvicorn api:app --reload
```

Configure the Gemini API key in `.env`:

```env
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
```

## Lead Scoring

The score is calculated using:

**Intent + Clarity + Business Information + Budget + Timeline + Business Value**

- **70–100:** High
- **40–69:** Medium
- **0–39:** Low

The score is calculated using deterministic Python logic rather than allowing the LLM to make the final business decision.

## Reliability

The system includes:

- Input validation
- Structured AI output validation
- Retry handling
- Gemini failure fallback
- Response guardrails
- Human review for sensitive or uncertain enquiries
- Database error handling

## Testing

The project includes automated tests covering validation, scoring, AI handling, pipeline processing, and error cases.

```bash
pytest
```

