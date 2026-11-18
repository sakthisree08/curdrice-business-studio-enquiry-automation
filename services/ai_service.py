"""
AI integration layer - Google Gemini REST API.

call_llm_json() is the single place where the LLM is called.
It:
  1. requests a JSON object,
  2. parses the response defensively,
  3. validates it with Pydantic,
  4. retries once if the AI returns invalid JSON,
  5. converts API/network errors into AIServiceError,
  6. falls back to the rule-based engine if Gemini fails.
"""

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

import config
from models.schemas import EnquiryAnalysis
from services.mock_ai import mock_analyse

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)


class AIServiceError(Exception):
    """Any failure of the AI layer."""


def extract_json(raw: str) -> dict:
    """Parse a JSON object from model output."""

    text = (raw or "").strip()

    # Remove markdown code fences
    text = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    # Find JSON object if Gemini adds surrounding text
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end <= start:
        raise ValueError("no JSON object found in the AI response")

    data = json.loads(text[start:end + 1])

    if not isinstance(data, dict):
        raise ValueError("AI response JSON is not an object")

    return data


def _call_gemini(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
) -> str:
    """
    Call Gemini using the REST API.

    Uses urllib instead of google-genai because the installed
    HTTP client stack was causing connection issues.
    """

    api_key = config.GEMINI_API_KEY
    model = config.GEMINI_MODEL

    if not api_key:
        raise AIServiceError(
            "GEMINI_API_KEY is missing. Check the .env file."
        )

    if not model:
        raise AIServiceError(
            "GEMINI_MODEL is missing. Check the .env file."
        )

    url = (
        f"https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent?key={api_key}"
    )

    payload = {
        "systemInstruction": {
            "parts": [
                {
                    "text": system_prompt
                }
            ]
        },
        "contents": [
            {
                "parts": [
                    {
                        "text": user_prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
        },
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=config.GEMINI_TIMEOUT_SECONDS,
        ) as response:
            response_data = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        try:
            error_body = error.read().decode("utf-8")
        except Exception:
            error_body = ""

        if error.code in (401, 403):
            raise AIServiceError(
                "Gemini rejected the API key. Check GEMINI_API_KEY in .env."
            ) from error

        if error.code == 404:
            raise AIServiceError(
                f"Gemini model '{model}' was not found. "
                "Check GEMINI_MODEL in .env."
            ) from error

        if error.code == 429:
            raise AIServiceError(
                "Gemini rate limit or free-tier quota exceeded."
            ) from error

        if error.code == 503:
            raise AIServiceError(
                "Gemini service is temporarily unavailable (HTTP 503)."
            ) from error

        raise AIServiceError(
            f"Gemini API error HTTP {error.code}: {error_body[:300]}"
        ) from error

    except urllib.error.URLError as error:
        raise AIServiceError(
            f"Could not reach Gemini API: {error.reason}"
        ) from error

    except TimeoutError as error:
        raise AIServiceError(
            "Gemini API request timed out."
        ) from error

    except Exception as error:
        raise AIServiceError(
            f"Gemini connection error: {error.__class__.__name__}"
        ) from error

    try:
        return (
            response_data["candidates"][0]
            ["content"]["parts"][0]["text"]
        )
    except (KeyError, IndexError, TypeError) as error:
        raise AIServiceError(
            "Gemini returned an unexpected response format."
        ) from error

def _get_client():
    """
    Compatibility client for the existing reliability tests.

    The production application uses the Gemini REST API directly.
    """
    return None
def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    model_cls: Type[ModelT],
    temperature: float = 0.2,
    client=None,
) -> ModelT:
    """
    Call Gemini and validate the returned JSON with Pydantic.
    """

    last_error = None

    messages_user_prompt = user_prompt

    if client is None:
        client = _get_client()

    use_fake_client = client is not None

    for attempt in range(1, config.LLM_MAX_ATTEMPTS + 1):

        try:
            if use_fake_client:
                completion = client.chat.completions.create(
                    model=config.GEMINI_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": messages_user_prompt},
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                raw = completion.choices[0].message.content or ""
            else:
                raw = _call_gemini(
                    system_prompt=system_prompt,
                    user_prompt=messages_user_prompt,
                    temperature=temperature,
                )

            try:
                parsed = extract_json(raw)
                return model_cls.model_validate(parsed)

            except (ValueError, ValidationError) as error:

                last_error = error

                logger.warning(
                    "Invalid Gemini output (attempt %s): %s",
                    attempt,
                    error,
                )

                messages_user_prompt = (
                    user_prompt
                    + "\n\n"
                    + "Your previous response was invalid.\n"
                    + f"Validation error: {str(error)[:300]}\n"
                    + "Return ONLY a valid JSON object matching "
                    "the required schema."
                )

        except AIServiceError:
            raise

    raise AIServiceError(
        "Gemini returned invalid output after "
        f"{config.LLM_MAX_ATTEMPTS} attempts "
        f"({last_error})"
    )


ANALYSIS_SYSTEM_PROMPT = f"""
You are an enquiry analyst for {config.BUSINESS_PROFILE['name']}, a studio offering:

{", ".join(config.BUSINESS_PROFILE['services'])}

Analyse the customer enquiry and return ONLY a JSON object with exactly these keys:

{{
  "customer_name": string|null,
  "company_name": string|null,
  "email": string|null,
  "industry": string|null,
  "requirement": string|null,
  "service_category": one of {config.CATEGORIES},
  "budget": string|null,
  "timeline": string|null,
  "intent": one of [
      "buy_service",
      "information",
      "job_application",
      "partnership",
      "complaint",
      "other"
  ],
  "sentiment": one of [
      "positive",
      "neutral",
      "negative",
      "angry"
  ],
  "is_urgent": boolean,
  "asks_for_pricing": boolean,
  "is_sensitive": boolean,
  "confidence": number 0-1,
  "summary": string
}}

STRICT RULES:

- Extract ONLY what is explicitly written.
- If something is not mentioned, use null.
- Never guess names, emails, budgets or dates.
- Students asking for projects/internships/jobs -> "Internship / Job Application".
- Unhappy customers or service problems -> "Complaint / Support".
- Generic questions about services or pricing with no concrete requirement -> "General Enquiry".
- Use "Other" only when nothing fits, and lower the confidence.
"""


def analyse_enquiry(
    text: str,
) -> tuple[EnquiryAnalysis, str, list[str]]:
    """
    Returns:
        (analysis, processing_mode, warnings)

    Never raises for AI problems.
    """

    if config.is_mock_mode():
        return mock_analyse(text), "mock", []

    try:

        analysis = call_llm_json(
            ANALYSIS_SYSTEM_PROMPT,
            f'Customer enquiry:\n"""{text}"""',
            EnquiryAnalysis,
        )

        return analysis, "gemini", []

    except AIServiceError as error:

        logger.error(
            "Gemini analysis failed, using rule-based fallback: %s",
            error,
        )

        return (
            mock_analyse(text),
            "fallback",
            [
                f"AI analysis failed ({error}). "
                "The rule-based fallback engine was used."
            ],
        )