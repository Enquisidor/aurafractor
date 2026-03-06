# Aurafractor — Music Source Separation Backend

A production-ready Python/Flask backend for AI-powered music source separation with user feedback loops, credit-based usage, and privacy-preserving training data.

[![CI](https://github.com/Enquisidor/aurafractor/actions/workflows/ci.yml/badge.svg)](https://github.com/Enquisidor/aurafractor/actions/workflows/ci.yml)

---

## Features

- **Audio upload & processing** — MP3, WAV, FLAC, OGG (up to 200 MB)
- **Instrument separation** — Demucs (htdemucs) and Spleeter, selectable per source
- **Spectral instrument classifier** — librosa-based suggestions with confidence scores
- **NLP label interpretation** — free-form labels ("lead vocals without reverb") → extraction parameters
- **Ambiguity detection** — vague labels are flagged, cost extra credits to proceed
- **Feedback → re-extraction loop** — users refine labels, re-extraction queued automatically
- **Credit system** — Free (100/mo), Pro (500/mo), Studio (unlimited)
- **Privacy-first** — opt-in training data, non-reversible user hashes, GDPR deletion
- **Cloud-native** — Cloud Run, Cloud Tasks, GCS, Cloud SQL

---

## Architecture

```
Mobile App
    │ HTTPS
Flask API (Cloud Run)
    ├── PostgreSQL (metadata, credits, sessions)
    ├── Google Cloud Storage (audio, stems, waveforms)
    └── Cloud Tasks (job queue)
             │
        Worker endpoint
             ├── Demucs (htdemucs)
             └── Spleeter (2/4/5 stems)
```

---

## Project Structure

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
│       ├── users.py
│       ├── sessions.py
│       ├── tracks.py
│       ├── extractions.py
│       ├── feedback.py
│       ├── credits.py
│       ├── suggestions.py
│       └── training.py
│
├── services/                   # Business logic
│   ├── auth.py                 # JWT generation, register/login
│   ├── extraction.py           # Orchestration: NLP → credits → DB → queue
│   ├── feedback.py             # Record feedback, trigger re-extraction
│   ├── credits.py              # Cost computation, deduction, refund
│   ├── nlp.py                  # Label → params, ambiguity scoring
│   ├── storage.py              # GCS upload/download/delete
│   └── tasks.py                # Cloud Tasks enqueueing
│
├── ml_models/                  # ML model wrappers
│   ├── demucs_wrapper.py       # Demucs separation
│   ├── spleeter_wrapper.py     # Spleeter separation
│   └── classifier.py           # Spectral instrument classifier
│
├── workers/
│   └── extraction_worker.py    # Cloud Tasks worker: separate → upload → webhook
│
├── utils/
│   ├── decorators.py           # @require_auth, @worker_auth, @handle_errors
│   ├── validation.py           # Input validation (raises ValueError)
│   ├── logging.py              # Structured JSON logging (GCP-compatible)
│   └── monitoring.py           # In-process counters/gauges, /metrics endpoint
│
└── tests/
    ├── conftest.py             # Shared fixtures (mock mode, test client)
    ├── test_routes.py          # Integration tests for all API endpoints
    ├── test_nlp.py             # NLP label parsing & ambiguity scoring
    ├── test_credits.py         # Credit cost computation
    ├── test_validation.py      # Input validation edge cases
    ├── test_auth.py            # JWT generation & verification
    └── test_classifier.py      # Instrument classifier (mock mode)

.github/
└── workflows/
    └── ci.yml                  # GitHub Actions: lint + test on push/PR
```

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.10+

### Run locally (mock mode — no GCS or real DB required)

```bash
cd backend
cp .env.example .env          # uses mock mode by default
docker-compose up -d          # starts postgres + api
curl http://localhost:5000/health
# {"status":"ok","mock_mode":true,...}
```

### Run tests

```bash
cd backend
pip install -r requirements.txt pytest pytest-cov
pytest tests/ -v --cov=.
```

---

## API Reference

See [docs/API_CONTRACT.md](docs/API_CONTRACT.md) for the full endpoint contract (generated from [docs/BACKEND_DESIGN.md](docs/BACKEND_DESIGN.md)).

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/register` | Register/login by device_id |
| `POST` | `/auth/refresh` | Refresh session token |
| `POST` | `/upload` | Upload audio file |
| `POST` | `/extraction/suggest-labels` | Get AI-suggested labels |
| `POST` | `/extraction/extract` | Queue extraction job |
| `GET`  | `/extraction/{id}` | Poll job status |
| `POST` | `/extraction/{id}/feedback` | Submit feedback / trigger re-extraction |
| `GET`  | `/user/history` | Paginated track history |
| `GET`  | `/user/credits` | Credit balance & usage |
| `DELETE` | `/track/{id}` | Delete track (GDPR) |
| `GET`  | `/health` | Health check |
| `GET`  | `/metrics` | Internal counters/gauges |

---

## Credit Costs

| Action | Credits |
|--------|---------|
| Single-source extraction | 5 |
| Multi-source extraction | 10 |
| Re-extraction | 20 |
| Ambiguous label surcharge | +1 per label |

Tiers: **Free** 100/mo · **Pro** 500/mo · **Studio** unlimited

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://localhost/music_separation` | Postgres connection string |
| `JWT_SECRET` | `dev-secret` | JWT signing key |
| `GCS_BUCKET` | `music-separation-dev` | GCS bucket name |
| `ENABLE_MOCK_RESPONSES` | `false` | Skip real GCS/Cloud Tasks calls |
| `WORKER_SECRET` | `worker-secret` | Shared secret for worker → API calls |
| `GCP_PROJECT` | `music-separation-dev` | GCP project ID |
| `MAX_CONCURRENT_EXTRACTIONS` | `4` | Concurrency cap |

See [backend/.env.example](backend/.env.example) for the full list.

---

## Implementation Status

### ✅ Complete
- PostgreSQL schema + views
- Connection pooling + parameterized query helpers
- Database model layer (per-table files)
- Auth service (JWT, register/login, refresh)
- Extraction orchestration (NLP → credits → DB → Cloud Tasks)
- Feedback + re-extraction pipeline
- Credit system (deduction, refund, studio bypass)
- NLP rule engine + ambiguity scoring (50+ instrument labels)
- Spectral instrument classifier (librosa)
- Demucs & Spleeter wrappers
- GCS upload/download/signed URLs
- Cloud Tasks enqueueing
- Extraction worker (separate → upload stems → webhook)
- Structured logging (JSON for GCP, human-readable in dev)
- Input validation + decorators
- In-process metrics (`/metrics`)
- Flask blueprint routing (one file per concern)
- Comprehensive tests (unit + integration, mock mode)
- GitHub Actions CI pipeline

---

## Further Reading

- [docs/BACKEND_DESIGN.md](docs/BACKEND_DESIGN.md) — full system design, schema decisions, NLP pipeline, credit model
- [docs/QUICKSTART.md](docs/QUICKSTART.md) — curl examples for every endpoint
- [docs/API_CONTRACT.md](docs/API_CONTRACT.md) — machine-readable endpoint contract for the NLP instance

---

### ⏳ Next (Phase 2 — NLP Instance)
- Enhanced NLP with learned weights
- Training data aggregation pipeline
- Transformer fine-tuning (optional)
- Terraform deployment configs
- Load testing
