"""Internal routes: webhook callbacks and Cloud Tasks worker entry point."""

import os

from flask import Blueprint, request, jsonify

from utils.decorators import worker_auth, handle_errors
from utils.validation import validate_uuid
from utils.monitoring import increment

bp = Blueprint('webhooks', __name__)
MOCK_MODE = os.getenv('ENABLE_MOCK_RESPONSES', 'false').lower() == 'true'


@bp.route('/webhooks/extraction-complete', methods=['POST'])
@worker_auth
@handle_errors
def extraction_complete():
    """Receive extraction result callback from a worker."""
    data = request.get_json(force=True) or {}
    extraction_id = validate_uuid(data.get('extraction_id'), 'extraction_id')
    success = bool(data.get('success', False))

    # NOTE: handle_extraction_webhook makes DB calls. In mock mode (ENABLE_MOCK_RESPONSES=true)
    # there is no database, so this call will raise an exception if the DB is unavailable.
    # The @handle_errors decorator will catch the exception and return a 500. This is
    # intentional: the webhook should not silently swallow the call in any mode.
    # If running mock mode without a DB, ensure the DB is either available or stub
    # handle_extraction_webhook in integration tests.
    from services.extraction import handle_extraction_webhook
    handle_extraction_webhook(
        extraction_id=extraction_id,
        success=success,
        sources=data.get('sources') if success else None,
        error_message=data.get('error_message'),
        processing_time_seconds=data.get('processing_time_seconds'),
    )

    increment('webhooks.extraction.' + ('success' if success else 'failure'))
    return jsonify({'status': 'accepted'})


@bp.route('/worker/extract', methods=['POST'])
@worker_auth
@handle_errors
def worker_extract():  # pragma: no cover
    """Entry point invoked by Cloud Tasks to run an extraction job."""
    payload = request.get_json(force=True) or {}
    if not payload.get('extraction_id'):
        raise ValueError('extraction_id required')

    from workers.extraction_worker import run_extraction
    run_extraction(payload)
    return jsonify({'status': 'done', 'extraction_id': payload['extraction_id']})
