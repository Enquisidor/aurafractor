"""Training data query helpers."""

import logging
from typing import Dict, Optional

from psycopg2.extras import RealDictCursor, Json

from database.connection import db_transaction

logger = logging.getLogger(__name__)


def insert_training_data(
    user_id_anon: str,
    original_label: str,
    nlp_params: Optional[dict],
    feedback_type: Optional[str],
    feedback_detail: Optional[str],
    refined_label: Optional[str],
    user_accepted: Optional[bool],
    genre: Optional[str],
    tempo: Optional[int],
    is_ambiguous: bool,
    opt_in: bool,
) -> Dict:
    """Store an anonymized training data point."""
    sql = """
        INSERT INTO training_data
            (user_id_anon, original_label, nlp_params, feedback_type,
             feedback_detail, refined_label, user_accepted, genre,
             tempo, is_ambiguous, opt_in)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (
                user_id_anon,
                original_label,
                Json(nlp_params) if nlp_params else None,
                feedback_type,
                feedback_detail,
                refined_label,
                user_accepted,
                genre,
                tempo,
                is_ambiguous,
                opt_in,
            ))
            return dict(cur.fetchone())
