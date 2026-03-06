"""Feedback query helpers."""

import logging
from typing import Dict, Optional

from psycopg2.extras import RealDictCursor

from database.connection import db_transaction

logger = logging.getLogger(__name__)


def create_feedback(
    extraction_id: str,
    user_id: str,
    track_id: str,
    segment_start_seconds: int,
    segment_end_seconds: int,
    segment_label: str,
    feedback_type: str,
    feedback_detail: Optional[str] = None,
    refined_label: Optional[str] = None,
    comment: Optional[str] = None,
    reextraction_id: Optional[str] = None,
) -> Dict:
    """Record user feedback for an extraction segment."""
    sql = """
        INSERT INTO feedback
            (extraction_id, user_id, track_id, segment_start_seconds,
             segment_end_seconds, segment_label, feedback_type,
             feedback_detail, refined_label, comment, reextraction_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (
                extraction_id, user_id, track_id,
                segment_start_seconds, segment_end_seconds,
                segment_label, feedback_type, feedback_detail,
                refined_label, comment, reextraction_id,
            ))
            return dict(cur.fetchone())


def link_feedback_reextraction(feedback_id: str, reextraction_id: str) -> None:
    """Attach a re-extraction ID to an existing feedback row."""
    sql = "UPDATE feedback SET reextraction_id = %s WHERE feedback_id = %s"
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (reextraction_id, feedback_id))
