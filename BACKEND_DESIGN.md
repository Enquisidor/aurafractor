# Music Source Separation Tool - Backend Design

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Native Mobile                       │
│                                                                   │
│  [Upload] → [Select Models] → [Play Results] → [Refine Labels]  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ HTTPS (gRPC preferred for streaming)
                 │
┌────────────────▼────────────────────────────────────────────────┐
│                    Cloud Run API (Python)                        │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   /upload    │  │  /extract    │  │  /feedback   │  ...      │
│  │   POST       │  │   POST       │  │   POST       │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│         │                 │                  │                   │
│         └─────────────────┼──────────────────┘                   │
│                           │                                      │
└───────────────────────────┼──────────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
    ┌────▼─────┐      ┌─────▼──────┐    ┌────▼─────┐
    │ Firestore│      │ Cloud Tasks│    │ GCS      │
    │ (metadata)      │ (job queue)│    │(audio)   │
    └──────────┘      └────────────┘    └──────────┘
         │                  │
         └──────────────────┼──────────────────┐
                            │                  │
                    ┌───────▼───────┐  ┌───────▼───────┐
                    │ Worker Pool   │  │ Worker Pool   │
                    │ (Cloud Run)   │  │ (Cloud Run)   │
                    │ Demucs        │  │ Spleeter      │
                    └───────────────┘  └───────────────┘
```

---

## API Contract

### Authentication
- User ID (UUID, generated on first app launch)
- Session token (short-lived, refresh token pattern)
- API key for backend-to-backend calls

```
Headers:
  Authorization: Bearer <session_token>
  X-User-ID: <uuid>
  X-Client-Version: <semver>
```

---

### Endpoints

#### 1. **POST /auth/register**
Register/initialize user (anonymous)

**Request:**
```json
{
  "device_id": "string",
  "app_version": "1.0.0"
}
```

**Response:**
```json
{
  "user_id": "uuid",
  "session_token": "jwt",
  "refresh_token": "jwt",
  "subscription_tier": "free|pro|studio",
  "credits_remaining": 100
}
```

**Behavior:**
- Generate user UUID
- Create Firestore doc: `/users/{user_id}`
- Track: device_id, app_version, created_at, subscription_tier
- Initialize credit balance (free tier: 100/month)

---

#### 2. **POST /auth/refresh**
Refresh session token

**Request:**
```json
{
  "refresh_token": "jwt"
}
```

**Response:**
```json
{
  "session_token": "jwt",
  "expires_in": 3600
}
```

---

#### 3. **POST /upload**
Upload audio file for processing

**Request:**
```
Content-Type: multipart/form-data

file: <audio.mp3/wav/flac>
metadata: {
  filename: "string",
  duration_seconds: number,
  sample_rate: 44100 | 48000,
  format: "mp3" | "wav" | "flac"
}
```

**Response:**
```json
{
  "track_id": "uuid",
  "uploaded_at": "2024-03-05T10:30:00Z",
  "duration_seconds": 180,
  "file_size_mb": 8.5,
  "audio_url": "gs://bucket/tracks/{track_id}/original.wav",
  "status": "ready"
}
```

**Behavior:**
- Validate audio (duration < 10min for free, < 60min for pro)
- Store original in GCS: `gs://bucket/tracks/{track_id}/original.{ext}`
- Convert to 44.1kHz WAV for processing (if needed)
- Create Firestore doc: `/users/{user_id}/tracks/{track_id}`
- Return metadata + signed URL for playback

---

#### 4. **POST /extraction/suggest-labels**
Get AI-suggested instrument labels for uploaded track

**Request:**
```json
{
  "track_id": "uuid"
}
```

**Response:**
```json
{
  "track_id": "uuid",
  "suggested_labels": [
    {
      "label": "lead vocals",
      "confidence": 0.94,
      "frequency_range": [85, 255],
      "recommended": true
    },
    {
      "label": "kick drum",
      "confidence": 0.89,
      "frequency_range": [20, 100],
      "recommended": true
    },
    {
      "label": "snare drum",
      "confidence": 0.81,
      "frequency_range": [100, 5000],
      "recommended": false
    },
    {
      "label": "bass synth",
      "confidence": 0.76,
      "frequency_range": [30, 200],
      "recommended": true
    }
  ],
  "genre": "indie_rock",
  "tempo": 94,
  "user_history_suggestions": ["vocal harmonies", "isolated bass"]
}
```

**Behavior:**
- Load instrument classifier model
- Extract audio features (spectral, chromatic, tempogram)
- Classify instruments + confidence
- Extract frequency ranges for each detected instrument
- Look up user's previous extractions for suggestions
- Cache result for 24 hours

