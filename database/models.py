"""
Database query helpers / "model" layer.

All SQL uses parameterized queries (%s placeholders via psycopg2).
Each function is focused on a single responsibility.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from psycopg2.extras import Json

from database.connection import db_connection, db_transaction, execute_query

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def create_user(device_id: str, app_version: Optional[str] = None) -> Dict:
    """Insert a new user record and return it."""
    sql = """
        INSERT INTO users (device_id, app_version, credits_reset_date)
        VALUES (%s, %s, (CURRENT_DATE + INTERVAL '1 month')::DATE)
        RETURNING *
    """
    with db_transaction() as conn:
        with conn.cursor() as cur:
            from psycopg2.extras import RealDictCursor
            conn.cursor_factory = None
            cur.close()
        with conn.cursor(cursor_factory=__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor) as cur:
            cur.execute(sql, (device_id, app_version))
            row = cur.fetchone()
            return dict(row)


def get_user_by_device_id(device_id: str) -> Optional[Dict]:
    """Look up a non-deleted user by device_id."""
    sql = """
        SELECT * FROM users
        WHERE device_id = %s AND deleted_at IS NULL
    """
    return execute_query(sql, (device_id,), fetch_one=True)


def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Look up a non-deleted user by user_id."""
    sql = """
        SELECT * FROM users
        WHERE user_id = %s AND deleted_at IS NULL
    """
    return execute_query(sql, (user_id,), fetch_one=True)


def update_user_last_active(user_id: str) -> None:
    """Touch last_active_at for the user."""
    sql = "UPDATE users SET last_active_at = CURRENT_TIMESTAMP WHERE user_id = %s"
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))


def soft_delete_user(user_id: str) -> Optional[Dict]:
    """Soft-delete a user (GDPR)."""
    sql = """
        UPDATE users
        SET deleted_at = CURRENT_TIMESTAMP
        WHERE user_id = %s AND deleted_at IS NULL
        RETURNING user_id, deleted_at
    """
    with db_transaction() as conn:
        with conn.cursor(__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor) as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

def create_session(user_id: str, session_token: str, refresh_token: str, expires_at: datetime) -> Dict:
    """Store a new session token pair."""
    sql = """
        INSERT INTO sessions (user_id, session_token, refresh_token, expires_at)
        VALUES (%s, %s, %s, %s)
        RETURNING *
    """
    with db_transaction() as conn:
        with conn.cursor(__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor) as cur:
            cur.execute(sql, (user_id, session_token, refresh_token, expires_at))
            row = cur.fetchone()
            return dict(row)


def get_session_by_token(session_token: str) -> Optional[Dict]:
    """Look up a session by its access token."""
    sql = """
        SELECT s.*, u.subscription_tier, u.credits_balance
        FROM sessions s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.session_token = %s AND s.expires_at > CURRENT_TIMESTAMP
          AND u.deleted_at IS NULL
    """
    return execute_query(sql, (session_token,), fetch_one=True)


def get_session_by_refresh_token(refresh_token: str) -> Optional[Dict]:
    """Look up a session by its refresh token."""
    sql = """
        SELECT s.*, u.subscription_tier
        FROM sessions s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.refresh_token = %s AND u.deleted_at IS NULL
    """
    return execute_query(sql, (refresh_token,), fetch_one=True)


def update_session_token(session_id: str, new_session_token: str, new_expires_at: datetime) -> None:
    """Replace session token on refresh."""
    sql = """
        UPDATE sessions
        SET session_token = %s, expires_at = %s
        WHERE session_id = %s
    """
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (new_session_token, new_expires_at, session_id))


def delete_expired_sessions() -> int:
    """Purge expired sessions. Returns count deleted."""
    sql = "DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP"
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.rowcount


