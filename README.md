# Music Source Separation Backend

A production-ready Python/Flask backend for AI-powered music source separation with user feedback loops, credit-based usage, and privacy-preserving training data.

## Features

✨ **Audio Processing**
- Upload & process music tracks (MP3, WAV, FLAC)
- Demucs & Spleeter integration for instrument separation
- Real-time job queue with Cloud Tasks

🎯 **Smart Labels**
- AI-generated instrument suggestions
- User-friendly label input (1-word to multi-word)
- NLP-based parameter interpretation
- Ambiguity detection & clarification

🔄 **User Feedback Loop**
- Mark extraction regions as "good" or flag for improvement
- Refine labels → automatic re-extraction
- Implicit success signals (1-day acceptance threshold)
- Training data collection (opt-in, anonymized)

💳 **Credits & Subscriptions**
- Free: 100 credits/month, 10-min tracks
- Pro: 500 credits/month, 60-min tracks
- Studio: unlimited credits & durations
- Cost-based ambiguity (vague labels cost extra)

🔐 **Privacy-First**
- Automatic data deletion (7-day retention)
- Anonymized training data (non-reversible hashes)
- User opt-in for model improvement
- GDPR-compliant deletion

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 React Native Mobile App              │
└────────────────┬────────────────────────────────────┘
                 │ HTTPS API
┌────────────────▼────────────────────────────────────┐
│          Flask API (Cloud Run)                       │
│  - Upload & Auth                                     │
│  - Label Suggestions                                 │
│  - Extraction Queueing                               │
│  - Feedback & Re-extraction                          │
│  - Credit Management                                 │
└────────────────┬────────────────────────────────────┘
         ┌───────┴───────┐
         │               │
    ┌────▼──────┐    ┌───▼───────┐
    │  Postgres  │    │Cloud Tasks │
    │(metadata)  │    │(job queue) │
    └────────────┘    └───┬───────┘
                          │
                    ┌─────┴──────┐
                    │            │
              ┌─────▼───┐  ┌─────▼──┐
              │  Demucs  │  │Spleeter│
              │ (workers)│  │(workers)│
              └──────────┘  └────────┘
