"""
NLP label interpretation service.

Wraps the rule engine from app.py with additional functionality:
  - Ambiguity scoring with context
  - Label normalization
  - Training data point construction
"""

import hashlib
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rule tables (single source of truth – moved here from app.py)
# ---------------------------------------------------------------------------

NLP_RULES: Dict[str, Dict[str, Any]] = {
    # Vocals
    'vocals': {'source': 'vocal', 'isolation_level': 0.7, 'dryness': 0.5, 'preserve_reverb': True},
    'lead vocals': {'source': 'vocal', 'vocal_type': 'lead', 'isolation_level': 0.85, 'dryness': 0.5, 'preserve_reverb': True},
    'lead vocals without reverb': {'source': 'vocal', 'vocal_type': 'lead', 'isolation_level': 0.9, 'dryness': 0.95, 'preserve_reverb': False},
    'backing vocals': {'source': 'vocal', 'vocal_type': 'backing', 'isolation_level': 0.75, 'dryness': 0.5, 'preserve_reverb': True},
    'isolated vocals': {'source': 'vocal', 'isolation_level': 0.95, 'dryness': 0.8, 'separation_aggression': 0.9},
    'dry vocals': {'source': 'vocal', 'isolation_level': 0.85, 'dryness': 0.9, 'preserve_reverb': False},
    'acapella': {'source': 'vocal', 'isolation_level': 0.95, 'dryness': 0.5, 'separation_aggression': 0.95},

    # Drums
    'drums': {'source': 'drum', 'isolation_level': 0.7, 'attack_preservation': 0.8},
    'kick': {'source': 'drum', 'drum_type': 'kick', 'isolation_level': 0.85, 'frequency_range': [20, 100]},
    'kick drum': {'source': 'drum', 'drum_type': 'kick', 'isolation_level': 0.85, 'frequency_range': [20, 100]},
    'tight kick': {'source': 'drum', 'drum_type': 'kick', 'isolation_level': 0.9, 'attack_preservation': 1.0, 'bleed_suppression': 0.95},
    'snare': {'source': 'drum', 'drum_type': 'snare', 'isolation_level': 0.75, 'frequency_range': [100, 5000]},
    'hi-hats': {'source': 'drum', 'drum_type': 'hi_hat', 'isolation_level': 0.8, 'frequency_range': [4000, 16000]},
    'hi-hat': {'source': 'drum', 'drum_type': 'hi_hat', 'isolation_level': 0.8, 'frequency_range': [4000, 16000]},
    'cymbals': {'source': 'drum', 'drum_type': 'cymbal', 'isolation_level': 0.75, 'frequency_range': [3000, 20000]},
    'overhead': {'source': 'drum', 'drum_type': 'overhead', 'isolation_level': 0.7, 'frequency_range': [2000, 20000]},

    # Bass
    'bass': {'source': 'bass', 'isolation_level': 0.75, 'frequency_range': [20, 250]},
    'bass guitar': {'source': 'bass', 'bass_type': 'guitar', 'isolation_level': 0.75},
    'bass synth': {'source': 'bass', 'bass_type': 'synth', 'isolation_level': 0.75},
    'sub bass': {'source': 'bass', 'bass_type': 'sub', 'isolation_level': 0.8, 'frequency_range': [20, 80]},

    # Synths / keys
    'synth': {'source': 'other', 'synth_type': 'synth', 'isolation_level': 0.7},
    'pad': {'source': 'other', 'synth_type': 'pad', 'isolation_level': 0.7},
    'synth pad': {'source': 'other', 'synth_type': 'pad', 'isolation_level': 0.7},
    'lead synth': {'source': 'other', 'synth_type': 'lead', 'isolation_level': 0.75},
    'arp': {'source': 'other', 'synth_type': 'arp', 'isolation_level': 0.7},
    'piano': {'source': 'other', 'instrument_type': 'piano', 'isolation_level': 0.7},
    'keys': {'source': 'other', 'instrument_type': 'keys', 'isolation_level': 0.7},
    'organ': {'source': 'other', 'instrument_type': 'organ', 'isolation_level': 0.7},
    'rhodes': {'source': 'other', 'instrument_type': 'rhodes', 'isolation_level': 0.7},

    # Guitars
    'guitar': {'source': 'other', 'instrument_type': 'guitar', 'isolation_level': 0.7},
    'electric guitar': {'source': 'other', 'instrument_type': 'guitar', 'guitar_type': 'electric', 'isolation_level': 0.75},
    'acoustic guitar': {'source': 'other', 'instrument_type': 'guitar', 'guitar_type': 'acoustic', 'isolation_level': 0.7},
    'rhythm guitar': {'source': 'other', 'instrument_type': 'guitar', 'guitar_type': 'rhythm', 'isolation_level': 0.7},
    'lead guitar': {'source': 'other', 'instrument_type': 'guitar', 'guitar_type': 'lead', 'isolation_level': 0.75},

    # Orchestral
    'strings': {'source': 'other', 'instrument_type': 'strings', 'isolation_level': 0.7},
    'violins': {'source': 'other', 'instrument_type': 'violin', 'isolation_level': 0.7},
    'brass': {'source': 'other', 'instrument_type': 'brass', 'isolation_level': 0.7},
    'horns': {'source': 'other', 'instrument_type': 'horn', 'isolation_level': 0.7},

    # Percussion
    'percussion': {'source': 'other', 'instrument_type': 'percussion', 'isolation_level': 0.7},
    'shaker': {'source': 'other', 'instrument_type': 'shaker', 'isolation_level': 0.7},
    'tambourine': {'source': 'other', 'instrument_type': 'tambourine', 'isolation_level': 0.7},

    # Misc
    'other': {'source': 'other', 'isolation_level': 0.6},
}