# ---------------------------------------------------------------------------
# Tracks
# ---------------------------------------------------------------------------

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
) -> Dict:
    """Insert a track record."""
    sql = """
        INSERT INTO tracks
            (user_id, filename, duration_seconds, format, gcs_path,
             file_size_mb, sample_rate, genre_detected, tempo_detected, spectral_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    with db_transaction() as conn:
        with conn.cursor(__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor) as cur:
            cur.execute(sql, (
                user_id, filename, duration_seconds, format, gcs_path,
                file_size_mb, sample_rate, genre_detected, tempo_detected, spectral_hash,
            ))
            row = cur.fetchone()
            return dict(row)


def get_track(track_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
    """Fetch a track by ID (optionally scoped to a user)."""
    sql = "SELECT * FROM tracks WHERE track_id = %s AND deleted_at IS NULL"
    params: tuple = (track_id,)
    if user_id:
        sql += " AND user_id = %s"
        params = (track_id, user_id)
    return execute_query(sql, params, fetch_one=True)


def list_user_tracks(user_id: str, limit: int = 20, offset: int = 0) -> Tuple:
    """Return paginated tracks for a user with extraction summary."""
    count_sql = "SELECT COUNT(*) AS cnt FROM tracks WHERE user_id = %s AND deleted_at IS NULL"
    count_row = execute_query(count_sql, (user_id,), fetch_one=True)
    total = count_row['cnt'] if count_row else 0

    sql = """
        SELECT * FROM track_extraction_summary_view
        WHERE user_id = %s
        ORDER BY uploaded_at DESC
        LIMIT %s OFFSET %s
    """
    rows = execute_query(sql, (user_id, limit, offset))
    return total, rows or []


def soft_delete_track(track_id: str, user_id: str) -> Optional[Dict]:
    """Soft-delete a track (GDPR compliance)."""
    sql = """
        UPDATE tracks
        SET deleted_at = CURRENT_TIMESTAMP
        WHERE track_id = %s AND user_id = %s AND deleted_at IS NULL
        RETURNING track_id, deleted_at
    """
    with db_transaction() as conn:
        with conn.cursor(__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor) as cur:
            cur.execute(sql, (track_id, user_id))
            row = cur.fetchone()
            return dict(row) if row else None


# ---------------------------------------------------------------------------
# Extractions
# ---------------------------------------------------------------------------

def create_extraction(
    track_id: str,
    user_id: str,
    sources_requested: list,
    credit_cost: int,
    iteration_id: Optional[str] = None,
) -> Dict:
    """Insert an extraction record."""
    sql = """
        INSERT INTO extractions
            (track_id, user_id, sources_requested, credit_cost, iteration_id, status)
        VALUES (%s, %s, %s, %s, %s, 'queued')
        RETURNING *
    """
    with db_transaction() as conn:
        with conn.cursor(__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor) as cur:
            cur.execute(sql, (
                track_id, user_id, Json(sources_requested), credit_cost, iteration_id,
            ))
            row = cur.fetchone()
            return dict(row)


def get_extraction(extraction_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
    """Fetch an extraction (optionally scoped to a user)."""
    sql = "SELECT * FROM extractions WHERE extraction_id = %s"
    params: tuple = (extraction_id,)
    if user_id:
        sql += " AND user_id = %s"
        params = (extraction_id, user_id)
    return execute_query(sql, params, fetch_one=True)


def update_extraction_status(
    extraction_id: str,
    status: str,
    job_id: Optional[str] = None,
    processing_time_seconds: Optional[int] = None,
) -> Optional[Dict]:
    """Update extraction status, optionally setting job_id and timing."""
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
        with conn.cursor(__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None


def get_extraction_with_result(extraction_id: str) -> Optional[Dict]:
    """Fetch extraction together with its result."""
    sql = """
        SELECT e.*, er.sources AS result_sources, er.created_at AS result_created_at
        FROM extractions e
        LEFT JOIN extraction_results er ON e.extraction_id = er.extraction_id
        WHERE e.extraction_id = %s
    """
    return execute_query(sql, (extraction_id,), fetch_one=True)


def count_active_extractions() -> int:
    """Count extractions currently queued or processing."""
    sql = "SELECT COUNT(*) AS cnt FROM extractions WHERE status IN ('queued', 'processing')"
    row = execute_query(sql, fetch_one=True)
    return row['cnt'] if row else 0


def create_extraction_result(extraction_id: str, sources: list) -> Dict:
    """Store extraction result sources."""
    sql = """
        INSERT INTO extraction_results (extraction_id, sources)
        VALUES (%s, %s)
        ON CONFLICT (extraction_id) DO UPDATE SET sources = EXCLUDED.sources
        RETURNING *
    """
    with db_transaction() as conn:
        with conn.cursor(__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor) as cur:
            cur.execute(sql, (extraction_id, Json(sources)))
            row = cur.fetchone()
            return dict(row)


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

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
        with conn.cursor(__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor) as cur:
            cur.execute(sql, (
                extraction_id, user_id, track_id, segment_start_seconds,
                segment_end_seconds, segment_label, feedback_type,
                feedback_detail, refined_label, comment, reextraction_id,
            ))
            row = cur.fetchone()
            return dict(row)


def link_feedback_reextraction(feedback_id: str, reextraction_id: str) -> None:
    """Set the reextraction_id on an existing feedback record."""
    sql = "UPDATE feedback SET reextraction_id = %s WHERE feedback_id = %s"
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (reextraction_id, feedback_id))


# ---------------------------------------------------------------------------
# Credits
# ---------------------------------------------------------------------------

def get_user_credits(user_id: str) -> Optional[Dict]:
    """Return credits view row for the user."""
    sql = "SELECT * FROM user_credits_view WHERE user_id = %s"
    return execute_query(sql, (user_id,), fetch_one=True)


def deduct_credits(
    user_id: str,
    amount: int,
    reason: str,
    extraction_id: Optional[str] = None,
) -> Dict:
    """Atomically deduct credits and log the transaction.

    Raises ValueError if the user has insufficient credits.
    """
    with db_transaction() as conn:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Lock the user row
            cur.execute(
                "SELECT credits_balance, subscription_tier FROM users WHERE user_id = %s AND deleted_at IS NULL FOR UPDATE",
                (user_id,),
            )
            user = cur.fetchone()
            if user is None:
                raise ValueError(f"User {user_id} not found")

            if user['subscription_tier'] == 'studio':
                # Studio tier: unlimited (no deduction needed)
                balance_before = user['credits_balance']
                balance_after = balance_before
            else:
                balance_before = user['credits_balance']
                if balance_before < amount:
                    raise ValueError(f"Insufficient credits: need {amount}, have {balance_before}")
                balance_after = balance_before - amount
                cur.execute(
                    "UPDATE users SET credits_balance = %s WHERE user_id = %s",
                    (balance_after, user_id),
                )

            # Log transaction
            cur.execute(
                """
                INSERT INTO credit_transactions
                    (user_id, extraction_id, amount, reason, balance_before, balance_after)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (user_id, extraction_id, -amount, reason, balance_before, balance_after),
            )
            tx = cur.fetchone()
            return dict(tx)


