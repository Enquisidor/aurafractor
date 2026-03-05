"""
Example test file showing test patterns for the backend.

Uses the shared fixtures from conftest.py (mock mode, no real DB/GCS).
Run with: pytest tests/test_example.py -v
"""

import uuid
import pytest

from services.nlp import parse_label_to_params, compute_ambiguity_score


# Note: client, auth_headers, worker_headers fixtures come from conftest.py


# ============================================================================
# HEALTH & AUTH TESTS
# ============================================================================

def test_health_check(client):
    """Health endpoint returns ok with version."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'
    assert 'timestamp' in data
    assert 'version' in data


def test_register_user(client):
    """Registration returns all expected fields."""
    response = client.post('/auth/register', json={
        'device_id': 'test-device-456',
        'app_version': '1.0.0',
    })
    assert response.status_code == 201
    data = response.get_json()
    assert 'user_id' in data
    assert 'session_token' in data
    assert 'refresh_token' in data
    assert data['subscription_tier'] == 'free'
    assert data['credits_remaining'] == 100


def test_register_missing_device_id(client):
    """Registration fails without device_id."""
    response = client.post('/auth/register', json={'app_version': '1.0.0'})
    assert response.status_code == 400


def test_refresh_token(client):
    """A valid refresh token returns a new session token."""
    reg = client.post('/auth/register', json={
        'device_id': 'test-device-refresh',
        'app_version': '1.0.0',
    })
    refresh_token = reg.get_json()['refresh_token']

    response = client.post('/auth/refresh', json={'refresh_token': refresh_token})
    assert response.status_code == 200
    data = response.get_json()
    assert 'session_token' in data
    assert data['expires_in'] == 86400


# ============================================================================
# NLP TESTS
# ============================================================================

def test_parse_label_lead_vocals_without_reverb():
    """Complex label parses to correct parameters."""
    params = parse_label_to_params('lead vocals without reverb')
    assert params['source'] == 'vocal'
    assert params['vocal_type'] == 'lead'
    assert params.get('preserve_reverb') is False
    assert params.get('dryness', 0) > 0.8


def test_parse_label_tight_kick():
    """'tight kick' parses to kick drum with high isolation."""
    params = parse_label_to_params('tight kick')
    assert params['source'] == 'drum'
    assert params['drum_type'] == 'kick'
    assert params['isolation_level'] == 0.9
    assert params['attack_preservation'] == 1.0
    assert params['bleed_suppression'] == 0.95


def test_parse_label_single_word_vocals():
    """Single-word 'vocals' is a valid, clear label."""
    params = parse_label_to_params('vocals')
    assert params['source'] == 'vocal'
    assert params['isolation_level'] == 0.7


def test_parse_label_drums():
    """Single-word 'drums' is valid."""
    params = parse_label_to_params('drums')
    assert params['source'] == 'drum'


def test_parse_label_synth():
    """'synth' maps to other source."""
    params = parse_label_to_params('synth')
    assert params['source'] == 'other'
    assert params['synth_type'] == 'synth'


def test_parse_label_ambiguous():
    """'thing' is flagged as ambiguous."""
    params = parse_label_to_params('thing')
    assert params['ambiguous'] is True
    assert params['confidence'] == 0.0
    assert params['requires_clarification'] is True


def test_parse_label_unknown():
    """Completely unknown label is flagged ambiguous."""
    params = parse_label_to_params('obscure_instrument_xyz')
    assert params['ambiguous'] is True


# ============================================================================
# AMBIGUITY SCORING TESTS
# ============================================================================

def test_ambiguity_score_clear_single_word():
    assert compute_ambiguity_score('vocals') < 0.2


def test_ambiguity_score_clear_single_word_drums():
    assert compute_ambiguity_score('drums') < 0.2


def test_ambiguity_score_clear_multi_word():
    assert compute_ambiguity_score('lead vocals') < 0.3


def test_ambiguity_score_vague_word():
    assert compute_ambiguity_score('thing') > 0.8


def test_ambiguity_score_empty():
    assert compute_ambiguity_score('') == 1.0


def test_ambiguity_score_whitespace():
    assert compute_ambiguity_score('   ') == 1.0


def test_ambiguity_score_unknown_single_word():
    score = compute_ambiguity_score('xyzzy')
    assert 0.3 < score < 0.5


def test_ambiguity_score_with_descriptors():
    """Descriptive multi-word labels are at least as clear as single-word."""
    base = compute_ambiguity_score('vocals')
    with_descriptor = compute_ambiguity_score('lead vocals')
    assert with_descriptor <= base


# ============================================================================
# UPLOAD TESTS
# ============================================================================

def test_upload_requires_auth(client):
    response = client.post('/upload', data={})
    assert response.status_code == 401


def test_upload_missing_file(client, auth_headers):
    response = client.post('/upload', headers=auth_headers,
                           content_type='multipart/form-data')
    assert response.status_code == 400


def test_upload_success(client, auth_headers):
    """Valid audio file returns track_id."""
    response = client.post(
        '/upload',
        headers=auth_headers,
        data={'file': (b'RIFF\x00\x00\x00\x00WAVEfmt ', 'test.wav')},
        content_type='multipart/form-data',
    )
    assert response.status_code == 201
    data = response.get_json()
    assert 'track_id' in data
    assert data['status'] == 'ready'


# ============================================================================
# EXTRACTION TESTS
# ============================================================================

def test_extraction_suggest_labels(client, auth_headers):
    """Suggest-labels returns labelled suggestions with genre/tempo."""
    track_id = str(uuid.uuid4())
    response = client.post('/extraction/suggest-labels',
                           headers=auth_headers,
                           json={'track_id': track_id})
    assert response.status_code == 200
    data = response.get_json()
    assert data['track_id'] == track_id
    assert len(data['suggested_labels']) > 0
    assert 'genre' in data
    assert 'tempo' in data


def test_extraction_extract_success(client, auth_headers):
    """Extraction request returns queued status with cost."""
    response = client.post('/extraction/extract', headers=auth_headers, json={
        'track_id': str(uuid.uuid4()),
        'sources': [
            {'label': 'vocals', 'model': 'demucs'},
            {'label': 'drums', 'model': 'demucs'},
        ],
    })
    assert response.status_code == 201
    data = response.get_json()
    assert 'extraction_id' in data
    assert data['status'] == 'queued'
    assert data['sources_requested'] == 2
    assert 'cost_credits' in data


def test_extraction_extract_ambiguous_label(client, auth_headers):
    """Ambiguous label is flagged and costs extra credits."""
    response = client.post('/extraction/extract', headers=auth_headers, json={
        'track_id': str(uuid.uuid4()),
        'sources': [{'label': 'thing', 'model': 'demucs'}],
    })
    assert response.status_code == 201
    data = response.get_json()
    assert len(data['ambiguous_labels']) > 0
    assert data['cost_credits'] > 5  # Ambiguity surcharge applied


def test_extraction_extract_missing_sources(client, auth_headers):
    """Missing sources returns 400."""
    response = client.post('/extraction/extract', headers=auth_headers,
                           json={'track_id': str(uuid.uuid4())})
    assert response.status_code == 400


# ============================================================================
# FEEDBACK TESTS
# ============================================================================

def test_feedback_good(client, auth_headers):
    """Feedback type 'good' is recorded with zero cost."""
    extraction_id = str(uuid.uuid4())
    response = client.post(
        f'/extraction/{extraction_id}/feedback',
        headers=auth_headers,
        json={
            'feedback_type': 'good',
            'segment_start_seconds': 0,
            'segment_end_seconds': 180,
            'segment_label': 'vocals',
        },
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data['status'] == 'recorded'
    assert data['cost_credits'] == 0


def test_feedback_with_refinement(client, auth_headers):
    """Feedback with refined_label queues a re-extraction."""
    extraction_id = str(uuid.uuid4())
    response = client.post(
        f'/extraction/{extraction_id}/feedback',
        headers=auth_headers,
        json={
            'feedback_type': 'too_much',
            'segment_start_seconds': 30,
            'segment_end_seconds': 60,
            'segment_label': 'vocals',
            'refined_label': 'dry lead vocals',
        },
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data['reextraction_queued'] is True
    assert data['new_extraction_id'] is not None
    assert data['cost_credits'] > 0


# ============================================================================
# CREDIT TESTS
# ============================================================================

def test_user_credits(client, auth_headers):
    """Credits endpoint returns balance, tier, and usage."""
    response = client.get('/user/credits', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert 'current_balance' in data
    assert 'monthly_allowance' in data
    assert 'subscription_tier' in data
    assert 'usage_this_month' in data


# ============================================================================
# HISTORY TESTS
# ============================================================================

def test_user_history(client, auth_headers):
    """History returns paginated tracks."""
    response = client.get('/user/history', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert 'total_tracks' in data
    assert 'tracks' in data
    assert 'pagination' in data


def test_user_history_pagination(client, auth_headers):
    """Pagination parameters are reflected in the response."""
    response = client.get('/user/history?limit=5&offset=10', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data['pagination']['limit'] == 5
    assert data['pagination']['offset'] == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