---

#### 5. **POST /extraction/extract**
Initiate extraction job with user-specified labels

**Request:**
```json
{
  "track_id": "uuid",
  "sources": [
    {
      "label": "lead vocals",
      "model": "demucs" | "spleeter",
      "timestamps": {
        "start_seconds": 0,
        "end_seconds": 180
      }
    },
    {
      "label": "drums",
      "model": "demucs"
    },
    {
      "label": "bass",
      "model": "demucs"
    }
  ],
  "iteration_id": "uuid" | null  // If refining previous extraction
}
```

**Response:**
```json
{
  "extraction_id": "uuid",
  "track_id": "uuid",
  "job_id": "gcp-job-id",
  "status": "queued",
  "sources_requested": 3,
  "models_used": ["demucs"],
  "estimated_time_seconds": 120,
  "cost_credits": 5,
  "queue_position": 7,
  "created_at": "2024-03-05T10:35:00Z"
}
```

**Behavior:**
- Validate labels (NLP ambiguity check → flag if score < threshold, costs extra credit)
- Map labels to extraction parameters via NLP rules
- Deduct credits from user account
- Create extraction record: `/users/{user_id}/tracks/{track_id}/extractions/{extraction_id}`
- Queue job to Cloud Tasks: `projects/PROJECT/locations/REGION/queues/extraction-queue`
- Return job ID + ETA
- Store extraction request metadata for training

---

#### 6. **GET /extraction/{extraction_id}**
Poll extraction job status

**Request:**
```
GET /extraction/{extraction_id}
```

**Response:**
```json
{
  "extraction_id": "uuid",
  "track_id": "uuid",
  "status": "queued|processing|completed|failed",
  "progress_percent": 45,
  "processing_started_at": "2024-03-05T10:35:30Z",
  "estimated_completion_at": "2024-03-05T10:37:30Z",
  "results": null,
  "error": null
}
```

**When status = "completed":**
```json
{
  "extraction_id": "uuid",
  "status": "completed",
  "completed_at": "2024-03-05T10:37:15Z",
  "results": {
    "sources": [
      {
        "label": "lead vocals",
        "model_used": "demucs",
        "duration_seconds": 180,
        "audio_url": "gs://bucket/extractions/{extraction_id}/lead_vocals.wav",
        "waveform_url": "gs://bucket/extractions/{extraction_id}/lead_vocals_waveform.json"
      },
      {
        "label": "drums",
        "model_used": "demucs",
        "audio_url": "gs://bucket/extractions/{extraction_id}/drums.wav",
        "waveform_url": "gs://bucket/extractions/{extraction_id}/drums_waveform.json"
      }
    ]
  }
}
```

---

#### 7. **POST /extraction/{extraction_id}/feedback**
Submit user feedback on extraction quality

**Request:**
```json
{
  "extraction_id": "uuid",
  "segment": {
    "start_seconds": 30,
    "end_seconds": 60,
    "label": "lead vocals"
  },
  "feedback_type": "too_much" | "too_little" | "artifacts" | "good",
  "feedback_detail": "vocals_bleeding_in" | "drums_in_vocals" | null,
  "refined_label": "lead vocals without reverb" | null,
  "optional_comment": "string" | null
}
```

**Response:**
```json
{
  "feedback_id": "uuid",
  "extraction_id": "uuid",
  "status": "recorded|queued_for_reextraction",
  "reextraction_queued": boolean,
  "new_extraction_id": "uuid" | null,
  "cost_credits": 5
}
```

**Behavior:**
- Store feedback: `/users/{user_id}/tracks/{track_id}/feedback/{feedback_id}`
- Tag for training data: {label, feedback, extraction_result, user_accepted}
- If refined_label provided → queue re-extraction automatically (costs credits)
- If feedback = "good" → mark segment as "accepted", don't re-extract
- Update extraction record with feedback count

---

#### 8. **GET /user/history**
Get extraction history for user

**Request:**
```
GET /user/history?limit=20&offset=0
```

