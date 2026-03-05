"""Unit tests for credit cost computation."""

import pytest
from services.credits import compute_extraction_cost, CREDIT_COSTS


class TestComputeExtractionCost:
    def test_single_clear_source(self):
        sources = [{'label': 'vocals', 'ambiguous': False}]
        result = compute_extraction_cost(sources)
        assert result['total_cost'] == CREDIT_COSTS['basic']
        assert result['ambiguity_cost'] == 0

    def test_multi_source(self):
        sources = [
            {'label': 'vocals', 'ambiguous': False},
            {'label': 'drums', 'ambiguous': False},
        ]
        result = compute_extraction_cost(sources)
        assert result['base_cost'] == CREDIT_COSTS['multi']

    def test_ambiguous_source_costs_extra(self):
        sources = [{'label': 'thing', 'ambiguous': True}]
        result = compute_extraction_cost(sources)
        assert result['ambiguity_cost'] == CREDIT_COSTS['ambiguous']
        assert result['total_cost'] == CREDIT_COSTS['basic'] + CREDIT_COSTS['ambiguous']

    def test_multiple_ambiguous(self):
        sources = [
            {'label': 'thing', 'ambiguous': True},
            {'label': 'stuff', 'ambiguous': True},
        ]
        result = compute_extraction_cost(sources)
        assert result['ambiguous_labels'] == 2
        assert result['ambiguity_cost'] == 2 * CREDIT_COSTS['ambiguous']

    def test_reextraction_uses_complex_cost(self):
        sources = [{'label': 'vocals', 'ambiguous': False}]
        result = compute_extraction_cost(sources, is_reextraction=True)
        assert result['base_cost'] == CREDIT_COSTS['complex']

    def test_breakdown_sums_correctly(self):
        sources = [{'label': 'stuff', 'ambiguous': True}, {'label': 'vocals', 'ambiguous': False}]
        result = compute_extraction_cost(sources)
        assert result['total_cost'] == result['base_cost'] + result['ambiguity_cost']
