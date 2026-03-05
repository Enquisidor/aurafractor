"""User query helpers."""

import logging
from typing import Dict, Optional

from psycopg2.extras import RealDictCursor

from database.connection import db_transaction, execute_query

logger = logging.getLogger(__name__)


def create_user(device_id: str, app_version: Optional[str] = None) -> Dict:
    """Insert a new user and return the full row."""
    sql = """
        INSERT INTO users (device_id, app_version, credits_reset_date)
        VALUES (%s, %s, (CURRENT_DATE + INTERVAL '1 month')::DATE)
        RETURNING *
    """
    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (device_id, app_version))
            return dict(cur.fetchone())


def get_user_by_device_id(device_id: str) -> Optional[Dict]:
    """Look up a non-deleted user by device_id."""
    sql = "SELECT * FROM users WHERE device_id = %s AND deleted_at IS NULL"
    return execute_query(sql, (device_id,), fetch_one=True)


def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Look up a non-deleted user by user_id."""
    sql = "SELECT * FROM users WHERE user_id = %s AND deleted_at IS NULL"
    return execute_query(sql, (user_id,), fetch_one=True)


def update_user_last_active(user_id: str) -> None:
    """Touch last_active_at."""
    sql = "UPDATE users SET last_active_at = CURRENT_TIMESTAMP WHERE user_id = %s"
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))


def soft_delete_user(user_id: str) -> Optional[Dict]:
    """Soft-delete a user (GDPR). Returns the deleted row or None."""
    sql = """
        UPDATE users
        SET deleted_at = CURRENT_TIMESTAMP
        WHERE user_id = %s AND deleted_at IS NULL
        RETURNING user_id, deleted_at
    """
    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None