**Response:**
```json
{
  "total_tracks": 47,
  "tracks": [
    {
      "track_id": "uuid",
      "filename": "song.mp3",
      "uploaded_at": "2024-03-05T10:30:00Z",
      "extractions_count": 3,
      "latest_extraction": {
        "extraction_id": "uuid",
        "status": "completed",
        "sources_extracted": ["lead vocals", "drums", "bass"],
        "completed_at": "2024-03-05T10:37:15Z"
      }
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

---

#### 9. **GET /user/credits**
Get current credit balance

**Request:**
```
GET /user/credits
```

**Response:**
```json
{
  "current_balance": 50,
  "monthly_allowance": 100,
  "subscription_tier": "free",
  "reset_date": "2024-04-05",
  "usage_this_month": {
    "extractions": 8,
    "credits_spent": 50,
    "ambiguous_labels_flagged": 2
  }
}
```

---

#### 10. **DELETE /track/{track_id}**
Delete track and all associated extractions (GDPR/privacy)

**Request:**
```
DELETE /track/{track_id}
```

**Response:**
```json
{
  "track_id": "uuid",
  "deleted_at": "2024-03-05T10:40:00Z",
  "files_deleted": 12,
  "feedback_anonymized": true
}
```

**Behavior:**
- Delete original audio from GCS
- Delete all extracted stems
- Delete track metadata
- Keep feedback data (anonymized) for training
- Cannot undo

---

## Database Schema (Firestore)

### Collection Structure

```
users/
  {user_id}/
    - profile
      - user_id (string)
      - device_id (string)
      - app_version (string)
      - subscription_tier (string: free|pro|studio)
      - credits_balance (number)
      - created_at (timestamp)
      - last_active_at (timestamp)
      - preference_genre (string | null)
      - models_preferred (array: [demucs, spleeter])
      - opt_in_training_data (boolean)
    
    tracks/
      {track_id}/
        - metadata
          - track_id (string)
          - filename (string)
          - duration_seconds (number)
          - sample_rate (number)
          - format (string)
          - file_size_mb (number)
          - gcs_path (string)
          - uploaded_at (timestamp)
          - genre_detected (string | null)
          - tempo_detected (number | null)
          - spectral_signature (blob | null)
        
        extractions/
          {extraction_id}/
            - metadata
              - extraction_id (string)
              - track_id (string)
              - user_id (string)
              - sources_requested (array)
                - label (string)
                - model (string)
                - nlp_params (map)
                - timestamps (map | null)
              - status (string: queued|processing|completed|failed)
              - job_id (string)
              - created_at (timestamp)
              - started_at (timestamp | null)
              - completed_at (timestamp | null)
              - processing_time_seconds (number | null)
              - credit_cost (number)
              - iteration_id (string | null)
              - is_accepted (boolean)
              - accepted_at (timestamp | null)
            
            - results (created when completed)
              - sources (array)
                - label (string)
                - model_used (string)
                - audio_url (string)
                - waveform_url (string)
                - size_mb (number)
            
            feedback/
              {feedback_id}/
                - feedback_id (string)
                - extraction_id (string)
                - segment_start_seconds (number)
                - segment_end_seconds (number)
                - segment_label (string)
                - feedback_type (string)
                - feedback_detail (string | null)
                - refined_label (string | null)
                - comment (string | null)
                - created_at (timestamp)
                - reextraction_id (string | null)

training_data/
  {feedback_id}/
    - original_label (string)
    - nlp_params (map)
    - extraction_result_waveform (blob | null)
    - feedback_type (string)
    - feedback_detail (string | null)
    - refined_label (string | null)
    - user_accepted (boolean)
    - genre (string)
    - instrument (string)
    - is_ambiguous (boolean)
    - timestamp (timestamp)
    - user_id_anon (string)  // Hash of user_id, not linkable
    - opt_in (boolean)
```

---

## NLP Parameter Mapping (Backend Responsibility)

The backend maps user labels → extraction parameters via **rule-based NLP**.

### Rule Engine

```python
LABEL_RULES = {
  "vocals": {
    "source": "vocal",
    "isolation_level": 0.7,
    "dryness": 0.5,
    "preserve_reverb": True
  },
  "lead vocals": {
    "source": "vocal",
    "vocal_type": "lead",
    "isolation_level": 0.85,
    "dryness": 0.5,
    "preserve_reverb": True
  },
  "lead vocals without reverb": {
    "source": "vocal",
    "vocal_type": "lead",
    "isolation_level": 0.9,
    "dryness": 0.95,  # High dryness
    "preserve_reverb": False
  },
  "isolated vocals": {
    "source": "vocal",
    "isolation_level": 0.95,
    "dryness": 0.8,
    "separation_aggression": 0.9
  },
  "tight kick drum": {
    "source": "drum",
    "drum_type": "kick",
    "isolation_level": 0.9,
    "attack_preservation": 1.0,
    "bleed_suppression": 0.95
  },
  "kick drum no bleed": {
    "source": "drum",
    "drum_type": "kick",
    "isolation_level": 0.95,
    "bleed_suppression": 1.0  # Max bleed suppression
  },
  "just the synth pad": {
    "source": "synth",
    "mask_everything_else": True,
    "isolation_level": 1.0
  }
}

