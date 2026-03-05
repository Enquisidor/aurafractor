"""Unit tests for NLP label interpretation and ambiguity scoring."""

import pytest
from services.nlp import parse_label_to_params, compute_ambiguity_score, normalize_label, suggest_clarification


# ---------------------------------------------------------------------------
# compute_ambiguity_score
# ---------------------------------------------------------------------------

class TestAmbiguityScore:
    def test_known_instrument_is_clear(self):
        assert compute_ambiguity_score('vocals') == pytest.approx(0.1)

    def test_known_multiword_is_clear(self):
        assert compute_ambiguity_score('lead vocals') <= 0.3

    def test_vague_word_is_ambiguous(self):
        assert compute_ambiguity_score('thing') > 0.6

    def test_stuff_is_ambiguous(self):
        assert compute_ambiguity_score('stuff') > 0.6

    def test_unknown_single_word_is_moderate(self):
        score = compute_ambiguity_score('flooglehorn')
        assert 0.3 <= score <= 0.6

    def test_empty_string_is_max(self):
        assert compute_ambiguity_score('') == pytest.approx(1.0)

    def test_exact_rule_match_is_clear(self):
        for label in ('drums', 'bass', 'guitar', 'piano', 'synth'):
            assert compute_ambiguity_score(label) <= 0.2

    def test_modified_known_label_is_clear(self):
        assert compute_ambiguity_score('tight kick') <= 0.3

    def test_case_insensitive(self):
        assert compute_ambiguity_score('VOCALS') == compute_ambiguity_score('vocals')


# ---------------------------------------------------------------------------
# parse_label_to_params
# ---------------------------------------------------------------------------

class TestParseLabelToParams:
    def test_exact_match_vocals(self):
        params = parse_label_to_params('vocals')
        assert params['source'] == 'vocal'
        assert 'isolation_level' in params

    def test_exact_match_drums(self):
        params = parse_label_to_params('drums')
        assert params['source'] == 'drum'

    def test_exact_match_bass(self):
        params = parse_label_to_params('bass')
        assert params['source'] == 'bass'

    def test_multiword_lead_vocals(self):
        params = parse_label_to_params('lead vocals')
        assert params['source'] == 'vocal'
        assert params.get('vocal_type') == 'lead'

    def test_lead_vocals_without_reverb(self):
        params = parse_label_to_params('lead vocals without reverb')
        assert params.get('preserve_reverb') is False
        assert params.get('dryness', 0) > 0.8

    def test_partial_match_uses_best_key(self):
        params = parse_label_to_params('some kick drum sound')
        assert params['source'] == 'drum'

    def test_unknown_label_returns_ambiguous(self):
        params = parse_label_to_params('kazoo solo')
        assert params.get('ambiguous') is True
        assert params.get('requires_clarification') is True

    def test_isolation_level_clamped(self):
        params = parse_label_to_params('isolated tight kick')
        level = params.get('isolation_level', 0)
        assert 0.0 <= level <= 1.0

    def test_case_insensitive(self):
        assert parse_label_to_params('VOCALS') == parse_label_to_params('vocals')


# ---------------------------------------------------------------------------
# normalize_label / suggest_clarification
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_normalize_strips_and_lowercases(self):
        assert normalize_label('  LEAD VOCALS  ') == 'lead vocals'

    def test_clarification_for_vague(self):
        msg = suggest_clarification('thing')
        assert 'vague' in msg.lower() or 'specific' in msg.lower()

    def test_clarification_for_unknown(self):
        msg = suggest_clarification('flooglehorn')
        assert 'flooglehorn' in msg
