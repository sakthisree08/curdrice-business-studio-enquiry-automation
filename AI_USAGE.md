# AI Usage Disclosure

> **Note to self before submitting:** this file must be accurate. Edit any line below that does not match what you actually did, especially sections 3 and 4, and keep only statements you can defend in the interview.

## 1. AI tools used

| Tool | Used as |
|---|---|
| **Claude (Anthropic)** | Development assistant: architecture proposal, code generation, test generation, documentation drafting |
| **OpenAI API (`gpt-4o-mini`)** | A runtime component of the product (enquiry analysis and reply drafting). Not a development tool |

## 2. What the AI assistant was used for

- Proposing the project structure and the "LLM for language, Python for decisions" architecture.
- Generating the first version of the source code: the pipeline, services, Pydantic schemas, SQLite layer, Streamlit UI and FastAPI endpoints.
- Writing the regular expressions for the rule-based fallback engine and the response guardrail.
- Generating the `unittest` test suite, including the fake OpenAI client used to test invalid-JSON and failure handling.
- Drafting the README, technical documentation, demo script and this disclosure.

## 3. Parts generated or assisted by AI

Most of the initial code and documentation was **generated with AI assistance** from my written requirements and the company's assessment brief. I do not claim that it was written manually line by line.

## 4. Decisions I made / my own work

- I wrote the requirements specification the assistant worked from: stack (Python, Streamlit, OpenAI, SQLite, Pydantic), the rule that the LLM must not choose the score, mandatory human approval, a mock mode, and the need for the innovation to be practical rather than a gimmick.
- I chose the **Next Best Action** innovation direction.
- I reviewed the scoring weights and priority thresholds and confirmed that they match how I would prioritise these enquiries. *(Edit: note any weights or thresholds you changed.)*
- I installed and ran the project locally on Windows, tested it with all 12 sample enquiries in **[mock / live]** mode, and ran the automated tests. *(Edit: fill in what you actually did.)*
- I recorded the demonstration and can explain and modify every file.

## 5. Review and verification

- All 21 automated tests pass (`python -m unittest discover -s tests -v`).
- I manually checked every sample enquiry's category, score, review flag and draft against the business rules (no invented prices, dates or commitments).
- No API keys, confidential information or real customer data are included in the repository. The extra sample enquiries use fictional names.
