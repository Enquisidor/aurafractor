"""
Monitoring and metrics helpers.

Provides simple counters and gauges that can be read by /metrics endpoint.
In production these would ship to GCP Cloud Monitoring.
"""

import logging
import time
from collections import defaultdict
from threading import Lock
from typing import Dict

logger = logging.getLogger(__name__)

_counters: Dict[str, int] = defaultdict(int)
_gauges: Dict[str, float] = {}
_lock = Lock()


# ---------------------------------------------------------------------------
# Counter
# ---------------------------------------------------------------------------

def increment(name: str, value: int = 1, labels: Dict = None) -> None:
    """Increment a named counter."""
    key = _make_key(name, labels)
    with _lock:
        _counters[key] += value


def get_counter(name: str, labels: Dict = None) -> int:
    key = _make_key(name, labels)
    return _counters.get(key, 0)


# ---------------------------------------------------------------------------
# Gauge
# ---------------------------------------------------------------------------

def set_gauge(name: str, value: float, labels: Dict = None) -> None:
    """Set a named gauge value."""
    key = _make_key(name, labels)
    with _lock:
        _gauges[key] = value


def get_gauge(name: str, labels: Dict = None) -> float:
    key = _make_key(name, labels)
    return _gauges.get(key, 0.0)


# ---------------------------------------------------------------------------
# Timing context manager
# ---------------------------------------------------------------------------

class Timer:
    """Context manager to measure and record latency."""

    def __init__(self, metric_name: str, labels: Dict = None):
        self.metric_name = metric_name
        self.labels = labels or {}

    def __enter__(self):
        self._start = time.monotonic()
        return self

    def __exit__(self, *args):
        elapsed_ms = (time.monotonic() - self._start) * 1000
        set_gauge(self.metric_name, elapsed_ms, self.labels)
        logger.debug('%s took %.1fms', self.metric_name, elapsed_ms)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

def get_metrics_snapshot() -> Dict:
    """Return all current metric values."""
    with _lock:
        return {
            'counters': dict(_counters),
            'gauges': dict(_gauges),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_key(name: str, labels: Dict = None) -> str:
    if not labels:
        return name
    label_str = ','.join(f'{k}={v}' for k, v in sorted(labels.items()))
    return f'{name}{{{label_str}}}'