def refund_credits(
    user_id: str,
    amount: int,
    reason: str,
    extraction_id: Optional[str] = None,
) -> Dict:
    """Add credits back to user (e.g. on extraction failure)."""
    with db_transaction() as conn:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT credits_balance FROM users WHERE user_id = %s FOR UPDATE",
                (user_id,),
            )
            user = cur.fetchone()
            if user is None:
                raise ValueError(f"User {user_id} not found")
            balance_before = user['credits_balance']
            balance_after = balance_before + amount
            cur.execute(
                "UPDATE users SET credits_balance = %s WHERE user_id = %s",
                (balance_after, user_id),
            )
            cur.execute(
                """
                INSERT INTO credit_transactions
                    (user_id, extraction_id, amount, reason, balance_before, balance_after)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (user_id, extraction_id, amount, reason, balance_before, balance_after),
            )
            tx = cur.fetchone()
            return dict(tx)


def list_credit_transactions(user_id: str, limit: int = 50) -> List[Dict]:
    """Return recent credit transactions for a user."""
    sql = """
        SELECT * FROM credit_transactions
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """
    return execute_query(sql, (user_id, limit)) or []


# ---------------------------------------------------------------------------
# Instrument suggestions cache
# ---------------------------------------------------------------------------

def get_suggestions_cache(track_id: str) -> Optional[Dict]:
    """Return non-expired cache entry for a track."""
    sql = """
        SELECT * FROM instrument_suggestions_cache
        WHERE track_id = %s AND expires_at > CURRENT_TIMESTAMP
    """
    return execute_query(sql, (track_id,), fetch_one=True)


def upsert_suggestions_cache(
    track_id: str,
    suggestions: list,
    genre: Optional[str],
    tempo: Optional[int],
    user_history_suggestions: Optional[list] = None,
    ttl_hours: int = 24,
) -> Dict:
    """Insert or update suggestion cache entry."""
    sql = """
        INSERT INTO instrument_suggestions_cache
            (track_id, suggestions, genre, tempo, user_history_suggestions, expires_at)
        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP + INTERVAL '%s hours')
        ON CONFLICT (track_id) DO UPDATE
        SET suggestions = EXCLUDED.suggestions,
            genre = EXCLUDED.genre,
            tempo = EXCLUDED.tempo,
            user_history_suggestions = EXCLUDED.user_history_suggestions,
            expires_at = EXCLUDED.expires_at
        RETURNING *
    """
    with db_transaction() as conn:
        with conn.cursor(__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor) as cur:
            cur.execute(sql, (
                track_id, Json(suggestions), genre, tempo,
                Json(user_history_suggestions) if user_history_suggestions else None,
                ttl_hours,
            ))
            row = cur.fetchone()
            return dict(row)


# ---------------------------------------------------------------------------
# Training data
# ---------------------------------------------------------------------------

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
        with conn.cursor(__import__('psycopg2.extras', fromlist=['RealDictCursor']).RealDictCursor) as cur:
            cur.execute(sql, (
                user_id_anon, original_label,
                Json(nlp_params) if nlp_params else None,
                feedback_type, feedback_detail, refined_label,
                user_accepted, genre, tempo, is_ambiguous, opt_in,
            ))
            row = cur.fetchone()
            return dict(row)


# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

from typing import Tuple  # noqa: E402 (used in list_user_tracks return hint)
