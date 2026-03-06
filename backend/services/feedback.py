"""
Feedback service.

Records user feedback on extraction results and optionally triggers
re-extraction. Also writes anonymized training data if user opted in.
"""

import logging
from typing import Dict, Optional

from database.models import (
    create_feedback,
    get_extraction,
    get_track,
    get_user_by_id,
    insert_training_data,
)
from services.credits import compute_extraction_cost, charge_for_extraction
from services.nlp import parse_label_to_params, build_training_point
from services.tasks import enqueue_reextraction_job
from database.models import create_extraction

logger = logging.getLogger(__name__)


def record_feedback(
    extraction_id: str,
    user_id: str,
    segment_start_seconds: int,
    segment_end_seconds: int,
    segment_label: str,
    feedback_type: str,
    feedback_detail: Optional[str] = None,
    refined_label: Optional[str] = None,
    comment: Optional[str] = None,
) -> Dict:
    """Record feedback and optionally queue re-extraction.

    Returns the feedback response dict.
    """
    # Validate extraction belongs to user
    extraction = get_extraction(extraction_id, user_id=user_id)
    if extraction is None:
        raise ValueError(f'Extraction {extraction_id} not found')

    track_id = str(extraction['track_id'])
    track = get_track(track_id)
    user = get_user_by_id(user_id)

    reextraction_id: Optional[str] = None
    credit_cost = 0

    # Queue re-extraction if user provided a refined label and feedback wasn't 'good'
    if refined_label and feedback_type != 'good':
        reextraction_id, credit_cost = _trigger_reextraction(
            user_id=user_id,
            track=track,
            original_extraction=extraction,
            refined_label=refined_label,
        )

    # Record feedback row
    feedback = create_feedback(
        extraction_id=extraction_id,
        user_id=user_id,
        track_id=track_id,
        segment_start_seconds=segment_start_seconds,
        segment_end_seconds=segment_end_seconds,
        segment_label=segment_label,
        feedback_type=feedback_type,
        feedback_detail=feedback_detail,
        refined_label=refined_label,
        comment=comment,
        reextraction_id=reextraction_id,
    )

    # Write training data if user opted in
    if user and user.get('opt_in_training_data'):
        _store_training_data(
            user_id=user_id,
            label=refined_label or segment_label,
            feedback_type=feedback_type,
            feedback_detail=feedback_detail,
            refined_label=refined_label,
            genre=track.get('genre_detected') if track else None,
            tempo=track.get('tempo_detected') if track else None,
            opt_in=True,
        )

    return {
        'feedback_id': str(feedback['feedback_id']),
        'extraction_id': extraction_id,
        'status': 'recorded' if feedback_type == 'good' else 'queued_for_reextraction',
        'reextraction_queued': reextraction_id is not None,
        'new_extraction_id': reextraction_id,
        'cost_credits': credit_cost,
        'created_at': feedback['created_at'].isoformat(),
    }


def _trigger_reextraction(
    user_id: str,
    track: Optional[Dict],
    original_extraction: Dict,
    refined_label: str,
) -> tuple:
    """Create and queue a re-extraction based on refined label.

    Returns (reextraction_id, credit_cost).
    Raises ValueError on insufficient credits.
    """
    if track is None:
        raise ValueError('Track not found for re-extraction')

    sources = [{'label': refined_label, 'model': 'demucs', 'ambiguous': False}]
    cost_info = compute_extraction_cost(sources, is_reextraction=True)
    credit_cost = cost_info['total_cost']

    # Charge credits (raises on insufficient)
    charge_for_extraction(user_id, credit_cost, is_reextraction=True)

    # Create re-extraction DB record
    reextraction = create_extraction(
        track_id=str(track['track_id']),
        user_id=user_id,
        sources_requested=sources,
        credit_cost=credit_cost,
        iteration_id=str(original_extraction['extraction_id']),
    )
    reextraction_id = str(reextraction['extraction_id'])

    # Enqueue task
    nlp_params = parse_label_to_params(refined_label)
    sources_with_params = [{**s, 'nlp_params': nlp_params} for s in sources]

    enqueue_reextraction_job(
        extraction_id=reextraction_id,
        track_id=str(track['track_id']),
        gcs_path=track['gcs_path'],
        sources=sources_with_params,
        feedback_id='',  # Will be linked after feedback row creation
    )

    logger.info('Re-extraction queued: %s with refined_label=%s', reextraction_id, refined_label)
    return reextraction_id, credit_cost


def _store_training_data(
    user_id: str,
    label: str,
    feedback_type: Optional[str],
    feedback_detail: Optional[str],
    refined_label: Optional[str],
    genre: Optional[str],
    tempo: Optional[int],
    opt_in: bool,
) -> None:
    """Write anonymized training data point."""
    try:
        nlp_params = parse_label_to_params(label)
        point = build_training_point(
            user_id=user_id,
            original_label=label,
            nlp_params=nlp_params,
            feedback_type=feedback_type,
            feedback_detail=feedback_detail,
            refined_label=refined_label,
            genre=genre,
            tempo=tempo,
            opt_in=opt_in,
        )
        insert_training_data(**point)
        logger.debug('Training data point written for user %s', user_id[:8])
    except Exception as exc:
        # Training data failure must not block user-facing response
        logger.warning('Training data write failed: %s', exc)
