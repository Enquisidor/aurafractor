"""Track query helpers."""

import logging
from typing import Dict, List, Optional, Tuple

from psycopg2.extras import RealDictCursor

from database.connection import db_transaction, execute_query

logger = logging.getLogger(__name__)


def create_track(
    user_id: str,
    filename: str,
    duration_seconds: int,
    format: str,
    gcs_path: str,
    file_size_mb: float,
    sample_rate: int = 44100,
    genre_detected: Optional[str] = None,
    tempo_detected: Optional[int] = None,
    spectral_hash: Optional[str] = None,
    client_id: Optional[str] = None,
) -> Dict:
    """Insert a track record and return the full row.

    If *client_id* is provided and a track with the same (user_id, client_id)
    already exists, the existing row is returned unchanged (idempotent retry).
    """
    sql = """
        INSERT INTO tracks
            (user_id, filename, duration_seconds, format, gcs_path,
             file_size_mb, sample_rate, genre_detected, tempo_detected, spectral_hash,
             client_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, client_id) WHERE client_id IS NOT NULL
        DO UPDATE SET client_id = EXCLUDED.client_id
        RETURNING *
    """
    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (
                user_id, filename, duration_seconds, format, gcs_path,
                file_size_mb, sample_rate, genre_detected, tempo_detected, spectral_hash,
                client_id,
            ))
            return dict(cur.fetchone())


def get_track(track_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
    """Fetch a non-deleted track, optionally scoped to a user."""
    sql = "SELECT * FROM tracks WHERE track_id = %s AND deleted_at IS NULL"
    params: tuple = (track_id,)
    if user_id:
        sql += " AND user_id = %s"
        params = (track_id, user_id)
    return execute_query(sql, params, fetch_one=True)


def list_user_tracks(user_id: str, limit: int = 20, offset: int = 0) -> Tuple[int, List[Dict]]:
    """Return (total_count, page) of tracks for a user with extraction summary."""
    count_row = execute_query(
        "SELECT COUNT(*) AS cnt FROM tracks WHERE user_id = %s AND deleted_at IS NULL",
        (user_id,),
        fetch_one=True,
    )
    total = count_row['cnt'] if count_row else 0

    rows = execute_query(
        """
        SELECT * FROM track_extraction_summary_view
        WHERE user_id = %s
        ORDER BY uploaded_at DESC
        LIMIT %s OFFSET %s
        """,
        (user_id, limit, offset),
    )
    return total, rows or []


def soft_delete_track(track_id: str, user_id: str) -> Optional[Dict]:
    """Soft-delete a track (GDPR). Returns the deleted row or None."""
    sql = """
        UPDATE tracks
        SET deleted_at = CURRENT_TIMESTAMP
        WHERE track_id = %s AND user_id = %s AND deleted_at IS NULL
        RETURNING track_id, deleted_at
    """
    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (track_id, user_id))
            row = cur.fetchone()
            return dict(row) if row else None
