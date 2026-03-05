"""Auth routes: register and token refresh."""

import os
from datetime import datetime

from flask import Blueprint, request, jsonify

from utils.decorators import handle_errors
from utils.validation import validate_device_id
from utils.monitoring import increment

bp = Blueprint('auth', __name__, url_prefix='/auth')
MOCK_MODE = os.getenv('ENABLE_MOCK_RESPONSES', 'false').lower() == 'true'


@bp.route('/register', methods=['POST'])
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
        return jsonify({
            'user_id': user_id,
            'session_token': session_token,
            'refresh_token': refresh_token,
            'expires_in': 86400,
            'subscription_tier': 'free',
            'credits_remaining': 100,
            'is_new_user': True,
            'timestamp': datetime.utcnow().isoformat(),
        }), 201

    from services.auth import register_or_login
    result = register_or_login(device_id, app_version)
    increment('auth.register')
    return jsonify(result), 201


@bp.route('/refresh', methods=['POST'])
@handle_errors
def refresh():
    """Exchange a refresh token for a new session token."""
    data = request.get_json(force=True) or {}
    refresh_token = data.get('refresh_token', '').strip()
    if not refresh_token:
        raise ValueError('refresh_token is required')

    from services.auth import refresh_session
    return jsonify(refresh_session(refresh_token))
