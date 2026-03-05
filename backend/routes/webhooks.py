"""Internal routes: webhook callbacks and Cloud Tasks worker entry point."""

from flask import Blueprint, request, jsonify

from utils.decorators import worker_auth, handle_errors
from utils.validation import validate_uuid
from utils.monitoring import increment

bp = Blueprint('webhooks', __name__)


@bp.route('/webhooks/extraction-complete', methods=['POST'])
@worker_auth
@handle_errors
def extraction_complete():
    """Receive extraction result callback from a worker."""
    data = request.get_json(force=True) or {}
    extraction_id = validate_uuid(data.get('extraction_id'), 'extraction_id')
    success = bool(data.get('success', False))

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
def worker_extract():
    """Entry point invoked by Cloud Tasks to run an extraction job."""
    payload = request.get_json(force=True) or {}
    if not payload.get('extraction_id'):
        raise ValueError('extraction_id required')

    from workers.extraction_worker import run_extraction
    run_extraction(payload)
    return jsonify({'status': 'done', 'extraction_id': payload['extraction_id']})
