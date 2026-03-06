"""
Structured logging setup.

Outputs JSON-structured logs compatible with Google Cloud Logging
in production; human-readable in development.
"""

import json
import logging
import os
import sys
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """Formats log records as JSON for GCP Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'severity': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'module': record.module,
            'line': record.lineno,
        }
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging(level: str = None) -> None:
    """Configure application-wide logging.

    Uses structured JSON in production, human-readable in development.
    """
    env = os.getenv('FLASK_ENV', 'production')
    log_level = level or os.getenv('LOG_LEVEL', 'INFO')

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)

    if env == 'development':
        fmt = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        handler.setFormatter(logging.Formatter(fmt, datefmt='%H:%M:%S'))
    else:
        handler.setFormatter(StructuredFormatter())

    # Remove existing handlers
    root_logger.handlers = []
    root_logger.addHandler(handler)

    # Quiet noisy libraries
    for noisy in ('urllib3', 'google.auth', 'google.cloud'):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info('Logging configured: env=%s level=%s', env, log_level)
