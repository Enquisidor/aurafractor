"""Session token query helpers."""

import logging
from datetime import datetime
from typing import Dict, Optional

from psycopg2.extras import RealDictCursor

from database.connection import db_transaction, execute_query

logger = logging.getLogger(__name__)


def create_session(
    user_id: str,
    session_token: str,
    refresh_token: str,
    expires_at: datetime,
) -> Dict:
    """Store a new session token pair."""
    sql = """
        INSERT INTO sessions (user_id, session_token, refresh_token, expires_at)
        VALUES (%s, %s, %s, %s)
        RETURNING *
    """
    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (user_id, session_token, refresh_token, expires_at))
            return dict(cur.fetchone())


def get_session_by_token(session_token: str) -> Optional[Dict]:
    """Look up a valid (non-expired) session by access token."""
    sql = """
        SELECT s.*, u.subscription_tier, u.credits_balance
        FROM sessions s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.session_token = %s
          AND s.expires_at > CURRENT_TIMESTAMP
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


def update_session_token(
    session_id: str,
    new_session_token: str,
    new_expires_at: datetime,
) -> None:
    """Replace the access token on refresh."""
    sql = "UPDATE sessions SET session_token = %s, expires_at = %s WHERE session_id = %s"
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
