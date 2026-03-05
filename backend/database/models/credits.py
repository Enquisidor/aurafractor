"""Credit transaction query helpers."""

import logging
from typing import Dict, List, Optional

from psycopg2.extras import RealDictCursor

from database.connection import db_transaction, execute_query

logger = logging.getLogger(__name__)


def get_user_credits(user_id: str) -> Optional[Dict]:
    """Return the user_credits_view row for a user."""
    return execute_query(
        "SELECT * FROM user_credits_view WHERE user_id = %s",
        (user_id,),
        fetch_one=True,
    )


def deduct_credits(
    user_id: str,
    amount: int,
    reason: str,
    extraction_id: Optional[str] = None,
) -> Dict:
    """Atomically deduct credits and log the transaction.

    Studio-tier users are never charged. Raises ValueError on insufficient balance.
    """
    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT credits_balance, subscription_tier FROM users "
                "WHERE user_id = %s AND deleted_at IS NULL FOR UPDATE",
                (user_id,),
            )
            user = cur.fetchone()
            if user is None:
                raise ValueError(f"User {user_id} not found")

            balance_before = user['credits_balance']

            if user['subscription_tier'] == 'studio':
                balance_after = balance_before  # Unlimited tier
            else:
                if balance_before < amount:
                    raise ValueError(
                        f"Insufficient credits: need {amount}, have {balance_before}"
                    )
                balance_after = balance_before - amount
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
                (user_id, extraction_id, -amount, reason, balance_before, balance_after),
            )
            return dict(cur.fetchone())


def refund_credits(
    user_id: str,
    amount: int,
    reason: str,
    extraction_id: Optional[str] = None,
) -> Dict:
    """Add credits back to a user (e.g. on extraction failure)."""
    with db_transaction() as conn:
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
            return dict(cur.fetchone())


def list_credit_transactions(user_id: str, limit: int = 50) -> List[Dict]:
    """Return the most recent credit transactions for a user."""
    return execute_query(
        "SELECT * FROM credit_transactions WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
        (user_id, limit),
    ) or []