# Descriptor modifiers
DESCRIPTORS = {
  "dry": { "dryness": +0.3 },
  "wet": { "dryness": -0.3 },
  "tight": { "isolation_level": +0.2, "attack_preservation": +0.2 },
  "loose": { "isolation_level": -0.2 },
  "isolated": { "isolation_level": +0.25 },
  "with": { "preserve_context": True },
  "without": { "suppress_context": True },
  "just": { "mask_everything_else": True },
  "only": { "mask_everything_else": True }
}

def parse_label(label_string: str) -> dict:
    params = {}
    
    # Check base label + descriptors
    label_lower = label_string.lower()
    
    # Find matching rule
    for rule_label, rule_params in LABEL_RULES.items():
        if rule_label in label_lower:
            params = rule_params.copy()
            
            # Apply descriptors
            for descriptor, modifier in DESCRIPTORS.items():
                if descriptor in label_lower:
                    params.update(modifier)
            
            return params
    
    # If no match, flag as ambiguous
    return {
        "ambiguous": True,
        "user_label": label_string,
        "confidence": 0.0,
        "requires_clarification": True
    }

def compute_ambiguity_score(label_string: str) -> float:
    """
    Return 0.0-1.0 where 1.0 = very ambiguous
    Triggers clarification prompts or costs extra credits
    """
    vague_words = ["thing", "stuff", "sound", "whatever"]
    specificity_score = 1.0
    
    if any(word in label_string.lower() for word in vague_words):
        return 0.9  # Very ambiguous
    
    if len(label_string) < 5:
        return 0.7  # Probably ambiguous
    
    # Has specific descriptors?
    if any(desc in label_string.lower() for desc in DESCRIPTORS.keys()):
        return 0.2  # Well-specified
    
    return 0.5  # Mildly ambiguous
```

---

## Job Queue & Worker Design

### Cloud Tasks (Extraction Queue)

**Queue Configuration:**
```yaml
location: us-central1
rateLimits:
  maxConcurrentDispatches: 4  # 4 extraction jobs in parallel
  maxDispatchesPerSecond: 1
retryConfig:
  maxAttempts: 3
  minBackoff: 60s
  maxBackoff: 600s
```

**Task Payload (sent to worker):**
```json
{
  "extraction_id": "uuid",
  "track_id": "uuid",
  "user_id": "uuid",
  "audio_path": "gs://bucket/tracks/{track_id}/original.wav",
  "sources": [
    {
      "label": "lead vocals",
      "model": "demucs",
      "nlp_params": {...}
    }
  ],
  "output_bucket": "gs://bucket/extractions/{extraction_id}",
  "callback_url": "https://api.example.com/webhooks/extraction-complete"
}
```

### Worker (Cloud Run, separate service)

**Responsibilities:**
1. Receive task from Cloud Tasks
2. Download audio from GCS
3. Load appropriate models (Demucs or Spleeter)
4. Run extraction with NLP parameters
5. Generate waveform JSONs (for UI visualization)
6. Upload stems to GCS
7. POST completion webhook to API
8. Handle errors + retry logic

**Container image structure:**
```
demucs-worker/
  ├── Dockerfile
  ├── requirements.txt (torch, torchaudio, fb-demucs)
  ├── main.py (receives Cloud Tasks job, handles extraction)
  ├── models/ (cached Demucs weights)
  └── utils/
      ├── audio_processing.py
      ├── waveform_generator.py
      └── gcs_handler.py

spleeter-worker/
  ├── Dockerfile
  ├── requirements.txt (spleeter, librosa)
  ├── main.py
  ├── models/ (cached Spleeter weights)
  └── utils/
      ├── audio_processing.py
      ├── waveform_generator.py
      └── gcs_handler.py
```

---

## Privacy & Training Data

### Anonymization Pipeline

```python
def anonymize_for_training(feedback_doc):
    """
    Before storing in training_data collection:
    1. Remove user_id → hash-based anon ID
    2. Remove track metadata except genre/tempo
    3. Keep label, feedback, extraction result (audio optional)
    """
    return {
        "user_id_anon": hash_sha256(user_id)[:8],  # 8-char hash, not reversible
        "original_label": feedback_doc["original_label"],
        "refined_label": feedback_doc["refined_label"],
        "feedback_type": feedback_doc["feedback_type"],
        "genre": feedback_doc["genre"],  # Generic, not identifying
        "tempo": feedback_doc["tempo"],  # Generic
        "is_ambiguous": compute_ambiguity_score(feedback_doc["original_label"]),
        "was_accepted": feedback_doc["user_accepted"],
        "timestamp": feedback_doc["timestamp"],
        "opt_in": feedback_doc["opt_in_training_data"]
    }