DESCRIPTORS: Dict[str, Dict[str, Any]] = {
    'dry': {'dryness': 0.3},
    'wet': {'dryness': -0.3},
    'tight': {'isolation_level': 0.2, 'attack_preservation': 0.2},
    'loose': {'isolation_level': -0.2},
    'isolated': {'isolation_level': 0.25},
    'clean': {'bleed_suppression': 0.2},
    'reverb': {},  # Context word; handled by 'without reverb'
    'without reverb': {'dryness': 0.4, 'preserve_reverb': False},
    'with reverb': {'preserve_reverb': True},
    'only': {'mask_everything_else': True},
    'just': {'mask_everything_else': True},
}

VAGUE_WORDS = {'thing', 'stuff', 'sound', 'whatever', 'music', 'audio', 'noise', 'track'}

COMMON_INSTRUMENTS = set(NLP_RULES.keys())


def parse_label_to_params(label: str) -> Dict[str, Any]:
    """Convert a user label to NLP extraction parameters.

    Returns a params dict. If the label is completely unknown/unresolvable,
    returns a dict with 'ambiguous': True.
    """
    label_lower = label.lower().strip()

    # Exact match
    if label_lower in NLP_RULES:
        return NLP_RULES[label_lower].copy()

    # Partial match (find the longest matching rule key)
    best_key: Optional[str] = None
    best_len = 0
    for rule_key in NLP_RULES:
        if rule_key in label_lower and len(rule_key) > best_len:
            best_key = rule_key
            best_len = len(rule_key)

    if best_key:
        params = NLP_RULES[best_key].copy()
        # Apply modifier descriptors
        for descriptor, modifier in DESCRIPTORS.items():
            if descriptor in label_lower:
                for k, v in modifier.items():
                    if isinstance(v, (int, float)):
                        params[k] = min(1.0, max(0.0, params.get(k, 0.5) + v))
                    else:
                        params[k] = v
        return params

    # No match
    return {
        'ambiguous': True,
        'user_label': label,
        'confidence': 0.0,
        'requires_clarification': True,
    }


def compute_ambiguity_score(label: str) -> float:
    """Score label ambiguity from 0.0 (crystal clear) to 1.0 (useless).

    All 1-word instrument names are valid. Only truly vague inputs score high.
    """
    label_lower = label.lower().strip()

    if not label_lower:
        return 1.0

    # Exact known label
    if label_lower in NLP_RULES:
        return 0.1

    # Vague single words
    if label_lower in VAGUE_WORDS:
        return 0.95

    # Contains a vague word among others
    words = set(label_lower.split())
    if words & VAGUE_WORDS:
        return 0.8

    # Multi-word label that partially matches a rule
    for rule_key in NLP_RULES:
        if rule_key in label_lower:
            return 0.2  # Modified known label – fairly clear

    # Multi-word but no match
    if len(label_lower.split()) > 1:
        return 0.5

    # Unknown single word
    return 0.4


def normalize_label(label: str) -> str:
    """Return a canonical lowercase, stripped version of the label."""
    return label.lower().strip()


def suggest_clarification(label: str) -> str:
    """Provide a human-readable clarification hint for an ambiguous label."""
    label_lower = label.lower().strip()
    if label_lower in VAGUE_WORDS:
        return f'"{label}" is too vague. Try a specific instrument like "lead vocals" or "kick drum".'
    words = set(label_lower.split())
    if words & VAGUE_WORDS:
        return f'Try removing vague terms from "{label}" and use a specific instrument name.'
    return f'"{label}" is not recognised. Use an instrument name like "vocals", "drums", or "synth".'


def build_training_point(
    user_id: str,
    original_label: str,
    nlp_params: Dict,
    feedback_type: Optional[str] = None,
    feedback_detail: Optional[str] = None,
    refined_label: Optional[str] = None,
    user_accepted: Optional[bool] = None,
    genre: Optional[str] = None,
    tempo: Optional[int] = None,
    opt_in: bool = False,
) -> Dict:
    """Construct an anonymized training data point for model improvement.

    User ID is hashed (non-reversible) to preserve privacy.
    """
    user_id_anon = hashlib.sha256(user_id.encode()).hexdigest()[:8]
    is_ambiguous = compute_ambiguity_score(original_label) > 0.6

    return {
        'user_id_anon': user_id_anon,
        'original_label': original_label,
        'nlp_params': nlp_params,
        'feedback_type': feedback_type,
        'feedback_detail': feedback_detail,
        'refined_label': refined_label,
        'user_accepted': user_accepted,
        'genre': genre,
        'tempo': tempo,
        'is_ambiguous': is_ambiguous,
        'opt_in': opt_in,
    }
