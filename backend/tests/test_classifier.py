"""Unit tests for instrument classifier (mock mode)."""

from ml_models.classifier import _mock_classify, _estimate_genre


class TestMockClassify:
    def test_returns_suggestions(self):
        result = _mock_classify()
        assert 'suggestions' in result
        assert len(result['suggestions']) > 0

    def test_suggestion_shape(self):
        for s in _mock_classify()['suggestions']:
            assert 'label' in s
            assert 'confidence' in s
            assert 0.0 <= s['confidence'] <= 1.0
            assert 'recommended' in s

    def test_returns_genre_and_tempo(self):
        result = _mock_classify()
        assert 'genre' in result
        assert isinstance(result['tempo'], int)


class TestGenreEstimate:
    def test_slow_ambient(self):
        bands = {k: 0.1 for k in ('sub_bass', 'bass', 'low_mid', 'mid', 'high_mid', 'presence', 'air')}
        assert _estimate_genre(60, bands) == 'ambient'

    def test_fast_edm(self):
        bands = {k: 0.0 for k in ('sub_bass', 'bass', 'low_mid', 'mid', 'high_mid', 'presence', 'air')}
        bands['sub_bass'] = 0.2
        bands['bass'] = 0.15
        assert _estimate_genre(140, bands) == 'edm'
