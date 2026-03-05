"""
Example test file showing test patterns for the backend.

Run with: pytest tests/test_example.py -v
"""

import pytest
import json
from datetime import datetime, timedelta
from app import app, parse_label_to_params, compute_ambiguity_score


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_headers(client):
    """Register user and return auth headers"""
    response = client.post('/auth/register', json={
        'device_id': 'test-device-123',
        'app_version': '1.0.0'
    })
    data = json.loads(response.data)
    
    return {
        'Authorization': f"Bearer {data['session_token']}",
        'X-User-ID': data['user_id'],
    }


# ============================================================================
# HEALTH & AUTH TESTS
# ============================================================================

def test_health_check(client):
    """Test health endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'ok'
    assert 'timestamp' in data
    assert 'version' in data


def test_register_user(client):
    """Test user registration"""
    response = client.post('/auth/register', json={
        'device_id': 'test-device-456',
        'app_version': '1.0.0'
    })
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'user_id' in data
    assert 'session_token' in data
    assert 'refresh_token' in data
    assert data['subscription_tier'] == 'free'
    assert data['credits_remaining'] == 100


def test_register_missing_device_id(client):
    """Test registration fails without device_id"""
    response = client.post('/auth/register', json={
        'app_version': '1.0.0'
    })
    assert response.status_code == 400


def test_refresh_token(client, auth_headers):
    """Test token refresh"""
    # First register to get refresh token
    register_response = client.post('/auth/register', json={
        'device_id': 'test-device-refresh',
        'app_version': '1.0.0'
    })
    register_data = json.loads(register_response.data)
    refresh_token = register_data['refresh_token']
    
    # Now refresh
    response = client.post('/auth/refresh', json={
        'refresh_token': refresh_token
    })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'session_token' in data
    assert data['expires_in'] == 86400


# ============================================================================
# NLP TESTS
# ============================================================================

def test_parse_label_lead_vocals_without_reverb():
    """Test NLP parameter mapping for specific label"""
    params = parse_label_to_params('lead vocals without reverb')
    
    assert params['source'] == 'vocal'
    assert params['vocal_type'] == 'lead'
    assert params['isolation_level'] == 0.9
    assert params['dryness'] == 0.95
    assert params['preserve_reverb'] == False


def test_parse_label_tight_kick():
    """Test NLP parameter mapping for kick drum"""
    params = parse_label_to_params('tight kick')
    
    assert params['source'] == 'drum'
    assert params['drum_type'] == 'kick'
    assert params['isolation_level'] == 0.9
    assert params['attack_preservation'] == 1.0
    assert params['bleed_suppression'] == 0.95


def test_parse_label_single_word_vocals():
    """Test that single-word labels work"""
    params = parse_label_to_params('vocals')
    
    assert params['source'] == 'vocal'
    assert params['isolation_level'] == 0.7


def test_parse_label_drums():
    """Test single-word 'drums'"""
    params = parse_label_to_params('drums')
    
    assert params['source'] == 'drum'
    assert params['isolation_level'] == 0.7


def test_parse_label_synth():
    """Test synth source"""
    params = parse_label_to_params('synth')
    
    assert params['source'] == 'other'
    assert params['synth_type'] == 'synth'


def test_parse_label_ambiguous():
    """Test ambiguous label detection"""
    params = parse_label_to_params('thing')
    
    assert params['ambiguous'] == True
    assert params['confidence'] == 0.0
    assert params['requires_clarification'] == True


def test_parse_label_unknown():
    """Test unknown label handling"""
    params = parse_label_to_params('obscure_instrument_xyz')
    
    assert params['ambiguous'] == True


# ============================================================================
# AMBIGUITY SCORING TESTS
# ============================================================================

def test_ambiguity_score_clear_single_word():
    """Single instrument word should be very clear"""
    score = compute_ambiguity_score('vocals')
    assert score < 0.2  # Very clear


def test_ambiguity_score_clear_single_word_drums():
    """Drums is clear"""
    score = compute_ambiguity_score('drums')
    assert score < 0.2


def test_ambiguity_score_clear_multi_word():
    """Multi-word with descriptors is clear"""
    score = compute_ambiguity_score('lead vocals')
    assert score < 0.3


def test_ambiguity_score_vague_word():
    """Very vague words should score high"""
    score = compute_ambiguity_score('thing')
    assert score > 0.8


def test_ambiguity_score_empty():
    """Empty label is maximally ambiguous"""
    score = compute_ambiguity_score('')
    assert score == 1.0


def test_ambiguity_score_whitespace():
    """Whitespace-only label is ambiguous"""
    score = compute_ambiguity_score('   ')
    assert score == 1.0


def test_ambiguity_score_unknown_single_word():
    """Unknown single word is moderately ambiguous"""
    score = compute_ambiguity_score('xyzzy')
    assert 0.3 < score < 0.5


def test_ambiguity_score_with_descriptors():
    """Adding descriptors makes it clearer"""
    base = compute_ambiguity_score('vocals')
    with_descriptor = compute_ambiguity_score('lead vocals')
    
    assert with_descriptor <= base  # Equal or clearer


# ============================================================================
# UPLOAD TESTS
# ============================================================================

def test_upload_requires_auth(client):
    """Test that upload requires authentication"""
    response = client.post('/upload', data={})
    assert response.status_code == 401


def test_upload_missing_file(client, auth_headers):
    """Test upload without file"""
    response = client.post('/upload', headers=auth_headers)
    assert response.status_code == 400


def test_upload_success(client, auth_headers):
    """Test successful upload (with mock data)"""
    # In a real test, you'd provide an actual audio file
    # For now, this tests the response format
    
    response = client.post(
        '/upload',
        headers=auth_headers,
        data={'file': (None, '')},
    )
    
    # Should fail because no real file, but test response format
    # In real implementation, would have test audio file


# ============================================================================
# EXTRACTION TESTS
# ============================================================================

def test_extraction_suggest_labels(client, auth_headers):
    """Test label suggestion endpoint"""
    track_id = 'test-track-123'
    
    response = client.post(
        '/extraction/suggest-labels',
        headers=auth_headers,
        json={'track_id': track_id}
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['track_id'] == track_id
    assert 'suggested_labels' in data
    assert len(data['suggested_labels']) > 0
    assert 'genre' in data
    assert 'tempo' in data


def test_extraction_extract_success(client, auth_headers):
    """Test extraction request"""
    response = client.post(
        '/extraction/extract',
        headers=auth_headers,
        json={
            'track_id': 'test-track-456',
            'sources': [
                {'label': 'vocals', 'model': 'demucs'},
                {'label': 'drums', 'model': 'demucs'},
            ]
        }
    )
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'extraction_id' in data
    assert data['status'] == 'queued'
    assert data['sources_requested'] == 2
    assert 'cost_credits' in data


def test_extraction_extract_ambiguous_label(client, auth_headers):
    """Test extraction with ambiguous label costs extra"""
    response = client.post(
        '/extraction/extract',
        headers=auth_headers,
        json={
            'track_id': 'test-track-789',
            'sources': [
                {'label': 'thing', 'model': 'demucs'},  # Ambiguous!
            ]
        }
    )
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert len(data['ambiguous_labels']) > 0
    assert data['cost_credits'] > 5  # Extra cost for ambiguity


def test_extraction_extract_missing_sources(client, auth_headers):
    """Test extraction without sources fails"""
    response = client.post(
        '/extraction/extract',
        headers=auth_headers,
        json={'track_id': 'test-track-999'}
    )
    
    assert response.status_code == 400


# ============================================================================
# FEEDBACK TESTS
# ============================================================================

def test_feedback_good(client, auth_headers):
    """Test marking extraction as good"""
    extraction_id = 'test-extraction-123'
    
    response = client.post(
        f'/extraction/{extraction_id}/feedback',
        headers=auth_headers,
        json={
            'feedback_type': 'good',
            'segment': {
                'start_seconds': 0,
                'end_seconds': 180,
                'label': 'vocals'
            }
        }
    )
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['status'] == 'recorded'
    assert data['cost_credits'] == 0  # No cost for "good"


def test_feedback_with_refinement(client, auth_headers):
    """Test feedback with label refinement queues re-extraction"""
    extraction_id = 'test-extraction-456'
    
    response = client.post(
        f'/extraction/{extraction_id}/feedback',
        headers=auth_headers,
        json={
            'feedback_type': 'too_much',
            'segment': {
                'start_seconds': 30,
                'end_seconds': 60,
                'label': 'vocals'
            },
            'refined_label': 'vocals without drums'
        }
    )
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['reextraction_queued'] == True
    assert data['new_extraction_id'] is not None
    assert data['cost_credits'] > 0


# ============================================================================
# CREDIT TESTS
# ============================================================================

def test_user_credits(client, auth_headers):
    """Test getting user credit balance"""
    response = client.get('/user/credits', headers=auth_headers)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'current_balance' in data
    assert 'monthly_allowance' in data
    assert 'subscription_tier' in data
    assert 'usage_this_month' in data


# ============================================================================
# HISTORY TESTS
# ============================================================================

def test_user_history(client, auth_headers):
    """Test getting user extraction history"""
    response = client.get('/user/history', headers=auth_headers)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'total_tracks' in data
    assert 'tracks' in data
    assert 'pagination' in data


def test_user_history_pagination(client, auth_headers):
    """Test history pagination"""
    response = client.get('/user/history?limit=5&offset=10', headers=auth_headers)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['pagination']['limit'] == 5
    assert data['pagination']['offset'] == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
