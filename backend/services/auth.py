"""
Authentication service.

Handles user registration, JWT generation/verification, and token refresh.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import jwt

from database.models import (
    create_user,
    get_user_by_device_id,
    get_user_by_id,
    get_session_by_token,
    get_session_by_refresh_token,
    create_session,
    update_session_token,
    update_user_last_active,
)

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret')
JWT_ALGORITHM = 'HS256'
SESSION_TTL_HOURS = 24
REFRESH_TTL_DAYS = 30


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _generate_token(user_id: str, token_type: str, expires_delta: timedelta) -> str:
    """Create a signed JWT."""
    payload = {
        'user_id': user_id,
        'type': token_type,
        'exp': datetime.utcnow() + expires_delta,
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def generate_session_token(user_id: str) -> Tuple[str, datetime]:
    """Return (session_token, expires_at)."""
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)
    token = _generate_token(user_id, 'session', timedelta(hours=SESSION_TTL_HOURS))
    return token, expires_at


def generate_refresh_token(user_id: str) -> str:
    """Return a long-lived refresh token."""
    return _generate_token(user_id, 'refresh', timedelta(days=REFRESH_TTL_DAYS))


def verify_session_token(token: str) -> Optional[str]:
    """Decode a session JWT.

    Returns user_id on success, None on any error.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get('type') != 'session':
            return None
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        logger.debug('Session token expired')
        return None
    except Exception as exc:
        logger.debug('Token verify failed: %s', exc)
        return None


# ---------------------------------------------------------------------------
# Registration / login
# ---------------------------------------------------------------------------

def register_or_login(device_id: str, app_version: Optional[str] = None) -> Dict:
    """Register a new user or return existing session.

    Returns the full auth response payload.
    """
    # Check if user already exists
    user = get_user_by_device_id(device_id)
    if user is None:
        logger.info('Registering new user device_id=%s', device_id[:8])
        user = create_user(device_id, app_version)
        is_new = True
    else:
        logger.info('Login existing user user_id=%s', str(user['user_id'])[:8])
        is_new = False

    user_id = str(user['user_id'])

    session_token, expires_at = generate_session_token(user_id)
    refresh_token = generate_refresh_token(user_id)

    create_session(user_id, session_token, refresh_token, expires_at)
    update_user_last_active(user_id)

    return {
        'user_id': user_id,
        'session_token': session_token,
        'refresh_token': refresh_token,
        'expires_in': SESSION_TTL_HOURS * 3600,
        'subscription_tier': user['subscription_tier'],
        'credits_remaining': user['credits_balance'],
        'is_new_user': is_new,
        'timestamp': datetime.utcnow().isoformat(),
    }


def refresh_session(refresh_token_str: str) -> Dict:
    """Issue a new session token from a valid refresh token.

    Raises ValueError on invalid/expired refresh token.
    """
    try:
        payload = jwt.decode(refresh_token_str, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get('type') != 'refresh':
            raise ValueError('Not a refresh token')
        user_id = payload['user_id']
    except jwt.ExpiredSignatureError:
        raise ValueError('Refresh token expired')
    except Exception as exc:
        raise ValueError(f'Invalid refresh token: {exc}')

    # Validate refresh token is in DB
    session = get_session_by_refresh_token(refresh_token_str)
    if session is None:
        raise ValueError('Refresh token not recognised')

    new_session_token, new_expires_at = generate_session_token(user_id)
    update_session_token(str(session['session_id']), new_session_token, new_expires_at)
    update_user_last_active(user_id)

    return {
        'session_token': new_session_token,
        'expires_in': SESSION_TTL_HOURS * 3600,
    }


def get_authenticated_user(session_token: str) -> Optional[Dict]:
    """Validate session token and return user record.

    Returns None if token is invalid or user not found.
    """
    session = get_session_by_token(session_token)
    if session is None:
        return None
    user = get_user_by_id(str(session['user_id']))
    if user:
        update_user_last_active(str(user['user_id']))
    return user
