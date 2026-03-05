"""
Extraction worker.

Called by Cloud Tasks via POST /worker/extract.
Runs Demucs or Spleeter, uploads stems to GCS, then POSTs webhook callback.
"""

import logging
import os
import time
from typing import Dict, List

import requests

from models import demucs_wrapper, spleeter_wrapper
from services.storage import download_audio, upload_stem, upload_waveform_json
from database.models import update_extraction_status

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5000')
WORKER_SECRET = os.getenv('WORKER_SECRET', 'worker-secret')


def run_extraction(payload: Dict) -> Dict:
    """Execute an extraction job from a Cloud Tasks payload.

    Args:
        payload: {extraction_id, track_id, gcs_path, sources, is_reextraction?}

    Returns:
        Result dict with extracted sources info.
    """
    extraction_id = payload['extraction_id']
    gcs_path = payload['gcs_path']
    sources = payload['sources']

    logger.info('Starting extraction %s with %d sources', extraction_id, len(sources))
    start_time = time.time()

    # Mark as processing
    update_extraction_status(extraction_id, 'processing')

    try:
        # Download audio from GCS
        logger.info('Downloading audio from %s', gcs_path)
        audio_bytes = download_audio(gcs_path)

        # Group sources by model
        demucs_sources = [s for s in sources if s.get('model', 'demucs') == 'demucs']
        spleeter_sources = [s for s in sources if s.get('model') == 'spleeter']

        result_sources = []

        if demucs_sources:
            results = demucs_wrapper.separate(audio_bytes, demucs_sources)
            result_sources.extend(_upload_stems(extraction_id, results))

        if spleeter_sources:
            results = spleeter_wrapper.separate(audio_bytes, spleeter_sources)
            result_sources.extend(_upload_stems(extraction_id, results))

        processing_time = int(time.time() - start_time)
        logger.info('Extraction %s completed in %ds', extraction_id, processing_time)

        # Notify API via webhook
        _send_webhook(
            extraction_id=extraction_id,
            success=True,
            sources=result_sources,
            processing_time_seconds=processing_time,
        )

        return {'extraction_id': extraction_id, 'sources': result_sources, 'processing_time': processing_time}

    except Exception as exc:
        logger.error('Extraction %s failed: %s', extraction_id, exc, exc_info=True)
        _send_webhook(
            extraction_id=extraction_id,
            success=False,
            error_message=str(exc),
        )
        raise


def _upload_stems(extraction_id: str, separation_results: List[Dict]) -> List[Dict]:
    """Upload stems to GCS and return source metadata."""
    uploaded = []
    for result in separation_results:
        label = result['label']
        audio_bytes = result.get('audio_bytes', b'')

        if audio_bytes and audio_bytes != b'MOCK_WAV_DATA':
            gcs_path, audio_url = upload_stem(audio_bytes, extraction_id, label)
            # Generate simple waveform data (peak amplitude per chunk)
            waveform_data = _compute_waveform_json(audio_bytes)
            waveform_url = upload_waveform_json(waveform_data, extraction_id, label)
        else:
            # Mock mode
            gcs_path = f'gs://bucket/extractions/{extraction_id}/stems/{label.replace(" ", "_")}.wav'
            audio_url = f'https://storage.googleapis.com/bucket/extractions/{extraction_id}/stems/{label.replace(" ", "_")}.wav'
            waveform_url = f'https://storage.googleapis.com/bucket/extractions/{extraction_id}/waveforms/{label.replace(" ", "_")}_waveform.json'

        uploaded.append({
            'label': label,
            'model_used': result.get('model', 'demucs'),
            'audio_url': audio_url,
            'gcs_path': gcs_path,
            'waveform_url': waveform_url,
            'duration_seconds': result.get('duration_seconds', 0),
            'sample_rate': result.get('sample_rate', 44100),
        })
    return uploaded


def _compute_waveform_json(audio_bytes: bytes, chunks: int = 100) -> bytes:
    """Compute a simple peak-amplitude waveform from audio bytes."""
    import json
    try:
        import numpy as np
        import soundfile as sf
        import io
        data, sr = sf.read(io.BytesIO(audio_bytes))
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        chunk_size = max(1, len(data) // chunks)
        peaks = [float(np.max(np.abs(data[i:i + chunk_size]))) for i in range(0, len(data), chunk_size)]
        return json.dumps({'peaks': peaks[:chunks]}).encode()
    except Exception:
        return json.dumps({'peaks': [0.0] * chunks}).encode()


def _send_webhook(
    extraction_id: str,
    success: bool,
    sources: List[Dict] = None,
    processing_time_seconds: int = None,
    error_message: str = None,
) -> None:
    """POST result to the webhook endpoint."""
    payload = {
        'extraction_id': extraction_id,
        'success': success,
        'sources': sources or [],
        'processing_time_seconds': processing_time_seconds,
        'error_message': error_message,
    }
    try:
        resp = requests.post(
            f'{API_BASE_URL}/webhooks/extraction-complete',
            json=payload,
            headers={'X-Worker-Secret': WORKER_SECRET},
            timeout=30,
        )
        resp.raise_for_status()
        logger.info('Webhook sent for extraction %s', extraction_id)
    except Exception as exc:
        logger.error('Webhook failed for extraction %s: %s', extraction_id, exc)
