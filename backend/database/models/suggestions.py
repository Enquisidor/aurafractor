"""Instrument suggestions cache query helpers."""

import logging
from typing import Dict, Optional

from psycopg2.extras import RealDictCursor, Json

from database.connection import db_transaction, execute_query

logger = logging.getLogger(__name__)


def get_suggestions_cache(track_id: str) -> Optional[Dict]:
    """Return a non-expired cache entry for a track, or None."""
    return execute_query(
        "SELECT * FROM instrument_suggestions_cache "
        "WHERE track_id = %s AND expires_at > CURRENT_TIMESTAMP",
        (track_id,),
        fetch_one=True,
    )


def upsert_suggestions_cache(
    track_id: str,
    suggestions: list,
    genre: Optional[str],
    tempo: Optional[int],
    user_history_suggestions: Optional[list] = None,
    ttl_hours: int = 24,
) -> Dict:
    """Insert or update a suggestions cache entry."""
    sql = """
        INSERT INTO instrument_suggestions_cache
            (track_id, suggestions, genre, tempo, user_history_suggestions, expires_at)
        VALUES (%s, %s, %s, %s, %s,
                CURRENT_TIMESTAMP + CAST(%s || ' hours' AS INTERVAL))
        ON CONFLICT (track_id) DO UPDATE
        SET suggestions              = EXCLUDED.suggestions,
            genre                    = EXCLUDED.genre,
            tempo                    = EXCLUDED.tempo,
            user_history_suggestions = EXCLUDED.user_history_suggestions,
            expires_at               = EXCLUDED.expires_at
        RETURNING *
    """
    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (
                track_id,
                Json(suggestions),
                genre,
                tempo,
                Json(user_history_suggestions) if user_history_suggestions else None,
                str(ttl_hours),
            ))
            return dict(cur.fetchone())
