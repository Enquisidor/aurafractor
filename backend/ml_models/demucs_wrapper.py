"""
Demucs model wrapper.

Abstracts the Demucs source separation model. In mock mode returns
synthetic audio data without loading the model.
"""

import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

MOCK_MODE = os.getenv('ENABLE_MOCK_RESPONSES', 'false').lower() == 'true'

# Default Demucs model (htdemucs has 4 stems: drums, bass, other, vocals)
DEFAULT_MODEL = os.getenv('DEMUCS_MODEL', 'htdemucs')
SAMPLE_RATE = 44100

_model = None


def _get_model(model_name: str = DEFAULT_MODEL):
    """Lazy-load Demucs model."""
    global _model
    if _model is None:
        logger.info('Loading Demucs model: %s', model_name)
        import torch
        from demucs.pretrained import get_model
        _model = get_model(model_name)
        _model.eval()
        if torch.cuda.is_available():
            _model.cuda()
            logger.info('Demucs running on GPU')
        else:
            logger.info('Demucs running on CPU')
    return _model


def separate(
    audio_bytes: bytes,
    sources: List[Dict],
    sample_rate: int = SAMPLE_RATE,
) -> List[Dict]:
    """Run Demucs source separation.

    Args:
        audio_bytes: Raw WAV/MP3 audio bytes.
        sources: List of source dicts with 'label' and 'nlp_params'.
        sample_rate: Expected sample rate of the audio.

    Returns:
        List of dicts: {label, audio_bytes, duration_seconds, sample_rate}.
    """
    if MOCK_MODE:
        return _mock_separate(audio_bytes, sources)

    import torch
    import torchaudio
    from demucs.apply import apply_model
    from demucs.audio import AudioFile

    model = _get_model()

    # Write to temp file and load
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        wav, sr = torchaudio.load(tmp_path)
        if wav.dim() == 1:
            wav = wav.unsqueeze(0)  # Add channel dim
        if wav.shape[0] == 1:
            wav = wav.repeat(2, 1)  # Mono → stereo

        wav = wav.unsqueeze(0)  # Add batch dim: (1, 2, T)

        with torch.no_grad():
            stems = apply_model(model, wav, device='cuda' if torch.cuda.is_available() else 'cpu')

        # stems shape: (batch, sources, channels, time)
        stem_names = model.sources  # e.g. ['drums', 'bass', 'other', 'vocals']
        results = []

        for source in sources:
            label = source['label']
            stem_key = _map_label_to_stem(label, stem_names)

            if stem_key is not None:
                idx = stem_names.index(stem_key)
                stem_wav = stems[0, idx]  # (channels, time)
                audio_out = _tensor_to_wav_bytes(stem_wav, sr)
                duration = stem_wav.shape[-1] / sr
            else:
                # Unknown label – return silence
                logger.warning('No Demucs stem for label "%s", returning silence', label)
                duration = wav.shape[-1] / sr
                audio_out = _silence_wav_bytes(int(duration * sr), sr)

            results.append({
                'label': label,
                'audio_bytes': audio_out,
                'duration_seconds': int(duration),
                'sample_rate': sr,
                'model': 'demucs',
                'stem_used': stem_key,
            })

        return results

    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _map_label_to_stem(label: str, stem_names: List[str]) -> Optional[str]:
    """Map a user label to a Demucs stem name."""
    label_lower = label.lower()
    stem_map = {
        'vocal': 'vocals',
        'voice': 'vocals',
        'sing': 'vocals',
        'acapella': 'vocals',
        'drum': 'drums',
        'kick': 'drums',
        'snare': 'drums',
        'hi-hat': 'drums',
        'cymbal': 'drums',
        'percussion': 'drums',
        'bass': 'bass',
        'guitar': 'other',
        'synth': 'other',
        'piano': 'other',
        'keys': 'other',
        'strings': 'other',
        'brass': 'other',
        'other': 'other',
    }
    for keyword, stem in stem_map.items():
        if keyword in label_lower and stem in stem_names:
            return stem
    return None


def _tensor_to_wav_bytes(tensor, sample_rate: int) -> bytes:
    """Convert a PyTorch tensor to WAV bytes."""
    import torch
    import torchaudio
    buf = io.BytesIO()
    torchaudio.save(buf, tensor, sample_rate, format='wav')
    buf.seek(0)
    return buf.read()


def _silence_wav_bytes(num_samples: int, sample_rate: int) -> bytes:
    """Generate a silent WAV byte string."""
    import torch
    import torchaudio
    silence = torch.zeros(2, num_samples)
    buf = io.BytesIO()
    torchaudio.save(buf, silence, sample_rate, format='wav')
    buf.seek(0)
    return buf.read()


def _mock_separate(audio_bytes: bytes, sources: List[Dict]) -> List[Dict]:
    """Return synthetic results without loading the model."""
    logger.debug('[MOCK] Demucs would separate %d sources', len(sources))
    results = []
    for source in sources:
        results.append({
            'label': source['label'],
            'audio_bytes': b'MOCK_WAV_DATA',
            'duration_seconds': 180,
            'sample_rate': SAMPLE_RATE,
            'model': 'demucs',
            'stem_used': 'mock',
        })
    return results
