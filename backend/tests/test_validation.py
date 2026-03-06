"""Unit tests for input validation utilities."""

import pytest
from utils.validation import (
    validate_uuid, validate_device_id, validate_audio_file,
    validate_sources, validate_feedback, validate_pagination,
)


class TestValidateUUID:
    def test_valid_uuid(self):
        uid = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
        assert validate_uuid(uid, 'field') == uid

    def test_invalid_uuid_raises(self):
        with pytest.raises(ValueError, match='valid UUID'):
            validate_uuid('not-a-uuid', 'field')

    def test_none_raises(self):
        with pytest.raises(ValueError):
            validate_uuid(None, 'field')


class TestValidateDeviceId:
    def test_valid(self):
        assert validate_device_id('device-abc-123') == 'device-abc-123'

    def test_strips_whitespace(self):
        assert validate_device_id('  abc123  ') == 'abc123'

    def test_too_short_raises(self):
        with pytest.raises(ValueError):
            validate_device_id('ab')

    def test_none_raises(self):
        with pytest.raises(ValueError):
            validate_device_id(None)

    def test_too_long_raises(self):
        with pytest.raises(ValueError):
            validate_device_id('x' * 256)


class TestValidateAudioFile:
    def test_valid_mp3(self):
        assert validate_audio_file('song.mp3', 1024 * 1024) == 'mp3'

    def test_valid_wav(self):
        assert validate_audio_file('track.wav', 1024) == 'wav'

    def test_unsupported_format_raises(self):
        with pytest.raises(ValueError, match='Unsupported'):
            validate_audio_file('file.exe', 100)

    def test_too_large_raises(self):
        with pytest.raises(ValueError, match='exceeds maximum'):
            validate_audio_file('big.wav', 201 * 1024 * 1024)


class TestValidateSources:
    def test_valid_single_source(self):
        result = validate_sources([{'label': 'vocals', 'model': 'demucs'}])
        assert len(result) == 1
        assert result[0]['label'] == 'vocals'

    def test_default_model_is_demucs(self):
        result = validate_sources([{'label': 'bass'}])
        assert result[0]['model'] == 'demucs'

    def test_empty_list_raises(self):
        with pytest.raises(ValueError):
            validate_sources([])

    def test_missing_label_raises(self):
        with pytest.raises(ValueError, match='label'):
            validate_sources([{'model': 'demucs'}])

    def test_invalid_model_raises(self):
        with pytest.raises(ValueError, match='model'):
            validate_sources([{'label': 'drums', 'model': 'unknown'}])

    def test_too_many_sources_raises(self):
        with pytest.raises(ValueError, match='Too many'):
            validate_sources([{'label': f'src{i}'} for i in range(11)])


class TestValidateFeedback:
    def _base(self, **overrides):
        base = {
            'feedback_type': 'too_much',
            'segment_start_seconds': 0,
            'segment_end_seconds': 10,
            'segment_label': 'vocals',
        }
        base.update(overrides)
        return base

    def test_valid_feedback(self):
        result = validate_feedback(self._base())
        assert result['feedback_type'] == 'too_much'

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            validate_feedback(self._base(feedback_type='bad_type'))

    def test_end_before_start_raises(self):
        with pytest.raises(ValueError):
            validate_feedback(self._base(segment_start_seconds=10, segment_end_seconds=5))

    def test_missing_label_raises(self):
        with pytest.raises(ValueError, match='segment_label'):
            validate_feedback(self._base(segment_label=''))

    def test_refined_label_stripped(self):
        result = validate_feedback(self._base(refined_label='  bass  '))
        assert result['refined_label'] == 'bass'


class TestValidatePagination:
    def test_defaults(self):
        limit, offset = validate_pagination(None, None)
        assert limit == 20
        assert offset == 0

    def test_clamped_max(self):
        limit, _ = validate_pagination(9999, 0)
        assert limit == 100

    def test_negative_offset_becomes_zero(self):
        _, offset = validate_pagination(10, -5)
        assert offset == 0
