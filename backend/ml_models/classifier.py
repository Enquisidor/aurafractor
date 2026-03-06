"""
Instrument classifier.

Uses spectral analysis (via librosa) to detect instruments present in an
audio file and generate confidence-ranked label suggestions.

In mock mode, returns pre-defined suggestions.
"""

import io
import logging
import os
from typing import Dict, List

import numpy as np

logger = logging.getLogger(__name__)

MOCK_MODE = os.getenv('ENABLE_MOCK_RESPONSES', 'false').lower() == 'true'
SAMPLE_RATE = 44100


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_instruments(
    audio_bytes: bytes,
    top_k: int = 8,
) -> Dict:
    """Analyse audio and return instrument suggestions.

    Args:
        audio_bytes: Raw audio bytes (WAV/MP3/FLAC).
        top_k: Maximum number of suggestions to return.

    Returns:
        Dict with keys: suggestions, genre, tempo.
    """
    if MOCK_MODE or not audio_bytes:
        return _mock_classify()

    try:
        import librosa
        import librosa.display
    except ImportError:
        logger.warning('librosa not installed; returning mock suggestions')
        return _mock_classify()

    try:
        # Load audio
        y, sr = librosa.load(io.BytesIO(audio_bytes), sr=SAMPLE_RATE, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)

        # Tempo detection
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        tempo = int(round(float(tempo)))

        # Spectral features
        stft = np.abs(librosa.stft(y))
        freqs = librosa.fft_frequencies(sr=sr)

        # Compute energy in frequency bands
        bands = _frequency_band_energies(stft, freqs)

        # Detect instruments from bands
        suggestions = _detect_instruments_from_bands(bands, duration, top_k)

        # Genre heuristic
        genre = _estimate_genre(tempo, bands)

        return {
            'suggestions': suggestions,
            'genre': genre,
            'tempo': tempo,
            'duration_seconds': int(duration),
        }

    except Exception as exc:
        logger.error('Classifier error: %s', exc)
        return _mock_classify()


# ---------------------------------------------------------------------------
# Spectral analysis helpers
# ---------------------------------------------------------------------------

FREQUENCY_BANDS = {
    'sub_bass': (20, 60),
    'bass': (60, 250),
    'low_mid': (250, 500),
    'mid': (500, 2000),
    'high_mid': (2000, 4000),
    'presence': (4000, 8000),
    'air': (8000, 16000),
}


def _frequency_band_energies(stft: np.ndarray, freqs: np.ndarray) -> Dict[str, float]:
    """Compute normalized energy per frequency band."""
    energies = {}
    total = np.sum(stft) + 1e-8
    for band_name, (low, high) in FREQUENCY_BANDS.items():
        mask = (freqs >= low) & (freqs < high)
        energies[band_name] = float(np.sum(stft[mask]) / total)
    return energies


