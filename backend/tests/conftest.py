"""
Pytest fixtures shared across all test modules.

Uses ENABLE_MOCK_RESPONSES=true so no real DB or GCS is needed.
"""

import os
import pytest

# Force mock mode for all tests (override CI env vars where needed)
os.environ['ENABLE_MOCK_RESPONSES'] = 'true'
os.environ.setdefault('JWT_SECRET', 'test-secret')
os.environ['WORKER_SECRET'] = 'test-worker-secret'


@pytest.fixture
def app():
    from app import create_app
    return create_app(testing=True)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def mock_user_id():
    return 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'


@pytest.fixture
def auth_headers(mock_user_id):
    """Headers that pass the mock-mode auth check."""
    from services.auth import generate_session_token
    token, _ = generate_session_token(mock_user_id)
    return {
        'Authorization': f'Bearer {token}',
        'X-User-ID': mock_user_id,
    }


@pytest.fixture
def worker_headers():
    return {'X-Worker-Secret': os.environ['WORKER_SECRET']}
