"""
Google Cloud Storage service.

In development (ENABLE_MOCK_RESPONSES=true), returns mock URLs.
In production, performs real GCS operations.
"""

import io
import os
import logging
import hashlib
from datetime import timedelta
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

GCS_BUCKET = os.getenv('GCS_BUCKET', 'music-separation-dev')
MOCK_MODE = os.getenv('ENABLE_MOCK_RESPONSES', 'false').lower() == 'true'

_gcs_client = None
_bucket = None


def _get_client():
    """Lazy-initialize GCS client."""
    global _gcs_client, _bucket
    if _gcs_client is None:
        from google.cloud import storage
        _gcs_client = storage.Client()
        _bucket = _gcs_client.bucket(GCS_BUCKET)
    return _gcs_client, _bucket


# ---------------------------------------------------------------------------
# Upload helpers
# ---------------------------------------------------------------------------

def upload_audio(
    file_data: bytes,
    track_id: str,
    filename: str,
    content_type: str = 'audio/wav',
) -> Tuple[str, str]:
    """Upload original audio to GCS.

    Returns (gcs_path, public_url).
    """
    gcs_path = f'tracks/{track_id}/original/{filename}'

    if MOCK_MODE:
        logger.debug('[MOCK] Would upload %s to gs://%s/%s', filename, GCS_BUCKET, gcs_path)
        return (
            f'gs://{GCS_BUCKET}/{gcs_path}',
            f'https://storage.googleapis.com/{GCS_BUCKET}/{gcs_path}',
        )

    _, bucket = _get_client()
    blob = bucket.blob(gcs_path)
    blob.upload_from_string(file_data, content_type=content_type)
    logger.info('Uploaded %s bytes to gs://%s/%s', len(file_data), GCS_BUCKET, gcs_path)
    return (
        f'gs://{GCS_BUCKET}/{gcs_path}',
        f'https://storage.googleapis.com/{GCS_BUCKET}/{gcs_path}',
    )


def upload_stem(
    file_data: bytes,
    extraction_id: str,
    label: str,
    content_type: str = 'audio/wav',
) -> Tuple[str, str]:
    """Upload a separated stem to GCS.

    Returns (gcs_path, audio_url).
    """
    safe_label = label.replace(' ', '_').lower()
    gcs_path = f'extractions/{extraction_id}/stems/{safe_label}.wav'

    if MOCK_MODE:
        return (
            f'gs://{GCS_BUCKET}/{gcs_path}',
            f'https://storage.googleapis.com/{GCS_BUCKET}/{gcs_path}',
        )

    _, bucket = _get_client()
    blob = bucket.blob(gcs_path)
    blob.upload_from_string(file_data, content_type=content_type)
    return (
        f'gs://{GCS_BUCKET}/{gcs_path}',
        f'https://storage.googleapis.com/{GCS_BUCKET}/{gcs_path}',
    )


def upload_waveform_json(
    waveform_data: bytes,
    extraction_id: str,
    label: str,
) -> str:
    """Upload waveform JSON for a stem.

    Returns the GCS path.
    """
    safe_label = label.replace(' ', '_').lower()
    gcs_path = f'extractions/{extraction_id}/waveforms/{safe_label}_waveform.json'

    if MOCK_MODE:
        return f'https://storage.googleapis.com/{GCS_BUCKET}/{gcs_path}'

    _, bucket = _get_client()
    blob = bucket.blob(gcs_path)
    blob.upload_from_string(waveform_data, content_type='application/json')
    return f'https://storage.googleapis.com/{GCS_BUCKET}/{gcs_path}'


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

def download_audio(gcs_path: str) -> bytes:
    """Download audio bytes from GCS path."""
    if MOCK_MODE:
        logger.debug('[MOCK] Would download %s', gcs_path)
        return b''  # Empty in mock mode

    _, bucket = _get_client()
    blob_name = gcs_path.replace(f'gs://{GCS_BUCKET}/', '')
    blob = bucket.blob(blob_name)
    return blob.download_as_bytes()


def get_signed_url(gcs_path: str, expiration_minutes: int = 60) -> str:
    """Generate a signed URL for temporary access to a GCS object.

    Returns a mock URL in development mode.
    """
    if MOCK_MODE:
        return f'https://storage.googleapis.com/{GCS_BUCKET}/{gcs_path}?mock=1&expires={expiration_minutes}m'

    _, bucket = _get_client()
    blob_name = gcs_path.replace(f'gs://{GCS_BUCKET}/', '')
    blob = bucket.blob(blob_name)
    return blob.generate_signed_url(expiration=timedelta(minutes=expiration_minutes))


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------

def delete_track_files(track_id: str) -> int:
    """Delete all files for a track from GCS.

    Returns count of deleted blobs.
    """
    if MOCK_MODE:
        logger.debug('[MOCK] Would delete track files for %s', track_id)
        return 0

    _, bucket = _get_client()
    prefix = f'tracks/{track_id}/'
    blobs = list(bucket.list_blobs(prefix=prefix))
    for blob in blobs:
        blob.delete()
    logger.info('Deleted %d blobs for track %s', len(blobs), track_id)
    return len(blobs)


def delete_extraction_files(extraction_id: str) -> int:
    """Delete all stem/waveform files for an extraction."""
    if MOCK_MODE:
        return 0

    _, bucket = _get_client()
    prefix = f'extractions/{extraction_id}/'
    blobs = list(bucket.list_blobs(prefix=prefix))
    for blob in blobs:
        blob.delete()
    return len(blobs)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def compute_spectral_hash(audio_bytes: bytes) -> str:
    """Compute a simple hash of audio bytes for dedup / fingerprinting."""
    return hashlib.sha256(audio_bytes).hexdigest()
