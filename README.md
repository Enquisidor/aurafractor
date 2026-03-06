# Aurafractor — AI Music Source Separation

An AI-powered music source separation tool. Users upload a track, describe what they want extracted in plain language ("lead vocals without reverb", "tight kick"), and the system isolates those sources using Demucs and Spleeter. A feedback loop lets users refine extractions, and all feedback feeds back into model training.

[![CI](https://github.com/Enquisidor/aurafractor/actions/workflows/ci.yml/badge.svg)](https://github.com/Enquisidor/aurafractor/actions/workflows/ci.yml)

---

## Components

| Component | Status | Description |
|-----------|--------|-------------|
| **Backend** | ✅ Complete | Flask API, PostgreSQL, GCS, Cloud Tasks |
| **Mobile App** | 🔨 In Progress | React Native iOS/Android |

---

## Architecture

```
React Native App
      │ HTTPS
      ▼
Flask API (Cloud Run)
      ├── PostgreSQL           — users, sessions, tracks, credits, feedback
      ├── Google Cloud Storage — original audio, extracted stems, waveforms
      ├── NLP rule engine      — label → extraction params, ambiguity scoring
      └── Cloud Tasks          — async extraction job queue
                │
          Worker endpoint
                ├── Demucs (htdemucs)
                └── Spleeter (2/4/5 stems)
```

---

## Backend

### Features

- **Audio upload** — MP3, WAV, FLAC, OGG up to 200 MB
- **Instrument separation** — Demucs and Spleeter, selectable per source
- **Spectral classifier** — librosa-based instrument suggestions with confidence scores
- **NLP label engine** — free-form labels ("lead vocals without reverb") → extraction parameters (50+ rules)
- **Ambiguity detection** — vague labels flagged, cost extra credits to proceed
- **Feedback → re-extraction loop** — users refine labels, re-extraction queued automatically
- **Credit system** — Free (100/mo), Pro (500/mo), Studio (unlimited)
- **Privacy-first** — opt-in training data, non-reversible user hashes, GDPR deletion endpoint
- **Cloud-native** — Cloud Run, Cloud Tasks, GCS, Cloud SQL, Terraform configs

### Project Structure

```
backend/
├── app.py                      # Application factory (registers blueprints)
├── schema.sql                  # PostgreSQL schema + views
├── requirements.txt
│
├── routes/                     # Flask blueprints (one file per concern)
│   ├── auth.py                 # POST /auth/register, /auth/refresh
│   ├── upload.py               # POST /upload
│   ├── extraction.py           # /extraction/* endpoints
│   ├── user.py                 # GET /user/*, DELETE /track/*
│   └── webhooks.py             # /webhooks/* and /worker/*
│
├── database/
│   ├── connection.py           # Connection pool, execute_query, db_transaction
│   ├── migrations.py           # Schema migration runner
│   └── models/                 # One file per table/concern
│       ├── users.py, sessions.py, tracks.py, extractions.py
│       ├── feedback.py, credits.py, suggestions.py, training.py
│
├── services/                   # Business logic
│   ├── auth.py                 # JWT generation, register/login
│   ├── extraction.py           # NLP → credits → DB → queue
│   ├── feedback.py             # Record feedback, trigger re-extraction
│   ├── credits.py              # Cost computation, deduction, refund
│   ├── nlp.py                  # Label → params, ambiguity scoring
│   ├── storage.py              # GCS upload/download/delete
│   └── tasks.py                # Cloud Tasks enqueueing
│
├── ml_models/
│   ├── classifier.py           # Spectral instrument classifier (librosa)
│   ├── demucs_wrapper.py       # Demucs separation
│   └── spleeter_wrapper.py     # Spleeter separation
│
├── workers/
│   └── extraction_worker.py    # Cloud Tasks worker: separate → upload → webhook
│
├── utils/
│   ├── decorators.py           # @require_auth, @worker_auth, @handle_errors
│   ├── validation.py           # Input validation (raises ValueError)
│   ├── rate_limiting.py        # Flask-Limiter setup
│   ├── logging.py              # Structured JSON logging (GCP-compatible)
│   └── monitoring.py           # In-process counters/gauges, /metrics endpoint
│
├── tests/
│   ├── conftest.py             # Shared fixtures (mock mode, test client)
│   ├── test_routes.py          # Integration tests for all API endpoints
│   ├── test_example.py         # Extended integration + NLP tests
│   ├── test_nlp.py             # Label parsing & ambiguity scoring
│   ├── test_credits.py         # Credit cost computation
│   ├── test_validation.py      # Input validation edge cases
│   ├── test_auth.py            # JWT generation & verification
│   └── test_classifier.py      # Instrument classifier
│
└── .coveragerc                 # Coverage config (excludes real-infra paths)

terraform/
├── main.tf, variables.tf       # Provider + shared locals
├── cloud_run.tf                # Cloud Run service + service account + IAM
├── gcs.tf                      # Audio bucket + lifecycle rules
└── cloud_tasks.tf              # Extraction queue

docs/
├── BACKEND_DESIGN.md           # System design, schema decisions, NLP pipeline
├── API_CONTRACT.md             # Machine-readable endpoint reference
├── QUICKSTART.md               # curl examples for every endpoint
└── DELIVERABLES_SUMMARY.md     # Project overview and roadmap

.github/workflows/ci.yml        # GitHub Actions: lint + test on push/PR
```

### Quick Start

**Prerequisites:** Docker & Docker Compose, Python 3.10+

```bash
cd backend
cp .env.example .env          # uses mock mode by default
docker-compose up -d          # starts postgres + api
curl http://localhost:5000/health
# {"status":"ok","mock_mode":true,...}
```

**Run tests:**
```bash
cd backend
pip install -r requirements.txt pytest pytest-cov
pytest tests/ -v --cov=.
```

### API Reference

See [docs/API_CONTRACT.md](docs/API_CONTRACT.md) for the full endpoint contract.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/register` | Register/login by device_id |
| `POST` | `/auth/refresh` | Refresh session token |
| `POST` | `/upload` | Upload audio file |
| `POST` | `/extraction/suggest-labels` | Get AI-suggested instrument labels |
| `POST` | `/extraction/extract` | Queue extraction job |
| `GET`  | `/extraction/{id}` | Poll job status & results |
| `POST` | `/extraction/{id}/feedback` | Submit feedback / trigger re-extraction |
| `GET`  | `/user/history` | Paginated track history |
| `GET`  | `/user/credits` | Credit balance & usage |
| `DELETE` | `/track/{id}` | Delete track (GDPR) |
| `GET`  | `/health` | Health check |
| `GET`  | `/metrics` | Internal counters/gauges |

### Credit Costs

| Action | Credits |
|--------|---------|
| Single-source extraction | 5 |
| Multi-source extraction | 10 |
| Re-extraction | 20 |
| Ambiguous label surcharge | +1 per label |

Tiers: **Free** 100/mo · **Pro** 500/mo · **Studio** unlimited

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | Postgres connection string |
| `JWT_SECRET` | `dev-secret` | JWT signing key |
| `GCS_BUCKET` | — | GCS bucket name |
| `WORKER_SECRET` | `worker-secret` | Shared secret for worker → API auth |
| `ENABLE_MOCK_RESPONSES` | `false` | Skip real GCS/Cloud Tasks (local dev) |
| `GCP_PROJECT_ID` | — | GCP project ID |
| `GCP_REGION` | — | GCP region |
| `CLOUD_TASKS_QUEUE` | — | Cloud Tasks queue name |
| `DEV_DEVICE_IDS` | — | Comma-separated device IDs that register as Studio tier (unlimited credits) |

See [backend/.env](backend/.env) for the full list.

---

## Mobile App

> **Status: 🔨 In Progress**

React Native (Expo) for iOS and Android, consuming the Backend API.

```
mobile/
├── app/                    # Expo Router screens
│   ├── (tabs)/             # Tab navigation
│   │   ├── index.tsx       # Home / upload
│   │   ├── history.tsx     # Track history
│   │   └── credits.tsx     # Credit balance
│   └── extraction/         # Extraction flow
│       ├── [id].tsx        # Poll status + results
│       └── feedback.tsx    # Feedback form
├── src/
│   ├── api/                # Typed API client
│   ├── components/         # Shared UI components
│   ├── hooks/              # Custom React hooks
│   └── store/              # Auth + session state
└── app.json
```

---

## Further Reading

- [docs/BACKEND_DESIGN.md](docs/BACKEND_DESIGN.md) — full system design, credit model, privacy approach
- [docs/QUICKSTART.md](docs/QUICKSTART.md) — curl examples for every endpoint
- [docs/API_CONTRACT.md](docs/API_CONTRACT.md) — machine-readable endpoint contract
