"""
Streamlit UI - AI-Powered Business Enquiry Automation System.

Run:  streamlit run app.py
Pages: New Enquiry · Batch Upload (CSV) · Enquiry History & Approval · Dashboard
"""
import io
import json
import logging

import pandas as pd
import streamlit as st

import config
from database import database as db
from services.pipeline import process_enquiry
from ui import components as ui
from utils.validators import EnquiryValidationError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")

st.set_page_config(page_title="Enquiry Automation · Curd Rice Business Studio", page_icon="🍚", layout="wide")


@st.cache_data
def load_samples() -> list[dict]:
    try:
        return json.loads(config.SAMPLE_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        logger.error("Could not load sample enquiries: %s", error)
        return []


def run_pipeline(text: str, source: str):
    """Shared error handling for every page. Returns ProcessedEnquiry or None."""
    try:
        return process_enquiry(text, source=source)
    except EnquiryValidationError as error:
        st.warning(f"⚠️ {error}")
    except Exception:  # last line of defence - never show a raw traceback to the user
        logger.exception("Unexpected error while processing enquiry")
        st.error("Something unexpected went wrong while processing this enquiry. Details were written to the "
                 "terminal log. Please try again.")
    return None


# --------------------------------------------------------------------------
# Page 1: New enquiry
# --------------------------------------------------------------------------
def page_new_enquiry() -> None:
    st.header("📨 New Enquiry")
    samples = load_samples()
    options = {f"{s['id']} · {s['label']}": s["enquiry"] for s in samples}

    def load_selected_sample() -> None:
        st.session_state["enquiry_text"] = options.get(st.session_state["sample_choice"], "")

    col_sample, col_source = st.columns([3, 1])
    col_sample.selectbox("Load a sample enquiry (optional)", ["-"] + list(options), key="sample_choice",
                         on_change=load_selected_sample)
    source = col_source.selectbox("Channel", ["website", "email", "whatsapp", "phone", "other"])

    text = st.text_area("Customer enquiry", key="enquiry_text", height=140,
                        placeholder="e.g. We are a jewellery business looking for an AI-powered WhatsApp "
                                    "customer support system.")
    if st.button("🚀 Process enquiry", type="primary"):
        with st.spinner("Analysing enquiry, scoring lead and drafting a reply..."):
            result = run_pipeline(text, source)
        if result:
            st.session_state["last_result"] = result
            if result.id:
                st.toast(f"Saved as enquiry #{result.id}", icon="💾")

    if "last_result" in st.session_state:
        st.divider()
        ui.render_result(st.session_state["last_result"])


# --------------------------------------------------------------------------
# Page 2: Batch processing (CSV upload or all samples)
# --------------------------------------------------------------------------
def _find_text_column(frame: pd.DataFrame) -> str | None:
    for name in ("enquiry", "text", "message", "customer_enquiry", "inquiry"):
        for column in frame.columns:
            if str(column).strip().lower() == name:
                return column
    return None


def page_batch() -> None:
    st.header("📂 Batch Processing")
    st.write("Upload a CSV with an **enquiry** column (optional **source** column), "
             "or process all built-in sample enquiries at once.")
    uploaded = st.file_uploader("CSV file", type=["csv"])
    use_samples = st.button("Process all sample enquiries")

    frame = None
    if uploaded is not None:
        try:
            frame = pd.read_csv(uploaded)
        except Exception as error:  # pandas raises several parser error types
            st.error(f"Could not read the CSV file: {error}")
            return
    elif use_samples:
        frame = pd.DataFrame(load_samples())

    if frame is None:
        return
    text_column = _find_text_column(frame)
    if text_column is None:
        st.error("No enquiry column found. Name the column 'enquiry', 'text' or 'message'.")
        return
    if len(frame) > config.MAX_BATCH_ROWS:
        st.warning(f"Only the first {config.MAX_BATCH_ROWS} rows will be processed.")
        frame = frame.head(config.MAX_BATCH_ROWS)

    progress = st.progress(0.0, text="Processing...")
    rows, errors = [], []
    for index, record in enumerate(frame.to_dict("records"), start=1):
        source = str(record.get("source") or "csv")
        try:
            result = process_enquiry(str(record.get(text_column) or ""), source=source)
            rows.append({"id": result.id, "enquiry": result.enquiry_text, "category": result.analysis.service_category,
                         "score": result.lead_score.score, "priority": result.lead_score.priority,
                         "human_review": "YES" if result.human_review.required else "no",
                         "next_action": result.next_action.action, "mode": result.processing_mode})
        except EnquiryValidationError as error:
            errors.append(f"Row {index}: {error}")
        except Exception:
            logger.exception("Batch row %s failed", index)
            errors.append(f"Row {index}: unexpected error (see terminal log)")
        progress.progress(index / len(frame), text=f"Processed {index}/{len(frame)}")

    st.success(f"Processed {len(rows)} enquiries and saved them to the database.")
    for error in errors:
        st.warning(error)
    if rows:
        results = pd.DataFrame(rows)
        st.dataframe(results, hide_index=True, width="stretch")
        buffer = io.StringIO()
        results.to_csv(buffer, index=False)
        st.download_button("⬇️ Download results CSV", buffer.getvalue(), "processed_enquiries.csv", "text/csv")


# --------------------------------------------------------------------------
# Page 3: History + human approval
# --------------------------------------------------------------------------
def page_history() -> None:
    st.header("🗂️ Enquiry History & Approval")
    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))
    f1, f2, f3, f4 = st.columns(4)
    priority = f1.selectbox("Priority", ["All", "High", "Medium", "Low"])
    category = f2.selectbox("Category", ["All"] + config.CATEGORIES)
    status = f3.selectbox("Status", ["All", "Draft", "Approved", "Rejected"])
    review_only = f4.checkbox("Needs human review only")

    records = db.list_enquiries(priority=None if priority == "All" else priority,
                                category=None if category == "All" else category,
                                status=None if status == "All" else status, review_only=review_only)
    if not records:
        st.info("No enquiries found. Process one on the **New Enquiry** page.")
        return

    table = pd.DataFrame(records)
    table["human_review_required"] = table["human_review_required"].map({1: "🚩 YES", 0: "no"})
    st.dataframe(table, hide_index=True, width="stretch")

    selected_id = st.selectbox("Open enquiry", [r["id"] for r in records],
                               format_func=lambda i: f"#{i} · " + next(r["original_enquiry"][:70] for r in records if r["id"] == i))
    result = db.get_enquiry(selected_id)
    if result is None:
        st.error("This enquiry no longer exists.")
        return

    st.divider()
    ui.render_result(result)

    st.subheader("👤 Human approval")
    st.caption("The AI only prepares a draft. A person decides whether it is sent. Nothing is emailed by this system.")
    edited = st.text_area("Edit the reply before approving", result.response.body, height=260, key=f"edit_{selected_id}")
    notes = st.text_input("Reviewer notes", db.get_reviewer_notes(selected_id), key=f"notes_{selected_id}")
    b1, b2, b3 = st.columns(3)
    for button_col, new_status, label in ((b1, "Approved", "✅ Approve draft"), (b2, "Rejected", "❌ Reject"),
                                          (b3, "Draft", "↩️ Back to draft")):
        if button_col.button(label, key=f"{new_status}_{selected_id}"):
            db.update_status(selected_id, new_status, edited_response=edited, reviewer_notes=notes)
            st.session_state["flash"] = f"Enquiry #{selected_id} marked as {new_status}."
            st.rerun()


