"""
Spleeter model wrapper.

Abstracts the Spleeter source separation model. Spleeter offers
2stems, 4stems, and 5stems configurations.
"""

import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

MOCK_MODE = os.getenv('ENABLE_MOCK_RESPONSES', 'false').lower() == 'true'
SAMPLE_RATE = 44100

# Spleeter stem configurations
STEM_CONFIGS = {
    2: ['vocals', 'accompaniment'],
    4: ['vocals', 'drums', 'bass', 'other'],
    5: ['vocals', 'drums', 'bass', 'piano', 'other'],
}


def separate(
    audio_bytes: bytes,
    sources: List[Dict],
    stems: int = 4,
) -> List[Dict]:
    """Run Spleeter source separation.

    Args:
        audio_bytes: Raw WAV/MP3 audio bytes.
        sources: List of source dicts with 'label' and 'nlp_params'.
        stems: Number of stems (2, 4, or 5).

    Returns:
        List of dicts: {label, audio_bytes, duration_seconds, sample_rate}.
    """
    if MOCK_MODE:
        return _mock_separate(audio_bytes, sources)

    from spleeter.separator import Separator
    from spleeter.audio.adapter import AudioAdapter

    separator = Separator(f'spleeter:{stems}stems')
    adapter = AudioAdapter.default()

    # Load audio
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        waveform, sr = adapter.load(tmp_path, sample_rate=SAMPLE_RATE)
        # waveform shape: (samples, channels)

        prediction = separator.separate(waveform)
        # prediction: dict {stem_name: np.ndarray (samples, channels)}

        available_stems = STEM_CONFIGS.get(stems, STEM_CONFIGS[4])
        results = []

        for source in sources:
            label = source['label']
            stem_key = _map_label_to_stem(label, available_stems)

            if stem_key and stem_key in prediction:
                stem_wav = prediction[stem_key]
                audio_out = _ndarray_to_wav_bytes(stem_wav, SAMPLE_RATE)
                duration = stem_wav.shape[0] / SAMPLE_RATE
            else:
                logger.warning('No Spleeter stem for label "%s"', label)
                duration = waveform.shape[0] / SAMPLE_RATE
                audio_out = _silence_wav_bytes(int(duration * SAMPLE_RATE))

            results.append({
                'label': label,
                'audio_bytes': audio_out,
                'duration_seconds': int(duration),
                'sample_rate': SAMPLE_RATE,
                'model': 'spleeter',
                'stem_used': stem_key,
            })

        return results

    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _map_label_to_stem(label: str, available_stems: List[str]) -> Optional[str]:
    """Map user label to a Spleeter stem."""
    label_lower = label.lower()
    stem_map = {
        'vocal': 'vocals',
        'voice': 'vocals',
        'acapella': 'vocals',
        'drum': 'drums',
        'kick': 'drums',
        'snare': 'drums',
        'percussion': 'drums',
        'bass': 'bass',
        'piano': 'piano',
        'keys': 'piano',
        'guitar': 'other',
        'synth': 'other',
        'strings': 'other',
        'other': 'other',
        'accompan': 'accompaniment',
    }
    for keyword, stem in stem_map.items():
        if keyword in label_lower and stem in available_stems:
            return stem
    return 'other' if 'other' in available_stems else None


def _ndarray_to_wav_bytes(array: np.ndarray, sample_rate: int) -> bytes:
    """Convert numpy array to WAV bytes via soundfile."""
    import soundfile as sf
    buf = io.BytesIO()
    sf.write(buf, array, sample_rate, format='WAV')
    buf.seek(0)
    return buf.read()


def _silence_wav_bytes(num_samples: int, channels: int = 2) -> bytes:
    """Generate a silent WAV byte string."""
    silence = np.zeros((num_samples, channels), dtype=np.float32)
    return _ndarray_to_wav_bytes(silence, SAMPLE_RATE)


def _mock_separate(audio_bytes: bytes, sources: List[Dict]) -> List[Dict]:
    logger.debug('[MOCK] Spleeter would separate %d sources', len(sources))
    return [
        {
            'label': s['label'],
            'audio_bytes': b'MOCK_WAV_DATA',
            'duration_seconds': 180,
            'sample_rate': SAMPLE_RATE,
            'model': 'spleeter',
            'stem_used': 'mock',
        }
        for s in sources
    ]
