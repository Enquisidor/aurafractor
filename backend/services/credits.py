"""
Credit system service.

Encapsulates all credit-related business logic:
  - Computing extraction costs
  - Deducting/refunding credits atomically
  - Enforcing limits per subscription tier
"""

import logging
from typing import Dict, Optional

from database.models import (
    deduct_credits,
    refund_credits,
    get_user_credits,
    list_credit_transactions,
    get_user_by_id,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Credit cost table
# ---------------------------------------------------------------------------

CREDIT_COSTS = {
    'basic': 5,           # Single source extraction
    'multi': 10,          # Multiple sources
    'complex': 20,        # Re-extraction / very complex
    'ambiguous': 1,       # Per ambiguous label surcharge
}

SUBSCRIPTION_LIMITS = {
    'free': 100,
    'pro': 500,
    'studio': None,  # Unlimited
}


def compute_extraction_cost(sources: list, is_reextraction: bool = False) -> Dict:
    """Calculate credit cost for an extraction request.

    Args:
        sources: List of source dicts with 'label' and optional 'ambiguous'.
        is_reextraction: Whether this is a re-extraction from feedback.

    Returns:
        Dict with total_cost, base_cost, ambiguity_cost, breakdown.
    """
    if is_reextraction:
        base_cost = CREDIT_COSTS['complex']
    elif len(sources) > 1:
        base_cost = CREDIT_COSTS['multi']
    else:
        base_cost = CREDIT_COSTS['basic']

    ambiguous_count = sum(1 for s in sources if s.get('ambiguous', False))
    ambiguity_cost = ambiguous_count * CREDIT_COSTS['ambiguous']
    total_cost = base_cost + ambiguity_cost

    return {
        'total_cost': total_cost,
        'base_cost': base_cost,
        'ambiguity_cost': ambiguity_cost,
        'ambiguous_labels': ambiguous_count,
    }


def check_sufficient_credits(user_id: str, required: int) -> bool:
    """Return True if the user can afford the given credit cost."""
    user = get_user_by_id(user_id)
    if user is None:
        return False
    if user['subscription_tier'] == 'studio':
        return True
    return user['credits_balance'] >= required


def charge_for_extraction(
    user_id: str,
    cost: int,
    extraction_id: Optional[str] = None,
    is_reextraction: bool = False,
) -> Dict:
    """Deduct credits for an extraction.

    Raises ValueError if insufficient credits.
    """
    reason = 're-extraction' if is_reextraction else 'extraction'
    logger.info('Charging %d credits to user %s for %s', cost, user_id[:8], reason)
    return deduct_credits(user_id, cost, reason, extraction_id)


def refund_for_failed_extraction(
    user_id: str,
    amount: int,
    extraction_id: Optional[str] = None,
) -> Dict:
    """Refund credits when an extraction fails after being charged."""
    logger.info('Refunding %d credits to user %s (failed extraction)', amount, user_id[:8])
    return refund_credits(user_id, amount, 'extraction failed - refund', extraction_id)


def get_credit_summary(user_id: str) -> Dict:
    """Return the full credit status for a user."""
    credits = get_user_credits(user_id)
    if credits is None:
        raise ValueError(f'User {user_id} not found')

    transactions = list_credit_transactions(user_id, limit=10)

    reset_date = credits.get('credits_reset_date')
    return {
        'current_balance': credits['credits_balance'],
        'monthly_allowance': credits['credits_monthly_allowance'],
        'subscription_tier': credits['subscription_tier'],
        'reset_date': reset_date.isoformat() if reset_date else None,
        'usage_this_month': {
            'extractions': credits.get('extractions_this_month', 0),
            'credits_spent': credits.get('credits_spent_this_month', 0),
        },
        'recent_transactions': [
            {
                'amount': t['amount'],
                'reason': t['reason'],
                'balance_after': t['balance_after'],
                'created_at': t['created_at'].isoformat(),
            }
            for t in transactions
        ],
    }
