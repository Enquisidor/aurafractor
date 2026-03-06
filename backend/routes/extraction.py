"""Extraction routes: suggest labels, extract, poll status, feedback."""

import os
from datetime import datetime

from flask import Blueprint, request, jsonify, g

from utils.decorators import require_auth, handle_errors
from utils.rate_limiting import limiter
from utils.validation import validate_uuid, validate_sources, validate_feedback
from utils.monitoring import increment, Timer

bp = Blueprint('extraction', __name__, url_prefix='/extraction')
MOCK_MODE = os.getenv('ENABLE_MOCK_RESPONSES', 'false').lower() == 'true'


@bp.route('/suggest-labels', methods=['POST'])
@require_auth
@limiter.limit("60 per hour")
@handle_errors
def suggest_labels():
    """Return AI-suggested instrument labels for a track."""
    data = request.get_json(force=True) or {}
    track_id = validate_uuid(data.get('track_id'), 'track_id')
    user_id = g.user['user_id']

    if MOCK_MODE:
        return jsonify({
            'track_id': track_id,
            'suggested_labels': [
                {'label': 'lead vocals', 'confidence': 0.94, 'frequency_range': [85, 255], 'recommended': True},
                {'label': 'kick drum', 'confidence': 0.89, 'frequency_range': [20, 100], 'recommended': True},
                {'label': 'snare', 'confidence': 0.81, 'frequency_range': [100, 5000], 'recommended': False},
                {'label': 'bass', 'confidence': 0.76, 'frequency_range': [30, 250], 'recommended': True},
                {'label': 'synth pad', 'confidence': 0.68, 'frequency_range': [200, 8000], 'recommended': True},
            ],
            'genre': 'indie_rock',
            'tempo': 94,
            'user_history_suggestions': [],
        })

    from database.models import get_track, get_suggestions_cache, upsert_suggestions_cache
    from ml_models.classifier import classify_instruments, get_user_history_suggestions
    from services.storage import download_audio

    track = get_track(track_id, user_id=user_id)
    if not track:
        raise ValueError(f'Track {track_id} not found')

    cached = get_suggestions_cache(track_id)
    if cached:
        return jsonify({
            'track_id': track_id,
            'suggested_labels': cached['suggestions'],
            'genre': cached.get('genre'),
            'tempo': cached.get('tempo'),
            'user_history_suggestions': cached.get('user_history_suggestions') or [],
        })

    with Timer('classifier.latency_ms'):
        result = classify_instruments(download_audio(track['gcs_path']))

    history = get_user_history_suggestions(user_id)
    upsert_suggestions_cache(
        track_id=track_id,
        suggestions=result['suggestions'],
        genre=result.get('genre'),
        tempo=result.get('tempo'),
        user_history_suggestions=history,
    )
    return jsonify({
        'track_id': track_id,
        'suggested_labels': result['suggestions'],
        'genre': result.get('genre'),
        'tempo': result.get('tempo'),
        'user_history_suggestions': history,
    })


@bp.route('/extract', methods=['POST'])
@require_auth
@limiter.limit("20 per hour")
@handle_errors
def extract():
    """Initiate a source extraction job."""
    data = request.get_json(force=True) or {}
    track_id = validate_uuid(data.get('track_id'), 'track_id')
    sources = validate_sources(data.get('sources', []))
    force_ambiguous = bool(data.get('force_ambiguous', False))
    user_id = g.user['user_id']

    if MOCK_MODE:
        import uuid
        from services.nlp import compute_ambiguity_score
        ambiguous = [
            {'label': s['label'], 'ambiguity_score': compute_ambiguity_score(s['label'])}
            for s in sources if compute_ambiguity_score(s['label']) > 0.6
        ]
        base_cost = 10 if len(sources) > 1 else 5
        ambiguity_cost = len(ambiguous)
        cost = base_cost + ambiguity_cost
        extraction_id = str(uuid.uuid4())
        return jsonify({
            'extraction_id': extraction_id,
            'track_id': track_id,
            'job_id': f'mock-job-{extraction_id[:8]}',
            'status': 'queued',
            'sources_requested': len(sources),
            'models_used': list({s['model'] for s in sources}),
            'estimated_time_seconds': 120,
            'cost_credits': cost,
            'cost_breakdown': {'total_cost': cost, 'base_cost': base_cost, 'ambiguity_cost': ambiguity_cost},
            'ambiguous_labels': ambiguous,
            'queue_position': 1,
            'created_at': datetime.utcnow().isoformat(),
        }), 201

    from services.extraction import initiate_extraction
    with Timer('extraction.queue_latency_ms'):
        result = initiate_extraction(
            user_id=user_id,
            track_id=track_id,
            sources=sources,
            force_ambiguous=force_ambiguous,
        )

    if result.get('status') == 'awaiting_confirmation':
        return jsonify(result), 202

    increment('extractions.queued')
    return jsonify(result), 201


@bp.route('/<extraction_id>', methods=['GET'])
@require_auth
@limiter.limit("120 per minute")
@handle_errors
def get_status(extraction_id):
    """Poll extraction job status and results."""
    extraction_id = validate_uuid(extraction_id, 'extraction_id')
    user_id = g.user['user_id']

    if MOCK_MODE:
        import random
        status = random.choice(['queued', 'processing', 'completed'])
        response = {
            'extraction_id': extraction_id,
            'status': status,
            'created_at': datetime.utcnow().isoformat(),
            'started_at': datetime.utcnow().isoformat() if status != 'queued' else None,
            'completed_at': datetime.utcnow().isoformat() if status == 'completed' else None,
            'cost_credits': 5,
        }
        if status == 'completed':
            response['results'] = {'sources': [
                {'label': 'lead vocals', 'model_used': 'demucs', 'duration_seconds': 180,
                 'audio_url': f'https://storage.googleapis.com/mock/{extraction_id}/vocals.wav',
                 'waveform_url': f'https://storage.googleapis.com/mock/{extraction_id}/vocals_waveform.json'},
            ]}
        return jsonify(response)

    from services.extraction import get_extraction_status
    return jsonify(get_extraction_status(extraction_id, user_id))


@bp.route('/<extraction_id>/feedback', methods=['POST'])
@require_auth
@handle_errors
def submit_feedback(extraction_id):
    """Submit feedback on an extraction result."""
    extraction_id = validate_uuid(extraction_id, 'extraction_id')
    validated = validate_feedback(request.get_json(force=True) or {})
    user_id = g.user['user_id']

    if MOCK_MODE:
        import uuid
        reextraction_id = (
            str(uuid.uuid4())
            if validated['refined_label'] and validated['feedback_type'] != 'good'
            else None
        )
        return jsonify({
            'feedback_id': str(uuid.uuid4()),
            'extraction_id': extraction_id,
            'status': 'recorded' if validated['feedback_type'] == 'good' else 'queued_for_reextraction',
            'reextraction_queued': reextraction_id is not None,
            'new_extraction_id': reextraction_id,
            'cost_credits': 20 if reextraction_id else 0,
            'created_at': datetime.utcnow().isoformat(),
        }), 201

    from services.feedback import record_feedback
    result = record_feedback(extraction_id=extraction_id, user_id=user_id, **validated)
    increment('feedback.total')
    if result.get('reextraction_queued'):
        increment('extractions.requeued')
    return jsonify(result), 201
