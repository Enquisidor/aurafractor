"""
Rate limiting configuration.

Uses Flask-Limiter with in-memory storage (suitable for single-instance dev/staging).
For multi-instance production, point RATELIMIT_STORAGE_URI at a Redis instance.

Limits are applied per-user for authenticated endpoints and per-IP for public ones.
The limiter instance is created here and registered via limiter.init_app(app) in
create_app(), so blueprints can import it directly.
"""

import logging

from flask import g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)


def _user_or_ip() -> str:
    """Key function: use authenticated user_id if available, else fall back to IP."""
    try:
        return g.user['user_id']
    except (AttributeError, KeyError):
        return get_remote_address()


# Single shared limiter.  init_app() is called in create_app().
limiter = Limiter(
    key_func=_user_or_ip,
    default_limits=["300 per hour", "60 per minute"],
    storage_uri="memory://",
)
