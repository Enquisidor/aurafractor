"""Integration tests for API routes (mock mode, no real DB/GCS)."""

import pathlib
import uuid

_TESTS_DIR = pathlib.Path(__file__).parent
_SAMPLE_MP3 = _TESTS_DIR / 'sample.mp3'


class TestHealth:
    def test_health_ok(self, client):
        r = client.get('/health')
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] in ('ok', 'degraded')
        assert 'mock_mode' in data

    def test_metrics(self, client):
        r = client.get('/metrics')
        assert r.status_code == 200
        data = r.get_json()
        assert 'counters' in data


class TestAuth:
    def test_register_success(self, client):
        r = client.post('/auth/register', json={'device_id': 'test-device-001'})
        assert r.status_code == 201
        data = r.get_json()
        assert 'user_id' in data
        assert 'session_token' in data
        assert 'refresh_token' in data
        assert data['subscription_tier'] == 'free'
        assert data['credits_remaining'] == 100

    def test_register_missing_device_id(self, client):
        r = client.post('/auth/register', json={})
        assert r.status_code == 400

    def test_register_short_device_id(self, client):
        r = client.post('/auth/register', json={'device_id': 'ab'})
        assert r.status_code == 400

    def test_refresh_success(self, client):
        reg = client.post('/auth/register', json={'device_id': 'device-refresh-test'})
        refresh_token = reg.get_json()['refresh_token']
        r = client.post('/auth/refresh', json={'refresh_token': refresh_token})
        assert r.status_code == 200
        assert 'session_token' in r.get_json()

    def test_refresh_invalid_token(self, client):
        r = client.post('/auth/refresh', json={'refresh_token': 'bad.token.here'})
        assert r.status_code == 400

    def test_refresh_missing_token(self, client):
        r = client.post('/auth/refresh', json={})
        assert r.status_code == 400


class TestUpload:
    def test_upload_requires_auth(self, client):
        r = client.post('/upload')
        assert r.status_code == 401

    def test_upload_success(self, client, auth_headers):
        data = {'file': (_SAMPLE_MP3.read_bytes(), 'sample.mp3')}
        r = client.post('/upload', data=data, headers=auth_headers,
                        content_type='multipart/form-data')
        assert r.status_code == 201
        body = r.get_json()
        assert 'track_id' in body
        assert body['status'] == 'ready'

    def test_upload_no_file(self, client, auth_headers):
        r = client.post('/upload', data={}, headers=auth_headers,
                        content_type='multipart/form-data')
        assert r.status_code == 400

    def test_upload_unsupported_format(self, client, auth_headers):
        data = {'file': (b'data', 'track.exe')}
        r = client.post('/upload', data=data, headers=auth_headers,
                        content_type='multipart/form-data')
        assert r.status_code == 400


