"""
Google Cloud Tasks integration.

In mock mode, logs the task and returns a fake job ID.
In production, creates a Cloud Tasks HTTP task targeting the worker endpoint.
"""

import json
import logging
import os
from typing import Dict, List

logger = logging.getLogger(__name__)

MOCK_MODE = os.getenv('ENABLE_MOCK_RESPONSES', 'false').lower() == 'true'
GCP_PROJECT = os.getenv('GCP_PROJECT', 'music-separation-dev')
GCP_LOCATION = os.getenv('GCP_LOCATION', 'us-central1')
TASKS_QUEUE = os.getenv('CLOUD_TASKS_QUEUE', 'extraction-jobs')
WORKER_URL = os.getenv('WORKER_URL', 'http://localhost:5001/worker/extract')

_tasks_client = None


def _get_tasks_client():
    """Lazy-initialize Cloud Tasks client."""
    global _tasks_client
    if _tasks_client is None:
        from google.cloud import tasks_v2
        _tasks_client = tasks_v2.CloudTasksClient()
    return _tasks_client


def enqueue_extraction_job(
    extraction_id: str,
    track_id: str,
    gcs_path: str,
    sources: List[Dict],
) -> str:
    """Create a Cloud Tasks job for an extraction.

    Returns the job ID string.
    """
    payload = {
        'extraction_id': extraction_id,
        'track_id': track_id,
        'gcs_path': gcs_path,
        'sources': sources,
    }

    if MOCK_MODE:
        job_id = f'mock-job-{extraction_id[:8]}'
        logger.info('[MOCK] Would enqueue extraction job: %s payload=%s', job_id, json.dumps(payload)[:100])
        return job_id

    client = _get_tasks_client()
    parent = client.queue_path(GCP_PROJECT, GCP_LOCATION, TASKS_QUEUE)

    task = {
        'http_request': {
            'http_method': 'POST',
            'url': WORKER_URL,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(payload).encode(),
        }
    }

    response = client.create_task(request={'parent': parent, 'task': task})
    # Task name format: projects/{proj}/locations/{loc}/queues/{q}/tasks/{id}
    job_id = response.name.split('/')[-1]
    logger.info('Enqueued Cloud Task job_id=%s for extraction_id=%s', job_id, extraction_id)
    return job_id


def enqueue_reextraction_job(
    extraction_id: str,
    track_id: str,
    gcs_path: str,
    sources: List[Dict],
    feedback_id: str,
) -> str:
    """Enqueue a re-extraction job (same as extraction but carries feedback_id)."""
    payload = {
        'extraction_id': extraction_id,
        'track_id': track_id,
        'gcs_path': gcs_path,
        'sources': sources,
        'feedback_id': feedback_id,
        'is_reextraction': True,
    }

    if MOCK_MODE:
        job_id = f'mock-reextract-{extraction_id[:8]}'
        logger.info('[MOCK] Would enqueue re-extraction job: %s', job_id)
        return job_id

    client = _get_tasks_client()
    parent = client.queue_path(GCP_PROJECT, GCP_LOCATION, TASKS_QUEUE)
    task = {
        'http_request': {
            'http_method': 'POST',
            'url': WORKER_URL,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(payload).encode(),
        }
    }
    response = client.create_task(request={'parent': parent, 'task': task})
    return response.name.split('/')[-1]
