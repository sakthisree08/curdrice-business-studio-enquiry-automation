"""Reusable Streamlit display blocks (used by the New Enquiry page and the History page)."""
import pandas as pd
import streamlit as st

import config
from models.schemas import ProcessedEnquiry

PRIORITY_BADGE = {"High": "🟢 HIGH", "Medium": "🟡 MEDIUM", "Low": "⚪ LOW"}
URGENCY_BADGE = {"Critical": "🔴 Critical", "High": "🟠 High", "Medium": "🟡 Medium", "Low": "⚪ Low"}
MODE_LABEL = {
    "gemini": f"🤖 Live AI ({config.GEMINI_MODEL})",
    "mock": "🧪 Demo / mock mode (rule-based engine)",
    "fallback": "⚠️ AI failed - rule-based fallback used",
}


def mode_banner() -> None:
    if config.is_mock_mode():
        st.warning("🧪 **DEMO / MOCK MODE** - no OpenAI API key configured. Enquiries are analysed by the "
                   "built-in rule-based engine and replies use safe templates. Add `OPENAI_API_KEY` to `.env` "
                   "for live AI.", icon="🧪")
    else:
        st.success(f"🤖 **Live AI mode** - model `{config.GEMINI_MODEL}`", icon="🤖")


def show_value(value) -> str:
    return value if value not in (None, "") else "Not mentioned"


def render_human_review(result: ProcessedEnquiry) -> None:
    if result.human_review.required:
        reasons = "\n".join(f"- {reason}" for reason in result.human_review.reasons)
        st.error(f"### 🚩 HUMAN REVIEW REQUIRED\n{reasons}")
    else:
        st.success("✅ **No human review required.** Routine approval of the draft is still needed before sending.")


def render_result(result: ProcessedEnquiry) -> None:
    a, score, nba = result.analysis, result.lead_score, result.next_action

    ref = f"Enquiry #{result.id}" if result.id else "Enquiry (not saved)"
    st.caption(f"{ref} · {result.created_at} · source: {result.source} · {MODE_LABEL[result.processing_mode]} "
               f"· status: **{result.status}**")
    for warning in result.warnings:
        st.warning(warning)

    render_human_review(result)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Category", a.service_category)
    col2.metric("Lead score", f"{score.score}/100")
    col3.metric("Priority", PRIORITY_BADGE[score.priority])
    col4.metric("Next-action urgency", URGENCY_BADGE[nba.urgency])
    st.progress(score.score / 100)
    st.info(f"**Why this score:** {score.explanation}")

    tab_info, tab_score, tab_nba, tab_reply, tab_json = st.tabs(
        ["📋 Extracted information", "📊 Score breakdown", "🎯 Next best action", "✉️ Response draft", "🧾 Raw JSON"])

    with tab_info:
        rows = [("Customer name", a.customer_name), ("Company name", a.company_name), ("Email", a.email),
                ("Industry", a.industry), ("Requirement", a.requirement), ("Service category", a.service_category),
                ("Budget", a.budget), ("Expected timeline", a.timeline), ("Intent", a.intent),
                ("Sentiment", a.sentiment), ("Urgent", "Yes" if a.is_urgent else "No"),
                ("Asks for pricing", "Yes" if a.asks_for_pricing else "No"),
                ("Sensitive", "Yes" if a.is_sensitive else "No"), ("AI confidence", f"{a.confidence:.2f}"),
                ("Summary", a.summary)]
        st.table(pd.DataFrame([(k, show_value(v)) for k, v in rows], columns=["Field", "Value"]).set_index("Field"))

    with tab_score:
        st.dataframe(pd.DataFrame([f.model_dump() for f in score.factors])
                     .rename(columns={"name": "Factor", "points": "Points", "max_points": "Max", "reason": "Reason"}),
                     hide_index=True, width="stretch")
        st.caption(f"Priority thresholds: High ≥ {config.HIGH_PRIORITY_MIN_SCORE}, "
                   f"Medium ≥ {config.MEDIUM_PRIORITY_MIN_SCORE}, otherwise Low. Score computed by Python rules, not by the AI.")

    with tab_nba:
        st.markdown(f"**Recommended action:** {nba.action}")
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**Urgency:** {URGENCY_BADGE[nba.urgency]}")
        c2.markdown(f"**Internal response target:** {nba.respond_within}")
        c3.markdown(f"**Owner:** {nba.assigned_team}")
        st.markdown(f"**Why it matters:** {nba.why_it_matters}")
        st.markdown("**Missing information to collect:**")
        st.markdown("\n".join(f"- {m}" for m in nba.missing_information) or "- Nothing critical missing")
        st.caption("These questions are automatically included in the response draft.")

    with tab_reply:
        st.markdown(f"**Subject:** {result.response.subject}")
        st.text_area("Draft body", result.response.body, height=320, disabled=True,
                     key=f"draft_view_{result.id}_{result.created_at}")
        st.caption("📝 DRAFT ONLY - nothing is sent automatically. Approve, edit or reject it in *Enquiry History*.")
        if result.guardrail_violations:
            st.warning("The AI's draft broke business rules and was replaced by a safe template:\n"
                       + "\n".join(f"- {v}" for v in result.guardrail_violations))

    with tab_json:
        st.json(result.model_dump())
