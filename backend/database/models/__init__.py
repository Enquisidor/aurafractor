"""
database.models — public re-export surface.

All callers use:
    from database.models import create_user, get_track, ...

This file keeps every import path stable regardless of which sub-module
holds the implementation.
"""

from database.models.users import (
    create_user,
    get_user_by_device_id,
    get_user_by_id,
    update_user_last_active,
    soft_delete_user,
)

from database.models.sessions import (
    create_session,
    get_session_by_token,
    get_session_by_refresh_token,
    update_session_token,
    delete_expired_sessions,
)

from database.models.tracks import (
    create_track,
    get_track,
    list_user_tracks,
    soft_delete_track,
)

from database.models.extractions import (
    create_extraction,
    get_extraction,
    get_extraction_with_result,
    update_extraction_status,
    count_active_extractions,
    create_extraction_result,
)

from database.models.feedback import (
    create_feedback,
    link_feedback_reextraction,
)

from database.models.credits import (
    get_user_credits,
    deduct_credits,
    refund_credits,
    list_credit_transactions,
)

from database.models.suggestions import (
    get_suggestions_cache,
    upsert_suggestions_cache,
)

from database.models.training import (
    insert_training_data,
)

__all__ = [
    # users
    'create_user', 'get_user_by_device_id', 'get_user_by_id',
    'update_user_last_active', 'soft_delete_user',
    # sessions
    'create_session', 'get_session_by_token', 'get_session_by_refresh_token',
    'update_session_token', 'delete_expired_sessions',
    # tracks
    'create_track', 'get_track', 'list_user_tracks', 'soft_delete_track',
    # extractions
    'create_extraction', 'get_extraction', 'get_extraction_with_result',
    'update_extraction_status', 'count_active_extractions', 'create_extraction_result',
    # feedback
    'create_feedback', 'link_feedback_reextraction',
    # credits
    'get_user_credits', 'deduct_credits', 'refund_credits', 'list_credit_transactions',
    # suggestions
    'get_suggestions_cache', 'upsert_suggestions_cache',
    # training
    'insert_training_data',
]
