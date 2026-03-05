"""
Extraction orchestration service.

Coordinates: upload → NLP → credit check → DB creation → Cloud Tasks queue.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from database.models import (
    get_track,
    create_extraction,
    get_extraction,
    get_extraction_with_result,
    update_extraction_status,
    create_extraction_result,
    count_active_extractions,
)
from services.credits import compute_extraction_cost, charge_for_extraction, refund_for_failed_extraction
from services.nlp import parse_label_to_params, compute_ambiguity_score
from services.tasks import enqueue_extraction_job

logger = logging.getLogger(__name__)

MAX_CONCURRENT_EXTRACTIONS = int(os.getenv('MAX_CONCURRENT_EXTRACTIONS', '4'))


def process_sources_with_nlp(sources: List[Dict]) -> tuple:
    """Run NLP over each source entry.

    Returns (processed_sources, ambiguous_labels).
    """
    processed: List[Dict] = []
    ambiguous: List[Dict] = []

    for source in sources:
        label = source.get('label', '')
        model = source.get('model', 'demucs')
        timestamps = source.get('timestamps')

        nlp_params = parse_label_to_params(label)
        ambiguity = compute_ambiguity_score(label)
        is_ambiguous = ambiguity > 0.6

        if is_ambiguous:
            ambiguous.append({
                'label': label,
                'ambiguity_score': ambiguity,
                'suggestion': 'Consider refining this label for better results',
            })

        processed.append({
            'label': label,
            'model': model,
            'nlp_params': nlp_params,
            'ambiguous': is_ambiguous,
            'ambiguity_score': ambiguity,
            'timestamps': timestamps,
        })

    return processed, ambiguous


def initiate_extraction(
    user_id: str,
    track_id: str,
    sources: List[Dict],
    is_reextraction: bool = False,
    iteration_id: Optional[str] = None,
    force_ambiguous: bool = False,
) -> Dict:
    """Full extraction pipeline:

    1. Validate track ownership
    2. Check concurrent extraction limit
    3. Run NLP on sources
    4. Compute + check credits
    5. Deduct credits
    6. Create DB record
    7. Enqueue Cloud Task
    8. Return response

    Args:
        force_ambiguous: If True, proceed even for ambiguous labels (user confirmed).

    Raises:
        ValueError: On validation failures.
    """
    # 1. Validate track
    track = get_track(track_id, user_id=user_id)
    if track is None:
        raise ValueError(f'Track {track_id} not found or does not belong to this user')

    # 2. Concurrent extraction limit
    active = count_active_extractions()
    if active >= MAX_CONCURRENT_EXTRACTIONS:
        raise ValueError(
            f'System is at capacity ({MAX_CONCURRENT_EXTRACTIONS} concurrent extractions). '
            'Please try again in a few minutes.'
        )

    # 3. NLP processing
    processed_sources, ambiguous_labels = process_sources_with_nlp(sources)

    # If ambiguous labels present and user hasn't confirmed, surface them
    if ambiguous_labels and not force_ambiguous:
        return {
            'status': 'awaiting_confirmation',
            'ambiguous_labels': ambiguous_labels,
            'message': 'Some labels are ambiguous. Set force_ambiguous=true to proceed anyway (costs extra credits).',
        }

    # 4. Credit calculation
    cost_breakdown = compute_extraction_cost(processed_sources, is_reextraction=is_reextraction)
    total_cost = cost_breakdown['total_cost']

    # 5. Deduct credits (raises ValueError on insufficient)
    charge_for_extraction(user_id, total_cost, is_reextraction=is_reextraction)

    # 6. Create DB record
    extraction = None
    try:
        extraction = create_extraction(
            track_id=track_id,
            user_id=user_id,
            sources_requested=processed_sources,
            credit_cost=total_cost,
            iteration_id=iteration_id,
        )
        extraction_id = str(extraction['extraction_id'])

        # 7. Queue Cloud Task
        job_id = enqueue_extraction_job(
            extraction_id=extraction_id,
            track_id=track_id,
            gcs_path=track['gcs_path'],
            sources=processed_sources,
        )

        update_extraction_status(extraction_id, 'queued', job_id=job_id)

        logger.info(
            'Extraction queued: extraction_id=%s track_id=%s sources=%d cost=%d',
            extraction_id, track_id, len(processed_sources), total_cost,
        )

        return {
            'extraction_id': extraction_id,
            'track_id': track_id,
            'job_id': job_id,
            'status': 'queued',
            'sources_requested': len(processed_sources),
            'models_used': list({s['model'] for s in processed_sources}),
            'estimated_time_seconds': _estimate_time(track, len(processed_sources)),
            'cost_credits': total_cost,
            'cost_breakdown': cost_breakdown,
            'ambiguous_labels': ambiguous_labels,
            'queue_position': active + 1,
            'created_at': extraction['created_at'].isoformat(),
        }

    except Exception as exc:
        # Refund credits if extraction record was not created or queuing failed
        logger.error('Extraction initiation failed, refunding credits: %s', exc)
        if extraction is not None:
            extraction_id = str(extraction['extraction_id'])
        else:
            extraction_id = None
        try:
            refund_for_failed_extraction(user_id, total_cost, extraction_id)
        except Exception as refund_exc:
            logger.error('Credit refund also failed: %s', refund_exc)
        raise ValueError(f'Extraction failed: {exc}') from exc


def get_extraction_status(extraction_id: str, user_id: str) -> Dict:
    """Return the current status of an extraction."""
    row = get_extraction_with_result(extraction_id)
    if row is None:
        raise ValueError(f'Extraction {extraction_id} not found')
    if str(row['user_id']) != user_id:
        raise ValueError('Extraction does not belong to this user')

    response: Dict[str, Any] = {
        'extraction_id': str(row['extraction_id']),
        'track_id': str(row['track_id']),
        'status': row['status'],
        'created_at': row['created_at'].isoformat(),
        'started_at': row['started_at'].isoformat() if row.get('started_at') else None,
        'completed_at': row['completed_at'].isoformat() if row.get('completed_at') else None,
        'cost_credits': row['credit_cost'],
        'job_id': row.get('job_id'),
    }

    if row['status'] == 'completed' and row.get('result_sources'):
        response['results'] = {'sources': row['result_sources']}
        response['processing_time_seconds'] = row.get('processing_time_seconds')

    return response


def handle_extraction_webhook(
    extraction_id: str,
    success: bool,
    sources: Optional[List[Dict]] = None,
    error_message: Optional[str] = None,
    processing_time_seconds: Optional[int] = None,
) -> None:
    """Handle callback from extraction worker.

    Updates DB status and stores results.
    """
    if success and sources is not None:
        create_extraction_result(extraction_id, sources)
        update_extraction_status(
            extraction_id,
            'completed',
            processing_time_seconds=processing_time_seconds,
        )
        logger.info('Extraction completed: %s', extraction_id)
    else:
        update_extraction_status(extraction_id, 'failed')
        logger.warning('Extraction failed: %s – %s', extraction_id, error_message)

        # Refund credits
        row = get_extraction(extraction_id)
        if row:
            user_id = str(row['user_id'])
            credit_cost = row['credit_cost']
            try:
                refund_for_failed_extraction(user_id, credit_cost, extraction_id)
            except Exception as exc:
                logger.error('Refund failed for extraction %s: %s', extraction_id, exc)


def _estimate_time(track: Dict, source_count: int) -> int:
    """Rough estimate of processing time in seconds."""
    duration = track.get('duration_seconds', 180)
    base = max(30, int(duration * 0.5))
    return base * source_count