```

### Data Retention

| Data | Retention | Reason |
|------|-----------|--------|
| Original audio | Delete after 7 days | Privacy, cost |
| Extracted stems | Delete after 30 days | User won't need them indefinitely |
| Feedback (identifiable) | Keep 90 days, then anonymize | GDPR: users can see their feedback |
| Training data (anonymized) | Keep indefinitely | Used to improve models |
| Extraction metadata | Keep indefinitely | For analytics, not identifying |

---

## Credit System & Costs

```python
CREDIT_COSTS = {
  "basic_extraction": 5,            # Single source, single model
  "multi_source_extraction": 10,    # 2-3 sources
  "complex_extraction": 20,         # 4+ sources or re-extraction
  "ambiguous_label_clarification": 1,  # User has to refine
  "model_switch": 0                 # Free to switch mid-extraction
}

# Monthly allowances
SUBSCRIPTION_TIERS = {
  "free": {
    "monthly_credits": 100,
    "max_track_duration_minutes": 10,
    "max_concurrent_extractions": 1
  },
  "pro": {
    "monthly_credits": 500,
    "max_track_duration_minutes": 60,
    "max_concurrent_extractions": 3
  },
  "studio": {
    "monthly_credits": -1,  # Unlimited
    "max_track_duration_minutes": 120,
    "max_concurrent_extractions": 10
  }
}
```

---

## Security Considerations

### API Security
- Rate limiting: 100 req/min per user
- Input validation: audio format, duration, file size
- Output: Signed URLs (24-hour expiry) for audio downloads
- No sensitive data in logs

### Data Security
- GCS: encryption at rest + in transit
- Firestore: IAM-based access control
- Cloud Tasks: internal queue, not exposed
- API authentication: JWT tokens with refresh

### Privacy
- No user tracking outside of Firestore
- User deletion: cascade delete all data
- Anonymized training data: hash-based, not reversible
- Opt-in for model improvement (default: off)

---

## Monitoring & Observability

### Key Metrics

```
- Extraction queue depth (Cloud Tasks)
- Extraction completion time (p50, p95, p99)
- Model performance per genre/instrument
- User satisfaction (implicit: feedback types, re-extraction rate)
- Credits burned vs. allowance (predict churn)
- Training data quality (label ambiguity score)
```

### Alerting

```
- Queue > 100 jobs pending → scale workers
- Extraction failure rate > 5% → investigate
- Worker memory usage > 80% → restart
- API latency p99 > 2s → scale API
```

---

## Deployment

### Infrastructure as Code (Terraform)
```
terraform/
├── main.tf (GCP project, IAM, networking)
├── cloud_run_api.tf (API service)
├── cloud_run_workers.tf (Demucs + Spleeter workers)
├── cloud_tasks.tf (extraction queue)
├── firestore.tf (database + indexes)
├── gcs.tf (storage buckets)
└── monitoring.tf (Cloud Monitoring alerts)
```

### CI/CD
```
GitHub Actions:
  1. Test push to main → run unit tests
  2. Pass → build Docker images for API + workers
  3. Push to GCP Artifact Registry
  4. Deploy to staging environment
  5. Run integration tests
  6. Manual approval → deploy to production
```

---

## Testing Strategy

### Unit Tests
- NLP parameter mapping (does "lead vocals without reverb" → correct params?)
- Credit deduction logic
- Ambiguity scoring
- Privacy anonymization

### Integration Tests
- Full extraction flow: upload → suggest → extract → feedback → re-extract
- Multiple models: Demucs vs Spleeter on same track
- Job queue: task creation, worker pickup, completion callback
- Database transactions: no race conditions on credit deduction

### Load Tests
- 100 concurrent uploads
- 50 concurrent extractions
- Worker scaling under load

---

## Phase 1 Implementation Order

**Week 1-2: Foundation**
- GCP setup, Firestore schema
- Cloud Run API skeleton
- Authentication endpoints

**Week 3-4: Core Extraction**
- Audio upload + GCS integration
- Model wrapping (Demucs + Spleeter)
- Cloud Tasks integration

**Week 5-6: NLP + Suggestions**
- Instrument classifier
- Label suggestion endpoint
- Rule-based NLP mapper

**Week 7: Testing + Stability**
- Integration tests
- Error handling
- Deployment pipeline

