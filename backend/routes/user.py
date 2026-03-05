"""User routes: history, credits, track deletion."""

import os
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, g

from utils.decorators import require_auth, handle_errors
from utils.validation import validate_uuid, validate_pagination
from utils.monitoring import increment

bp = Blueprint('user', __name__)
MOCK_MODE = os.getenv('ENABLE_MOCK_RESPONSES', 'false').lower() == 'true'


@bp.route('/user/history', methods=['GET'])
@require_auth
@handle_errors
def user_history():
    """Paginated extraction history for the authenticated user."""
    limit, offset = validate_pagination(
        request.args.get('limit', 20),
        request.args.get('offset', 0),
    )
    user_id = g.user['user_id']

    if MOCK_MODE:
        import uuid
        return jsonify({
            'total_tracks': 1,
            'tracks': [{
                'track_id': str(uuid.uuid4()),
                'filename': 'song_1.mp3',
                'uploaded_at': (datetime.utcnow() - timedelta(days=1)).isoformat(),
                'extractions_count': 1,
                'latest_extraction': {'extraction_id': str(uuid.uuid4()), 'status': 'completed'},
            }],
            'pagination': {'limit': limit, 'offset': offset, 'has_more': False},
        })

    from database.models import list_user_tracks
    total, tracks = list_user_tracks(user_id, limit=limit, offset=offset)
    serialized = [
        {k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in t.items()}
        for t in tracks
    ]
    return jsonify({
        'total_tracks': total,
        'tracks': serialized,
        'pagination': {'limit': limit, 'offset': offset, 'has_more': offset + limit < total},
    })


@bp.route('/user/credits', methods=['GET'])
@require_auth
@handle_errors
def user_credits():
    """Return current credit balance and usage summary."""
    user_id = g.user['user_id']

    if MOCK_MODE:
        return jsonify({
            'current_balance': 50,
            'monthly_allowance': 100,
            'subscription_tier': 'free',
            'reset_date': (datetime.utcnow() + timedelta(days=25)).isoformat(),
            'usage_this_month': {'extractions': 8, 'credits_spent': 50},
            'recent_transactions': [],
        })

    from services.credits import get_credit_summary
    return jsonify(get_credit_summary(user_id))


@bp.route('/track/<track_id>', methods=['DELETE'])
@require_auth
@handle_errors
def delete_track(track_id):
    """Soft-delete a track and its GCS files (GDPR right to erasure)."""
    track_id = validate_uuid(track_id, 'track_id')
    user_id = g.user['user_id']

    if MOCK_MODE:
        return jsonify({
            'track_id': track_id,
            'deleted_at': datetime.utcnow().isoformat(),
            'files_deleted': 0,
            'feedback_anonymized': True,
        })

    from database.models import get_track, soft_delete_track
    from services.storage import delete_track_files

    track = get_track(track_id, user_id=user_id)
    if not track:
        raise ValueError(f'Track {track_id} not found')

    soft_delete_track(track_id, user_id)
    files_deleted = delete_track_files(track_id)
    increment('tracks.deleted')

    return jsonify({
        'track_id': track_id,
        'deleted_at': datetime.utcnow().isoformat(),
        'files_deleted': files_deleted,
        'feedback_anonymized': True,
    })
