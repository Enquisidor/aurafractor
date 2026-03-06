"""Upload route."""

import io
import os
from datetime import datetime

from flask import Blueprint, request, jsonify, g

from utils.decorators import require_auth, handle_errors
from utils.rate_limiting import limiter
from utils.validation import validate_audio_file
from utils.monitoring import increment

bp = Blueprint('upload', __name__)
MOCK_MODE = os.getenv('ENABLE_MOCK_RESPONSES', 'false').lower() == 'true'


@bp.route('/upload', methods=['POST'])
@require_auth
@limiter.limit("10 per hour")
@handle_errors
def upload():
    """Upload an audio file and store it in GCS."""
    if 'file' not in request.files:
        raise ValueError('file is required')
    file = request.files['file']
    if not file.filename:
        raise ValueError('filename is required')

    file_bytes = file.read()
    ext = validate_audio_file(file.filename, len(file_bytes))
    user_id = g.user['user_id']

    if MOCK_MODE:
        import uuid
        track_id = str(uuid.uuid4())
        return jsonify({
            'track_id': track_id,
            'uploaded_at': datetime.utcnow().isoformat(),
            'duration_seconds': 180,
            'file_size_mb': round(len(file_bytes) / (1024 * 1024), 2),
            'audio_url': f'https://storage.googleapis.com/mock-bucket/tracks/{track_id}/original.wav',
            'status': 'ready',
        }), 201

    if not MOCK_MODE:  # pragma: no cover
        import soundfile as sf
        from services.storage import upload_audio, compute_spectral_hash
        from ml_models.classifier import classify_instruments
        from database.models import create_track
        from database.connection import execute_query

        try:
            audio_data, sample_rate = sf.read(io.BytesIO(file_bytes))
            duration_seconds = int(len(audio_data) / sample_rate)
        except Exception:
            duration_seconds = 0
            sample_rate = 44100

        file_size_mb = round(len(file_bytes) / (1024 * 1024), 2)
        classification = classify_instruments(file_bytes)

        track = create_track(
            user_id=user_id,
            filename=file.filename,
            duration_seconds=max(1, duration_seconds),
            format=ext,
            gcs_path='pending',
            file_size_mb=file_size_mb,
            sample_rate=sample_rate,
            genre_detected=classification.get('genre'),
            tempo_detected=classification.get('tempo'),
            spectral_hash=compute_spectral_hash(file_bytes),
        )
        track_id = str(track['track_id'])

        gcs_path, audio_url = upload_audio(file_bytes, track_id, file.filename)
        execute_query("UPDATE tracks SET gcs_path = %s WHERE track_id = %s", (gcs_path, track_id))

        increment('uploads.total')
        return jsonify({
            'track_id': track_id,
            'uploaded_at': track['uploaded_at'].isoformat(),
            'duration_seconds': duration_seconds,
            'file_size_mb': file_size_mb,
            'audio_url': audio_url,
            'genre_detected': classification.get('genre'),
            'tempo_detected': classification.get('tempo'),
            'status': 'ready',
        }), 201
