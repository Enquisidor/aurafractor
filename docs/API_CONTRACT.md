# API Contract

> Authoritative endpoint reference for the NLP instance and any downstream consumers.
> Full design rationale in [BACKEND_DESIGN.md](BACKEND_DESIGN.md).

Base URL: `https://<cloud-run-host>` (local dev: `http://localhost:5000`)

---

## Authentication

All endpoints except `/health`, `/auth/register`, and `/auth/refresh` require:

```
Authorization: Bearer <session_token>
```

Worker-only endpoints (`/webhooks/*`, `/worker/*`) require:

```
X-Worker-Secret: <WORKER_SECRET env var>
```

---

## Endpoints

### POST /auth/register

Register or log in an anonymous user.

**Request**
```json
{ "device_id": "string (≥4 chars)", "app_version": "string (optional)" }
```

**Response 201**
```json
{
  "user_id": "uuid",
  "session_token": "string",
  "refresh_token": "string",
  "expires_in": 86400,
  "subscription_tier": "free|pro|studio",
  "credits_remaining": 100,
  "is_new_user": true,
  "timestamp": "ISO8601"
}
```

---

### POST /auth/refresh

Exchange a refresh token for a new session token.

**Request**
```json
{ "refresh_token": "string" }
```

**Response 200**
```json
{ "session_token": "string", "expires_in": 86400 }
```

---

### POST /upload

Upload an audio file. Supported formats: `mp3`, `wav`, `flac`, `ogg`. Max 200 MB.

**Request** — `multipart/form-data`
- `file`: audio file

**Response 201**
```json
{
  "track_id": "uuid",
  "uploaded_at": "ISO8601",
  "duration_seconds": 180,
  "file_size_mb": 8.5,
  "audio_url": "https://...",
  "genre_detected": "indie_rock",
  "tempo_detected": 94,
  "status": "ready"
}
```

---

### POST /extraction/suggest-labels

Get AI-suggested instrument labels for a track (cached 24 h).

**Request**
```json
{ "track_id": "uuid" }
```

**Response 200**
```json
{
  "track_id": "uuid",
  "suggested_labels": [
    { "label": "lead vocals", "confidence": 0.94, "frequency_range": [85, 255], "recommended": true }
  ],
  "genre": "indie_rock",
  "tempo": 94,
  "user_history_suggestions": ["isolated bass"]
}
```

---

### POST /extraction/extract

Queue a source extraction job.

**Request**
```json
{
  "track_id": "uuid",
  "sources": [
    { "label": "lead vocals", "model": "demucs" },
    { "label": "bass", "model": "spleeter" }
  ],
  "force_ambiguous": false
}
```

- `model`: `demucs` | `spleeter` (default: `demucs`)
- `force_ambiguous`: proceed even if labels are ambiguous (costs extra credit)

**Response 201** (queued)
```json
{
  "extraction_id": "uuid",
  "track_id": "uuid",
  "job_id": "string",
  "status": "queued",
  "sources_requested": 2,
  "models_used": ["demucs"],
  "estimated_time_seconds": 120,
  "cost_credits": 10,
  "cost_breakdown": { "total_cost": 10, "base_cost": 10, "ambiguity_cost": 0, "ambiguous_labels": 0 },
  "ambiguous_labels": [],
  "queue_position": 1,
  "created_at": "ISO8601"
}
```

**Response 202** (awaiting confirmation — ambiguous labels detected)
```json
{
  "status": "awaiting_confirmation",
  "ambiguous_labels": [{ "label": "thing", "ambiguity_score": 0.95, "suggestion": "..." }],
  "message": "Set force_ambiguous=true to proceed."
}
```

---

### GET /extraction/{extraction_id}

Poll job status. Poll every 5 s until `status == "completed"` or `"failed"`.

**Response 200**
```json
{
  "extraction_id": "uuid",
  "track_id": "uuid",
  "status": "queued|processing|completed|failed",
  "created_at": "ISO8601",
  "started_at": "ISO8601|null",
  "completed_at": "ISO8601|null",
  "cost_credits": 10,
  "job_id": "string",
  "processing_time_seconds": 45,
  "results": {
    "sources": [
      {
        "label": "lead vocals",
        "model_used": "demucs",
        "audio_url": "https://...",
        "waveform_url": "https://...",
        "duration_seconds": 180,
        "sample_rate": 44100
      }
    ]
  }
}
```

`results` is only present when `status == "completed"`.

---

### POST /extraction/{extraction_id}/feedback

Submit feedback on an extraction segment.

**Request**
```json
{
  "feedback_type": "too_much|too_little|artifacts|good",
  "segment_start_seconds": 0,
  "segment_end_seconds": 30,
  "segment_label": "lead vocals",
  "feedback_detail": "string (optional)",
  "refined_label": "dry lead vocals (optional — triggers re-extraction)",
  "comment": "string (optional)"
}
```

**Response 201**
```json
{
  "feedback_id": "uuid",
  "extraction_id": "uuid",
  "status": "recorded|queued_for_reextraction",
  "reextraction_queued": true,
  "new_extraction_id": "uuid|null",
  "cost_credits": 20,
  "created_at": "ISO8601"
}
```

---

### GET /user/history

Paginated list of uploaded tracks with extraction summaries.

**Query params**: `limit` (1–100, default 20), `offset` (default 0)

**Response 200**
```json
{
  "total_tracks": 47,
  "tracks": [
    {
      "track_id": "uuid",
      "filename": "song.mp3",
      "uploaded_at": "ISO8601",
      "extractions_count": 3,
      "latest_extraction": { "extraction_id": "uuid", "status": "completed" }
    }
  ],
  "pagination": { "limit": 20, "offset": 0, "has_more": true }
}
```

---

### GET /user/credits

**Response 200**
```json
{
  "current_balance": 80,
  "monthly_allowance": 100,
  "subscription_tier": "free",
  "reset_date": "ISO8601",
  "usage_this_month": { "extractions": 4, "credits_spent": 20 },
  "recent_transactions": [
    { "amount": -10, "reason": "extraction", "balance_after": 80, "created_at": "ISO8601" }
  ]
}
```

---

### DELETE /track/{track_id}

Soft-delete a track and schedule GCS file deletion (GDPR right to erasure).

**Response 200**
```json
{
  "track_id": "uuid",
  "deleted_at": "ISO8601",
  "files_deleted": 12,
  "feedback_anonymized": true
}
```

---

## NLP Label Reference

The NLP engine maps free-form labels to extraction parameters. All 1-word instrument names are valid.

| Ambiguity Score | Examples | Behaviour |
|---|---|---|
| 0.0–0.2 | `vocals`, `kick drum`, `lead vocals without reverb` | Accepted as-is |
| 0.3–0.6 | unknown single word (e.g. `kazoo`) | Accepted with warning |
| 0.6–1.0 | `thing`, `stuff`, `sound` | Flagged — requires `force_ambiguous=true`, costs +1 credit |

Full rule table: [../backend/services/nlp.py](../backend/services/nlp.py)

---

## Credit Costs

| Operation | Credits |
|---|---|
| Single-source extraction | 5 |
| Multi-source extraction | 10 |
| Re-extraction | 20 |
| Ambiguous label surcharge | +1 per label |

---

## Error Responses

All errors follow:
```json
{ "error": "Human-readable message" }
```

| Status | Meaning |
|---|---|
| 400 | Validation error (message describes the issue) |
| 401 | Missing or invalid Bearer token |
| 403 | Worker secret mismatch |
| 404 | Resource not found |
| 500 | Internal server error |
