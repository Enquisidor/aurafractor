"""
Input validation utilities.

All validation functions raise ValueError with user-friendly messages.
"""

import uuid
from typing import Any, Dict, List

SUPPORTED_FORMATS = {'mp3', 'wav', 'flac', 'ogg'}
SUPPORTED_MODELS = {'demucs', 'spleeter'}
VALID_FEEDBACK_TYPES = {'too_much', 'too_little', 'artifacts', 'good'}
MAX_FILE_SIZE_MB = 200
MAX_DURATION_SECONDS = 600  # 10 minutes
MAX_SOURCES_PER_REQUEST = 10


def validate_uuid(value: Any, field_name: str) -> str:
    """Validate and return a string UUID."""
    if not value:
        raise ValueError(f'{field_name} is required')
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError):
        raise ValueError(f'{field_name} must be a valid UUID')


def validate_device_id(device_id: Any) -> str:
    """Validate device_id: non-empty string, 8-255 chars."""
    if not device_id or not isinstance(device_id, str):
        raise ValueError('device_id is required and must be a string')
    device_id = device_id.strip()
    if len(device_id) < 4:
        raise ValueError('device_id must be at least 4 characters')
    if len(device_id) > 255:
        raise ValueError('device_id must be 255 characters or fewer')
    return device_id


def validate_audio_file(filename: str, file_size_bytes: int) -> str:
    """Validate audio file name and size. Returns the file extension."""
    if not filename:
        raise ValueError('filename is required')
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f'Unsupported format "{ext}". Supported: {", ".join(sorted(SUPPORTED_FORMATS))}')
    size_mb = file_size_bytes / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f'File size {size_mb:.1f}MB exceeds maximum {MAX_FILE_SIZE_MB}MB')
    return ext


def validate_sources(sources: Any) -> List[Dict]:
    """Validate extraction sources list."""
    if not sources or not isinstance(sources, list):
        raise ValueError('sources must be a non-empty list')
    if len(sources) > MAX_SOURCES_PER_REQUEST:
        raise ValueError(f'Too many sources: max {MAX_SOURCES_PER_REQUEST}')

    validated = []
    for i, source in enumerate(sources):
        if not isinstance(source, dict):
            raise ValueError(f'sources[{i}] must be an object')
        label = source.get('label', '').strip()
        if not label:
            raise ValueError(f'sources[{i}].label is required')
        if len(label) > 255:
            raise ValueError(f'sources[{i}].label must be 255 characters or fewer')
        model = source.get('model', 'demucs').lower()
        if model not in SUPPORTED_MODELS:
            raise ValueError(f'sources[{i}].model must be one of: {", ".join(SUPPORTED_MODELS)}')
        validated.append({'label': label, 'model': model, **{k: v for k, v in source.items() if k not in ('label', 'model')}})

    return validated


def validate_feedback(data: Dict) -> Dict:
    """Validate feedback submission payload."""
    feedback_type = data.get('feedback_type', '')
    if feedback_type not in VALID_FEEDBACK_TYPES:
        raise ValueError(f'feedback_type must be one of: {", ".join(sorted(VALID_FEEDBACK_TYPES))}')

    segment_start = data.get('segment_start_seconds')
    segment_end = data.get('segment_end_seconds')
    segment_label = data.get('segment_label', '').strip()

    if segment_start is None:
        raise ValueError('segment_start_seconds is required')
    if segment_end is None:
        raise ValueError('segment_end_seconds is required')
    if not isinstance(segment_start, (int, float)) or segment_start < 0:
        raise ValueError('segment_start_seconds must be a non-negative number')
    if not isinstance(segment_end, (int, float)) or segment_end <= segment_start:
        raise ValueError('segment_end_seconds must be greater than segment_start_seconds')
    if not segment_label:
        raise ValueError('segment_label is required')

    refined_label = data.get('refined_label', '').strip() or None

    return {
        'feedback_type': feedback_type,
        'segment_start_seconds': int(segment_start),
        'segment_end_seconds': int(segment_end),
        'segment_label': segment_label,
        'feedback_detail': data.get('feedback_detail'),
        'refined_label': refined_label,
        'comment': data.get('comment'),
    }


def validate_pagination(limit: Any, offset: Any) -> tuple:
    """Validate and clamp pagination parameters."""
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 20
    try:
        offset = int(offset)
    except (TypeError, ValueError):
        offset = 0
    limit = max(1, min(100, limit))
    offset = max(0, offset)
    return limit, offset
