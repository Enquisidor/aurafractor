"""
Reusable Flask decorators.

@require_auth  - Verifies JWT and loads current user
@worker_auth   - Validates internal worker secret
"""

import logging
import os
from functools import wraps
from typing import Callable

from flask import request, jsonify, g

logger = logging.getLogger(__name__)

WORKER_SECRET = os.getenv('WORKER_SECRET', 'worker-secret')
MOCK_MODE = os.getenv('ENABLE_MOCK_RESPONSES', 'false').lower() == 'true'


def _error(message: str, status: int):
    return jsonify({'error': message}), status


def require_auth(f: Callable) -> Callable:
    """Decorator: verify Bearer JWT and set g.user (the full user dict)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return _error('Unauthorized: missing Bearer token', 401)

        token = auth_header[len('Bearer '):]

        if MOCK_MODE:
            # In mock mode, accept any token but validate X-User-ID header
            user_id = request.headers.get('X-User-ID', '')
            if not user_id:
                return _error('Unauthorized: missing X-User-ID header in mock mode', 401)
            try:
                import uuid
                uuid.UUID(user_id)
            except ValueError:
                return _error('Unauthorized: invalid X-User-ID format', 401)
            g.user = {'user_id': user_id, 'subscription_tier': 'free', 'credits_balance': 100}
            return f(*args, **kwargs)

        # Production: validate against DB session
        try:
            from services.auth import get_authenticated_user
            user = get_authenticated_user(token)
            if user is None:
                return _error('Unauthorized: invalid or expired token', 401)
            g.user = user
            return f(*args, **kwargs)
        except Exception as exc:
            logger.error('Auth error: %s', exc)
            return _error('Unauthorized', 401)

    return decorated


def worker_auth(f: Callable) -> Callable:
    """Decorator: validate X-Worker-Secret header for internal worker calls."""
    @wraps(f)
    def decorated(*args, **kwargs):
        secret = request.headers.get('X-Worker-Secret', '')
        if secret != WORKER_SECRET:
            return _error('Forbidden: invalid worker secret', 403)
        return f(*args, **kwargs)
    return decorated


def handle_errors(f: Callable) -> Callable:
    """Decorator: catch ValueError (user-facing) and unexpected exceptions."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as exc:
            return _error(str(exc), 400)
        except PermissionError as exc:
            return _error(str(exc), 403)
        except Exception as exc:
            logger.error('Unhandled exception in %s: %s', f.__name__, exc, exc_info=True)
            return _error('Internal server error', 500)
    return decorated
