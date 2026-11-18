"""
Central configuration.

Everything that a business user might want to tune lives here:
environment variables, the business profile, the business rules,
service categories, scoring thresholds and human-review thresholds.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# --------------------------------------------------------------------------
# Environment / AI settings (never hard-code the API key)
# --------------------------------------------------------------------------
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
GEMINI_TIMEOUT_SECONDS: float = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "30"))

FORCE_MOCK_MODE: bool = os.getenv("FORCE_MOCK_MODE", "false").strip().lower() in (
    "1", "true", "yes"
)

LLM_MAX_ATTEMPTS: int = 2

DB_PATH: Path = Path(os.getenv("DB_PATH", str(BASE_DIR / "database" / "enquiries.db")))
SAMPLE_DATA_PATH: Path = BASE_DIR / "data" / "sample_enquiries.json"


def is_mock_mode() -> bool:
    """Mock/demo mode is used when no Gemini API key is configured or it is forced."""
    placeholder = not GEMINI_API_KEY or GEMINI_API_KEY.startswith("your")
    return FORCE_MOCK_MODE or placeholder


# --------------------------------------------------------------------------
# Business information (taken from the assessment brief)
# --------------------------------------------------------------------------
BUSINESS_PROFILE = {
    "name": "Curd Rice Business Studio",
    "tagline": "Business Intelligence · Operational Systems · AI Automation",
    "description": (
        "Curd Rice Business Studio helps businesses improve their operations, "
        "make better decisions and implement technology-driven solutions."
    ),
    "services": [
        "Business Consulting",
        "AI Automation",
        "Website Development",
        "Application Development",
        "Branding",
        "Digital Marketing",
        "Business Intelligence",
        "Operational Systems",
    ],
}

BUSINESS_RULES = [
    "Never invent service pricing, quotes, discounts or cost estimates.",
    "Never guarantee or promise project delivery dates or timeframes.",
    "Never make commitments on behalf of the business.",
    "Never claim services, clients, awards or facts not listed in the business profile.",
    "Escalate unclear or sensitive enquiries for human review.",
    "All generated responses remain drafts until a human approves them.",
]

# --------------------------------------------------------------------------
# Service categories
# To add a category: add ONE entry here. Nothing else needs to change.
#   value_points        -> 0-12 points used by the lead-scoring "project value" factor
#   is_sales            -> True if this is a potential paying-client enquiry
#   discovery_questions -> category-specific questions used by Next Best Action
# --------------------------------------------------------------------------
CATEGORY_PROFILES: dict[str, dict] = {
    "Business Consulting": {
        "value_points": 8, "is_sales": True,
        "discovery_questions": ["What is the main business challenge you want to solve?"],
    },
    "AI Automation": {
        "value_points": 12, "is_sales": True,
        "discovery_questions": [
            "Which channels or tools do you currently use for this process?",
            "Roughly how many requests/transactions does this process handle per day?",
        ],
    },
    "Website Development": {
        "value_points": 8, "is_sales": True,
        "discovery_questions": [
            "What key pages or features should the website have?",
            "Do you already have a domain, hosting or an existing website?",
        ],
    },
    "Application Development": {
        "value_points": 12, "is_sales": True,
        "discovery_questions": [
            "Which platforms do you need (Android, iOS, web)?",
            "Who will use the application and roughly how many users?",
        ],
    },
    "Branding": {
        "value_points": 6, "is_sales": True,
        "discovery_questions": ["Is this a new brand or a refresh of an existing one?"],
    },
    "Digital Marketing": {
        "value_points": 6, "is_sales": True,
        "discovery_questions": ["Who is your target audience and which channels matter most?"],
    },
    "Business Intelligence": {
        "value_points": 12, "is_sales": True,
        "discovery_questions": [
            "Which data sources do you use today (Excel, ERP, CRM, etc.)?",
            "Which decisions or metrics should the dashboards support?",
        ],
    },
    "Operational Systems": {
        "value_points": 12, "is_sales": True,
        "discovery_questions": [
            "How is this process managed today (manual, Excel, existing software)?",
            "How many users, locations or warehouses are involved?",
        ],
    },
    "Internship / Job Application": {
        "value_points": 0, "is_sales": False,
        "discovery_questions": ["Could you share your CV and your availability?"],
    },
    "General Enquiry": {
        "value_points": 3, "is_sales": False,
        "discovery_questions": [
            "What would you like to achieve for your business?",
            "What industry is your business in?",
        ],
    },
    "Complaint / Support": {
        "value_points": 0, "is_sales": False,
        "discovery_questions": [
            "Could you share your project or order reference?",
            "What is the best phone number and time to reach you?",
        ],
    },
    "Partnership": {
        "value_points": 5, "is_sales": False,
        "discovery_questions": ["Could you share a short overview of the partnership you have in mind?"],
    },
    "Other": {
        "value_points": 2, "is_sales": False,
        "discovery_questions": ["Could you tell us a little more about what you are looking for?"],
    },
}
CATEGORIES: list[str] = list(CATEGORY_PROFILES.keys())

# --------------------------------------------------------------------------
# Thresholds
# --------------------------------------------------------------------------
HIGH_PRIORITY_MIN_SCORE = 70
MEDIUM_PRIORITY_MIN_SCORE = 40
REVIEW_CONFIDENCE_THRESHOLD = 0.6  # below this the AI is "not sure" -> human review

MIN_ENQUIRY_CHARS = 8
MAX_ENQUIRY_CHARS = 5000
MAX_BATCH_ROWS = 200
