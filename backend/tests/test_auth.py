"""Unit tests for auth service (token generation/verification)."""

import pytest
import time
from services.auth import (
    generate_session_token,
    generate_refresh_token,
    verify_session_token,
)


class TestTokenGeneration:
    def test_session_token_is_string(self):
        token, expires_at = generate_session_token('user-123')
        assert isinstance(token, str)
        assert len(token) > 0

    def test_refresh_token_is_string(self):
        token = generate_refresh_token('user-123')
        assert isinstance(token, str)

    def test_session_token_verifies(self):
        user_id = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
        token, _ = generate_session_token(user_id)
        result = verify_session_token(token)
        assert result == user_id

    def test_invalid_token_returns_none(self):
        assert verify_session_token('not.a.token') is None

    def test_refresh_token_not_valid_as_session(self):
        # Refresh tokens should not pass session validation
        token = generate_refresh_token('user-123')
        assert verify_session_token(token) is None

    def test_different_users_get_different_tokens(self):
        t1, _ = generate_session_token('user-aaa')
        t2, _ = generate_session_token('user-bbb')
        assert t1 != t2