```

---

## Tech Stack

- **Runtime**: Python 3.10+
- **Web Framework**: Flask
- **Database**: PostgreSQL
- **Job Queue**: Google Cloud Tasks
- **Storage**: Google Cloud Storage
- **ML Models**: Demucs, Spleeter
- **Classifier**: librosa + custom models
- **Deployment**: Docker + Cloud Run + Terraform

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- PostgreSQL (provided via Docker)

### 1. Setup (2 min)
```bash
git clone <repo>
cd music-separation-backend
cp .env.example .env
docker-compose up -d
```

### 2. Verify
```bash
curl http://localhost:5000/health
# {"status": "ok", ...}
```

### 3. Test API
See [QUICKSTART.md](./QUICKSTART.md) for detailed examples.

---

## Project Structure

```
.
├── app.py                      # Main Flask application
├── schema.sql                  # PostgreSQL database schema
├── requirements.txt            # Python dependencies
│
├── database/                   # (To be implemented)
│   ├── __init__.py
│   └── connection.py          # Connection pooling
│
├── services/                   # (To be implemented)
│   ├── auth.py                # User registration & tokens
│   ├── extraction.py          # Extraction pipeline
│   ├── feedback.py            # Feedback recording
│   ├── credits.py             # Credit system
│   ├── nlp.py                 # Label interpretation
│   └── storage.py             # GCS integration
│
├── models/                     # (To be implemented)
│   ├── demucs_wrapper.py      # Demucs inference
│   ├── spleeter_wrapper.py    # Spleeter inference
│   └── classifier.py          # Instrument classifier
│
├── tests/
│   └── test_example.py        # Test examples & patterns
│
├── docker-compose.yml         # Local dev environment
├── Dockerfile.dev             # Development container
│
├── terraform/                 # (To be implemented)
│   ├── main.tf
│   ├── cloud_run.tf
│   ├── cloud_tasks.tf
│   └── gcs.tf
│
├── BACKEND_DESIGN.md          # Complete system design
├── BACKEND_INITIAL_PROMPT.md  # Detailed implementation guide
├── QUICKSTART.md              # Testing & development guide
└── README.md                  # This file
```

---

## API Overview

### Authentication
- `POST /auth/register` - Create user account
- `POST /auth/refresh` - Refresh session token

### Audio Processing
- `POST /upload` - Upload audio file
- `POST /extraction/suggest-labels` - Get AI suggestions
- `POST /extraction/extract` - Queue extraction job
- `GET /extraction/{id}` - Check job status

### Feedback & Refinement
- `POST /extraction/{id}/feedback` - Submit feedback
- (Feedback can trigger re-extraction)

### User Management
- `GET /user/credits` - Check credit balance
- `GET /user/history` - Extraction history
- `DELETE /track/{id}` - Delete track (GDPR)

---

## Key Design Decisions

### 1. **Labels as Flexible, Free-Form Input**
- Users type any label: "vocals", "lead vocals", "lead vocals without reverb"
- 1-word labels are perfectly valid ("drums", "synth")
- NLP interprets labels to extraction parameters
- Ambiguous labels are flagged and cost extra credits

### 2. **Ambiguity Scoring**
- Clear (0.0-0.3): "vocals", "lead vocals", "kick drum"
- Moderate (0.3-0.6): Unknown single words
- Ambiguous (0.6-1.0): "thing", "stuff", very generic
- Cost penalty: >0.6 ambiguity = extra 1 credit to clarify

### 3. **User Feedback as Training Signal**
- Explicit: "good" (mark section accepted), "too_much", "too_little", "artifacts"
- Implicit: 1-day no-follow-up = "good enough"
- Refined labels teach NLP what users meant
- Aggregated patterns improve global model

### 4. **Privacy-First Approach**
- Original audio: delete after 7 days
- Training data: anonymized with non-reversible hashes
- User opt-in: off by default, users can enable in settings
- GDPR: users can delete all their data anytime

### 5. **Cost Structure**
- Base extraction: 5 credits
- Re-extraction: 20 credits (expensive to discourage over-iteration)
- Ambiguous label: +1 credit penalty
- Free tier: 100 credits/month (20 extractions)
- Pro tier: 500 credits/month (100 extractions)

---

## Development Workflow

### Add a Feature
1. Update schema if needed (`schema.sql`)
2. Implement service layer (`services/`)
3. Add endpoint to Flask app (`app.py`)
4. Write tests (`tests/`)
5. Test locally with mock responses
6. Test with real GCS/Postgres when ready

### Run Tests
```bash
pytest tests/ -v
```

### Check Code Quality
```bash
black . --check
flake8 app.py services/ models/
```

### View Database
```bash
docker exec music-separation-db psql -U postgres -d music_separation
```

---

## Deployment

### Local Development
```bash
docker-compose up -d
# API runs on localhost:5000
# Postgres on localhost:5432
```

### Cloud Deployment (Production)
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

This deploys:
- Flask API to Cloud Run
- PostgreSQL to Cloud SQL
- Cloud Tasks queue for extraction jobs
- GCS buckets for audio storage
- Demucs & Spleeter workers to Cloud Run

---

## Implementation Status

### ✅ Completed
- PostgreSQL schema design
- Flask app skeleton with all endpoints
- NLP rule engine + ambiguity scoring
- Mock response system for testing
- Docker Compose local dev setup
- API documentation
- Test patterns & examples

### 🔄 In Progress (Week 1-7)
- Real database integration
- Cloud Tasks job queue
- Model wrappers (Demucs + Spleeter)
- Instrument classifier
- GCS integration
- Comprehensive error handling
- Terraform deployment configs

### ⏳ Future (Phase 2 - NLP Instance)
- Enhanced NLP with learned weights
- Transformer fine-tuning (if needed)
- Label → parameter mapping improvements
- Training data aggregation & insights

---

## Monitoring & Observability

### Key Metrics
- Extraction success rate
- Average processing time
- Queue depth (backpressure indicator)
- Credit usage patterns
- Model accuracy (implicit: re-extraction rate)

### Alerting
- Queue > 100 jobs → scale workers
- Extraction failure > 5% → investigate
- API latency p99 > 2s → scale API

---

## Privacy & Security

### Data Handling
- **Original audio**: Deleted after 7 days
- **Extracted stems**: Deleted after 30 days
- **User metadata**: Kept indefinitely (anonymized if for training)
- **Feedback data**: Kept 90 days, then anonymized

### Security Features
- JWT token authentication
- Rate limiting (100 req/min per user)
- Input validation on all endpoints
- SQL injection prevention (prepared statements)
- HTTPS enforcement (in production)
- CORS headers for mobile app

---

## Troubleshooting

### API won't start
```bash
docker-compose logs api
docker-compose restart api
```

### Database errors
```bash
docker-compose logs postgres
docker exec music-separation-db psql -U postgres -d music_separation
```

### Can't connect to API
```bash
# Check if running
docker-compose ps
# Check port
lsof -i :5000
```

---

## Contributing

1. Create feature branch: `git checkout -b feature/my-feature`
2. Write tests for any new functionality
3. Ensure tests pass: `pytest`
4. Commit: `git commit -m "Add feature"`
5. Push: `git push origin feature/my-feature`
6. Create PR with detailed description

---

## License

MIT

---

## Support

For questions or issues:
1. Check [BACKEND_INITIAL_PROMPT.md](./BACKEND_INITIAL_PROMPT.md) for detailed implementation guide
2. Check [QUICKSTART.md](./QUICKSTART.md) for testing examples
3. Review [BACKEND_DESIGN.md](./BACKEND_DESIGN.md) for architecture details

---

**Next Steps**: Read [BACKEND_INITIAL_PROMPT.md](./BACKEND_INITIAL_PROMPT.md) to start implementing the backend with real database integration, Cloud Tasks, and model wrappers.