class TestExtraction:
    def test_suggest_labels_requires_auth(self, client):
        r = client.post('/extraction/suggest-labels', json={'track_id': str(uuid.uuid4())})
        assert r.status_code == 401

    def test_suggest_labels_success(self, client, auth_headers):
        r = client.post('/extraction/suggest-labels',
                        json={'track_id': str(uuid.uuid4())},
                        headers=auth_headers)
        assert r.status_code == 200
        data = r.get_json()
        assert 'suggested_labels' in data
        assert len(data['suggested_labels']) > 0

    def test_suggest_labels_missing_track_id(self, client, auth_headers):
        r = client.post('/extraction/suggest-labels', json={}, headers=auth_headers)
        assert r.status_code == 400

    def test_extract_success(self, client, auth_headers):
        r = client.post('/extraction/extract', json={
            'track_id': str(uuid.uuid4()),
            'sources': [{'label': 'vocals', 'model': 'demucs'}],
        }, headers=auth_headers)
        assert r.status_code == 201
        data = r.get_json()
        assert 'extraction_id' in data
        assert data['status'] == 'queued'

    def test_extract_missing_sources(self, client, auth_headers):
        r = client.post('/extraction/extract', json={
            'track_id': str(uuid.uuid4()),
            'sources': [],
        }, headers=auth_headers)
        assert r.status_code == 400

    def test_extract_invalid_model(self, client, auth_headers):
        r = client.post('/extraction/extract', json={
            'track_id': str(uuid.uuid4()),
            'sources': [{'label': 'vocals', 'model': 'unknownmodel'}],
        }, headers=auth_headers)
        assert r.status_code == 400

    def test_poll_status(self, client, auth_headers):
        extraction_id = str(uuid.uuid4())
        r = client.get(f'/extraction/{extraction_id}', headers=auth_headers)
        assert r.status_code == 200
        data = r.get_json()
        assert data['extraction_id'] == extraction_id
        assert data['status'] in ('queued', 'processing', 'completed')

    def test_poll_invalid_id(self, client, auth_headers):
        r = client.get('/extraction/not-a-uuid', headers=auth_headers)
        assert r.status_code == 400

    def test_feedback_good(self, client, auth_headers):
        extraction_id = str(uuid.uuid4())
        r = client.post(f'/extraction/{extraction_id}/feedback', json={
            'feedback_type': 'good',
            'segment_start_seconds': 0,
            'segment_end_seconds': 30,
            'segment_label': 'vocals',
        }, headers=auth_headers)
        assert r.status_code == 201
        data = r.get_json()
        assert data['status'] == 'recorded'

    def test_feedback_with_refined_label(self, client, auth_headers):
        extraction_id = str(uuid.uuid4())
        r = client.post(f'/extraction/{extraction_id}/feedback', json={
            'feedback_type': 'too_much',
            'segment_start_seconds': 0,
            'segment_end_seconds': 30,
            'segment_label': 'vocals',
            'refined_label': 'lead vocals',
        }, headers=auth_headers)
        assert r.status_code == 201
        data = r.get_json()
        assert data['reextraction_queued'] is True

    def test_feedback_invalid_type(self, client, auth_headers):
        r = client.post(f'/extraction/{str(uuid.uuid4())}/feedback', json={
            'feedback_type': 'terrible',
            'segment_start_seconds': 0,
            'segment_end_seconds': 10,
            'segment_label': 'vocals',
        }, headers=auth_headers)
        assert r.status_code == 400


class TestUser:
    def test_history_requires_auth(self, client):
        r = client.get('/user/history')
        assert r.status_code == 401

    def test_history_success(self, client, auth_headers):
        r = client.get('/user/history', headers=auth_headers)
        assert r.status_code == 200
        data = r.get_json()
        assert 'tracks' in data
        assert 'pagination' in data

    def test_credits_success(self, client, auth_headers):
        r = client.get('/user/credits', headers=auth_headers)
        assert r.status_code == 200
        data = r.get_json()
        assert 'current_balance' in data
        assert 'subscription_tier' in data

    def test_delete_track_success(self, client, auth_headers):
        track_id = str(uuid.uuid4())
        r = client.delete(f'/track/{track_id}', headers=auth_headers)
        assert r.status_code == 200
        data = r.get_json()
        assert data['track_id'] == track_id

    def test_delete_track_invalid_id(self, client, auth_headers):
        r = client.delete('/track/not-a-uuid', headers=auth_headers)
        assert r.status_code == 400


class TestWebhooks:
    def test_webhook_requires_worker_secret(self, client):
        r = client.post('/webhooks/extraction-complete', json={
            'extraction_id': str(uuid.uuid4()),
            'success': True,
            'sources': [],
        })
        assert r.status_code == 403

    def test_webhook_success(self, client, worker_headers):
        r = client.post('/webhooks/extraction-complete', json={
            'extraction_id': str(uuid.uuid4()),
            'success': True,
            'sources': [{'label': 'vocals', 'audio_url': 'gs://bucket/file.wav'}],
            'processing_time_seconds': 45,
        }, headers=worker_headers)
        assert r.status_code == 200
        assert r.get_json()['status'] == 'accepted'

    def test_webhook_failure(self, client, worker_headers):
        r = client.post('/webhooks/extraction-complete', json={
            'extraction_id': str(uuid.uuid4()),
            'success': False,
            'error_message': 'OOM',
        }, headers=worker_headers)
        assert r.status_code == 200