# --------------------------------------------------------------------------
# Page 4: Dashboard
# --------------------------------------------------------------------------
def page_dashboard() -> None:
    st.header("📊 Dashboard")
    stats = db.get_stats()
    if not stats["total"]:
        st.info("No data yet. Process some enquiries first (tip: Batch Processing → Process all sample enquiries).")
        return

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total enquiries", stats["total"])
    m2.metric("High-priority leads", stats["high"])
    m3.metric("Average lead score", stats["avg_score"])
    m4.metric("Awaiting human review", stats["pending_review"])
    m5.metric("Approved drafts", stats["approved"])

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Enquiries by category")
        st.bar_chart(pd.DataFrame(stats["by_category"]).set_index("category")["count"])
    with c2:
        st.subheader("Average lead score by category")
        st.bar_chart(pd.DataFrame(stats["by_category"]).set_index("category")["avg_score"])

    st.subheader("Priority distribution")
    priority = pd.DataFrame(stats["by_priority"]).set_index("priority").reindex(["High", "Medium", "Low"]).fillna(0)
    st.bar_chart(priority["count"], horizontal=True)

    st.subheader("🚩 Review queue (needs human attention, not yet actioned)")
    queue = db.list_enquiries(review_only=True, status="Draft")
    if queue:
        st.dataframe(pd.DataFrame(queue)[["id", "created_at", "category", "lead_score", "priority", "original_enquiry"]],
                     hide_index=True, width="stretch")
    else:
        st.success("Review queue is empty.")

    st.subheader("🔥 Top leads")
    leads = db.list_enquiries(priority="High", limit=10)
    if leads:
        st.dataframe(pd.DataFrame(leads)[["id", "lead_score", "category", "company_name", "original_enquiry"]],
                     hide_index=True, width="stretch")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
PAGES = {"📨 New Enquiry": page_new_enquiry, "📂 Batch Processing": page_batch,
         "🗂️ Enquiry History & Approval": page_history, "📊 Dashboard": page_dashboard}


def main() -> None:
    try:
        db.init_db()  # creates database/enquiries.db and the table automatically
    except db.DatabaseError as error:
        st.error(f"Database unavailable: {error}")
        st.stop()

    with st.sidebar:
        st.title("🍚 Curd Rice Business Studio")
        st.caption(config.BUSINESS_PROFILE["tagline"])
        page = st.radio("Navigate", list(PAGES))
        st.divider()
        st.caption("AI-Powered Business Enquiry Automation")
        st.caption("All replies are drafts. Nothing is sent automatically.")

    ui.mode_banner()
    try:
        PAGES[page]()
    except db.DatabaseError as error:
        st.error(f"Database error: {error}")


main()