def _detect_instruments_from_bands(
    bands: Dict[str, float],
    duration: float,
    top_k: int,
) -> List[Dict]:
    """Map spectral energy patterns to instrument suggestions."""
    candidates = []

    # Vocal detection (presence + mid energy with moderate bass)
    vocal_score = bands['mid'] * 0.4 + bands['presence'] * 0.4 + bands['high_mid'] * 0.2
    if vocal_score > 0.05:
        candidates.append({
            'label': 'lead vocals',
            'confidence': min(0.98, vocal_score * 8),
            'frequency_range': [85, 8000],
            'recommended': vocal_score > 0.08,
        })

    # Kick drum (sub + bass energy, high attack)
    kick_score = bands['sub_bass'] * 0.6 + bands['bass'] * 0.4
    if kick_score > 0.05:
        candidates.append({
            'label': 'kick drum',
            'confidence': min(0.95, kick_score * 10),
            'frequency_range': [20, 100],
            'recommended': kick_score > 0.07,
        })

    # Snare (low-mid energy)
    snare_score = bands['low_mid'] * 0.5 + bands['mid'] * 0.3 + bands['presence'] * 0.2
    if snare_score > 0.03:
        candidates.append({
            'label': 'snare',
            'confidence': min(0.90, snare_score * 12),
            'frequency_range': [100, 5000],
            'recommended': snare_score > 0.05,
        })

    # Hi-hats (presence + air)
    hihat_score = bands['presence'] * 0.5 + bands['air'] * 0.5
    if hihat_score > 0.02:
        candidates.append({
            'label': 'hi-hats',
            'confidence': min(0.85, hihat_score * 15),
            'frequency_range': [4000, 16000],
            'recommended': hihat_score > 0.04,
        })

    # Bass guitar / synth bass
    bass_score = bands['bass'] * 0.7 + bands['sub_bass'] * 0.3
    if bass_score > 0.06:
        candidates.append({
            'label': 'bass',
            'confidence': min(0.92, bass_score * 9),
            'frequency_range': [30, 250],
            'recommended': bass_score > 0.09,
        })

    # Synth / pad (mid + high-mid, sustained)
    synth_score = bands['mid'] * 0.35 + bands['high_mid'] * 0.35 + bands['presence'] * 0.30
    if synth_score > 0.04:
        candidates.append({
            'label': 'synth pad',
            'confidence': min(0.82, synth_score * 10),
            'frequency_range': [200, 8000],
            'recommended': synth_score > 0.06,
        })

    # Guitar (mid + presence)
    guitar_score = bands['mid'] * 0.5 + bands['presence'] * 0.3 + bands['high_mid'] * 0.2
    if guitar_score > 0.04:
        candidates.append({
            'label': 'guitar',
            'confidence': min(0.80, guitar_score * 9),
            'frequency_range': [80, 6000],
            'recommended': guitar_score > 0.06,
        })

    # Sort by confidence descending, cap at top_k
    candidates.sort(key=lambda x: x['confidence'], reverse=True)
    return candidates[:top_k]


def _estimate_genre(tempo: int, bands: Dict[str, float]) -> str:
    """Heuristic genre classification from tempo + spectral profile."""
    bass_heavy = bands['sub_bass'] + bands['bass'] > 0.25

    if tempo < 80:
        return 'ambient'
    if 80 <= tempo < 100:
        return 'hip_hop' if bass_heavy else 'pop'
    if 100 <= tempo < 130:
        return 'pop' if not bass_heavy else 'r_and_b'
    if 130 <= tempo < 160:
        return 'edm' if bass_heavy else 'indie_rock'
    if tempo >= 160:
        return 'drum_and_bass' if bass_heavy else 'metal'
    return 'unknown'


def get_user_history_suggestions(user_id: str, limit: int = 5) -> List[str]:
    """Return previously used labels for this user (for suggestion UI)."""
    try:
        from database.connection import execute_query
        sql = """
            SELECT DISTINCT f.segment_label
            FROM feedback f
            WHERE f.user_id = %s AND f.refined_label IS NOT NULL
            ORDER BY f.segment_label
            LIMIT %s
        """
        rows = execute_query(sql, (user_id, limit)) or []
        return [r['segment_label'] for r in rows]
    except Exception as exc:
        logger.warning('Could not fetch user history suggestions: %s', exc)
        return []


# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------

def _mock_classify() -> Dict:
    return {
        'suggestions': [
            {'label': 'lead vocals', 'confidence': 0.94, 'frequency_range': [85, 8000], 'recommended': True},
            {'label': 'kick drum', 'confidence': 0.89, 'frequency_range': [20, 100], 'recommended': True},
            {'label': 'snare', 'confidence': 0.81, 'frequency_range': [100, 5000], 'recommended': False},
            {'label': 'bass', 'confidence': 0.76, 'frequency_range': [30, 250], 'recommended': True},
            {'label': 'synth pad', 'confidence': 0.68, 'frequency_range': [200, 8000], 'recommended': True},
        ],
        'genre': 'indie_rock',
        'tempo': 94,
        'duration_seconds': 180,
    }
