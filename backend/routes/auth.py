"""Auth routes: register and token refresh."""

import os
from datetime import datetime

from flask import Blueprint, request, jsonify

from utils.decorators import handle_errors
from utils.rate_limiting import limiter
from utils.validation import validate_device_id
from utils.monitoring import increment

bp = Blueprint('auth', __name__, url_prefix='/auth')
MOCK_MODE = os.getenv('ENABLE_MOCK_RESPONSES', 'false').lower() == 'true'

# Comma-separated device IDs that receive Studio tier (unlimited credits).
# Set DEV_DEVICE_IDS in your .env to your own device ID after first login.
_DEV_DEVICE_IDS: set = {
    d.strip() for d in os.getenv('DEV_DEVICE_IDS', '').split(',') if d.strip()
}


def _tier_for_device(device_id: str) -> str:
    return 'studio' if device_id in _DEV_DEVICE_IDS else 'free'


@bp.route('/register', methods=['POST'])
@limiter.limit("10 per minute")
@handle_errors
def register():
    """Register or log in an anonymous user by device_id."""
    data = request.get_json(force=True) or {}
    device_id = validate_device_id(data.get('device_id'))
    app_version = data.get('app_version')

    if MOCK_MODE:
        import uuid
        from services.auth import generate_session_token, generate_refresh_token
        user_id = str(uuid.uuid4())
        session_token, _ = generate_session_token(user_id)
        refresh_token = generate_refresh_token(user_id)
        tier = _tier_for_device(device_id)
        credits_remaining = None if tier == 'studio' else 100
        return jsonify({
            'user_id': user_id,
            'session_token': session_token,
            'refresh_token': refresh_token,
            'expires_in': 86400,
            'subscription_tier': tier,
            'credits_remaining': credits_remaining,
            'is_new_user': True,
            'timestamp': datetime.utcnow().isoformat(),
        }), 201

    if not MOCK_MODE:  # pragma: no cover
        from services.auth import register_or_login
        result = register_or_login(device_id, app_version)
        increment('auth.register')
        return jsonify(result), 201


@bp.route('/refresh', methods=['POST'])
@limiter.limit("20 per minute")
@handle_errors
def refresh():
    """Exchange a refresh token for a new session token."""
    data = request.get_json(force=True) or {}
    refresh_token = data.get('refresh_token', '').strip()
    if not refresh_token:
        raise ValueError('refresh_token is required')

    if MOCK_MODE:
        import jwt as _jwt
        from services.auth import generate_session_token
        try:
            payload = _jwt.decode(
                refresh_token,
                os.getenv('JWT_SECRET', 'dev-secret'),
                algorithms=['HS256'],
            )
            if payload.get('type') != 'refresh':
                raise ValueError('Not a refresh token')
            user_id = payload['user_id']
        except _jwt.ExpiredSignatureError:
            raise ValueError('Refresh token expired')
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f'Invalid refresh token: {exc}')
        token, _ = generate_session_token(user_id)
        return jsonify({'session_token': token, 'expires_in': 86400})

    if not MOCK_MODE:  # pragma: no cover
        from services.auth import refresh_session
        return jsonify(refresh_session(refresh_token))
