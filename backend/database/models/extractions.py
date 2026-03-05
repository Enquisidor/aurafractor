"""Extraction query helpers."""

import logging
from typing import Dict, List, Optional

from psycopg2.extras import RealDictCursor, Json

from database.connection import db_transaction, execute_query

logger = logging.getLogger(__name__)


def create_extraction(
    track_id: str,
    user_id: str,
    sources_requested: list,
    credit_cost: int,
    iteration_id: Optional[str] = None,
) -> Dict:
    """Insert an extraction record with status='queued'."""
    sql = """
        INSERT INTO extractions
            (track_id, user_id, sources_requested, credit_cost, iteration_id, status)
        VALUES (%s, %s, %s, %s, %s, 'queued')
        RETURNING *
    """
    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (
                track_id, user_id, Json(sources_requested), credit_cost, iteration_id,
            ))
            return dict(cur.fetchone())


def get_extraction(extraction_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
    """Fetch an extraction, optionally scoped to a user."""
    sql = "SELECT * FROM extractions WHERE extraction_id = %s"
    params: tuple = (extraction_id,)
    if user_id:
        sql += " AND user_id = %s"
        params = (extraction_id, user_id)
    return execute_query(sql, params, fetch_one=True)


def get_extraction_with_result(extraction_id: str) -> Optional[Dict]:
    """Fetch an extraction joined with its result row."""
    sql = """
        SELECT e.*, er.sources AS result_sources, er.created_at AS result_created_at
        FROM extractions e
        LEFT JOIN extraction_results er ON e.extraction_id = er.extraction_id
        WHERE e.extraction_id = %s
    """
    return execute_query(sql, (extraction_id,), fetch_one=True)


def update_extraction_status(
    extraction_id: str,
    status: str,
    job_id: Optional[str] = None,
    processing_time_seconds: Optional[int] = None,
) -> Optional[Dict]:
    """Update extraction status; set timestamps and optional fields."""
    parts = ["status = %s"]
    params: list = [status]

    if status == 'processing':
        parts.append("started_at = CURRENT_TIMESTAMP")
    if status in ('completed', 'failed'):
        parts.append("completed_at = CURRENT_TIMESTAMP")
    if job_id is not None:
        parts.append("job_id = %s")
        params.append(job_id)
    if processing_time_seconds is not None:
        parts.append("processing_time_seconds = %s")
        params.append(processing_time_seconds)

    params.append(extraction_id)
    sql = f"UPDATE extractions SET {', '.join(parts)} WHERE extraction_id = %s RETURNING *"

    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None


def count_active_extractions() -> int:
    """Count extractions currently queued or processing."""
    row = execute_query(
        "SELECT COUNT(*) AS cnt FROM extractions WHERE status IN ('queued', 'processing')",
        fetch_one=True,
    )
    return row['cnt'] if row else 0


def create_extraction_result(extraction_id: str, sources: list) -> Dict:
    """Store (or replace) the result sources for an extraction."""
    sql = """
        INSERT INTO extraction_results (extraction_id, sources)
        VALUES (%s, %s)
        ON CONFLICT (extraction_id) DO UPDATE SET sources = EXCLUDED.sources
        RETURNING *
    """
    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (extraction_id, Json(sources)))
            return dict(cur.fetchone())
