"""
SQLite persistence (standard-library sqlite3, no ORM).

One table, `enquiries`:
  * flat columns for everything we filter, sort or chart on (category, score, priority, review ...)
  * `result_json` with the complete validated ProcessedEnquiry, so any record can be
    re-displayed exactly as it was produced.
The database file and table are created automatically on first use.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, Optional

import config
from models.schemas import ProcessedEnquiry


class DatabaseError(Exception):
    """Raised for any storage problem, with a user-readable message."""


SCHEMA = """
CREATE TABLE IF NOT EXISTS enquiries (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at             TEXT    NOT NULL,
    updated_at             TEXT    NOT NULL,
    source                 TEXT    NOT NULL DEFAULT 'form',
    original_enquiry       TEXT    NOT NULL,
    customer_name          TEXT,
    company_name           TEXT,
    email                  TEXT,
    requirement            TEXT,
    category               TEXT    NOT NULL,
    budget                 TEXT,
    timeline               TEXT,
    sentiment              TEXT,
    confidence             REAL,
    extracted_json         TEXT    NOT NULL,
    lead_score             INTEGER NOT NULL,
    priority               TEXT    NOT NULL,
    scoring_explanation    TEXT    NOT NULL,
    next_action            TEXT,
    response_subject       TEXT,
    response_draft         TEXT    NOT NULL,
    human_review_required  INTEGER NOT NULL,
    human_review_reason    TEXT,
    processing_mode        TEXT    NOT NULL,
    status                 TEXT    NOT NULL DEFAULT 'Draft',
    reviewer_notes         TEXT,
    result_json            TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_enquiries_priority ON enquiries(priority);
CREATE INDEX IF NOT EXISTS idx_enquiries_review   ON enquiries(human_review_required, status);
"""

LIST_COLUMNS = ("id, created_at, source, category, customer_name, company_name, lead_score, priority, "
                "human_review_required, status, processing_mode, original_enquiry")


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    try:
        config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(config.DB_PATH)
        connection.row_factory = sqlite3.Row
    except (sqlite3.Error, OSError) as error:
        raise DatabaseError(f"Cannot open database at {config.DB_PATH}: {error}") from error
    try:
        yield connection
        connection.commit()
    except sqlite3.Error as error:
        connection.rollback()
        raise DatabaseError(f"Database operation failed: {error}") from error
    finally:
        connection.close()


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)


def save_enquiry(result: ProcessedEnquiry) -> int:
    init_db()
    a, score, review, nba = result.analysis, result.lead_score, result.human_review, result.next_action
    row = {
        "created_at": result.created_at, "updated_at": result.created_at, "source": result.source,
        "original_enquiry": result.enquiry_text, "customer_name": a.customer_name,
        "company_name": a.company_name, "email": a.email, "requirement": a.requirement,
        "category": a.service_category, "budget": a.budget, "timeline": a.timeline,
        "sentiment": a.sentiment, "confidence": a.confidence,
        "extracted_json": a.model_dump_json(), "lead_score": score.score, "priority": score.priority,
        "scoring_explanation": score.explanation, "next_action": nba.action,
        "response_subject": result.response.subject, "response_draft": result.response.body,
        "human_review_required": int(review.required), "human_review_reason": "; ".join(review.reasons),
        "processing_mode": result.processing_mode, "status": result.status,
        "result_json": result.model_dump_json(),
    }
    columns = ", ".join(row)
    placeholders = ", ".join(f":{key}" for key in row)
    with _connect() as conn:
        cursor = conn.execute(f"INSERT INTO enquiries ({columns}) VALUES ({placeholders})", row)
        return int(cursor.lastrowid)


def list_enquiries(priority: Optional[str] = None, category: Optional[str] = None,
                   review_only: bool = False, status: Optional[str] = None, limit: int = 500) -> list[dict]:
    clauses, params = [], []
    if priority:
        clauses.append("priority = ?")
        params.append(priority)
    if category:
        clauses.append("category = ?")
        params.append(category)
    if status:
        clauses.append("status = ?")
        params.append(status)
    if review_only:
        clauses.append("human_review_required = 1")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with _connect() as conn:
        rows = conn.execute(f"SELECT {LIST_COLUMNS} FROM enquiries {where} ORDER BY id DESC LIMIT ?",
                            (*params, limit)).fetchall()
    return [dict(r) for r in rows]


def get_enquiry(enquiry_id: int) -> Optional[ProcessedEnquiry]:
    """Load one record as a ProcessedEnquiry (including any reviewer edits)."""
    with _connect() as conn:
        row = conn.execute("SELECT id, status, response_draft, result_json FROM enquiries WHERE id = ?",
                           (enquiry_id,)).fetchone()
    if row is None:
        return None
    result = ProcessedEnquiry.model_validate(json.loads(row["result_json"]))
    result.id, result.status = row["id"], row["status"]
    result.response.body = row["response_draft"]  # may have been edited by a reviewer
    return result


def get_reviewer_notes(enquiry_id: int) -> str:
    with _connect() as conn:
        row = conn.execute("SELECT reviewer_notes FROM enquiries WHERE id = ?", (enquiry_id,)).fetchone()
    return (row["reviewer_notes"] or "") if row else ""


def update_status(enquiry_id: int, status: str, edited_response: Optional[str] = None,
                  reviewer_notes: Optional[str] = None) -> bool:
    """Human approval step. Returns False if the enquiry does not exist."""
    sets, params = ["status = ?", "updated_at = ?"], [status, datetime.now().isoformat(timespec="seconds")]
    if edited_response is not None:
        sets.append("response_draft = ?")
        params.append(edited_response)
    if reviewer_notes is not None:
        sets.append("reviewer_notes = ?")
        params.append(reviewer_notes)
    with _connect() as conn:
        cursor = conn.execute(f"UPDATE enquiries SET {', '.join(sets)} WHERE id = ?", (*params, enquiry_id))
        return cursor.rowcount > 0


def get_stats() -> dict:
    with _connect() as conn:
        totals = conn.execute("""
            SELECT COUNT(*) AS total,
                   COALESCE(ROUND(AVG(lead_score), 1), 0) AS avg_score,
                   COALESCE(SUM(priority = 'High'), 0) AS high,
                   COALESCE(SUM(human_review_required = 1 AND status = 'Draft'), 0) AS pending_review,
                   COALESCE(SUM(status = 'Approved'), 0) AS approved
            FROM enquiries""").fetchone()
        by_category = conn.execute("""SELECT category, COUNT(*) AS count, ROUND(AVG(lead_score), 1) AS avg_score
                                      FROM enquiries GROUP BY category ORDER BY count DESC""").fetchall()
        by_priority = conn.execute("SELECT priority, COUNT(*) AS count FROM enquiries GROUP BY priority").fetchall()
    return {**dict(totals),
            "by_category": [dict(r) for r in by_category],
            "by_priority": [dict(r) for r in by_priority]}
