# Aurafractor

## Project Overview

Aurafractor is an AI-powered music source separation tool. Users upload an audio track, describe what they want extracted in plain language ("lead vocals without reverb", "tight kick"), and the system isolates those sources using Demucs and Spleeter. A feedback loop lets users refine extractions, and all feedback flows back into model training.

## Tech Stack

### Backend (`backend/`)
- Runtime: Python 3.10+
- Framework: Flask 2.3 (blueprints per concern in `routes/`)
- Database: PostgreSQL (Cloud SQL) via psycopg2, connection pool in `database/connection.py`
- Auth: JWT (PyJWT), anonymous device-ID registration — no email/password
- Storage: Google Cloud Storage (GCS) for audio, stems, and waveforms
- Async jobs: Google Cloud Tasks (extraction job queue)
- ML: Demucs (`htdemucs`) + Spleeter (2/4/5 stems) via `ml_models/`
- NLP: Rule-based label → extraction params engine (`services/nlp.py`, 50+ rules)
- Rate limiting: Flask-Limiter
- Logging: Structured JSON (GCP-compatible) via `utils/logging.py`
- Monitoring: In-process counters/gauges, `/metrics` endpoint

### Frontend (`ui/`)
- Runtime: Expo SDK 55, React Native 0.83.2, React 19
- Language: TypeScript
- Routing: Expo Router (file-based, `app/` directory)
- State: Redux Toolkit (`src/store/`)
- Audio: expo-av (playback with scrub bar)
- File picking: expo-document-picker
- Auth storage: expo-secure-store (native) / localStorage (web) via `src/storage/platform.ts`
- API client: typed fetch client at `src/api/client.ts`
- Web: metro bundler, responsive layout capped at 600 px max-width
- Testing: jest-expo + @testing-library/react-native

### Infrastructure
- Cloud: Google Cloud Platform (Cloud Run, Cloud SQL, Cloud Tasks, GCS, Artifact Registry)
- IaC: Terraform (`terraform/`)
- CI/CD: GitHub Actions (backend build/deploy, web build/deploy, Android build, Firebase hosting)
- Containerisation: Docker (backend `Dockerfile` + `Dockerfile.dev`, `docker-compose.yml`)

## Commands

```bash
# Backend
cd backend
cp .env.example .env
docker-compose up -d          # starts postgres + api at localhost:5000
pytest tests/ -v --cov=.      # 79 tests

# Frontend
cd ui
npm install --legacy-peer-deps
npm run web                   # browser at localhost:8081
npm run android               # requires expo prebuild first
npm run ios                   # requires expo prebuild first
npm test                      # 26 tests
npm run test:coverage
```

## Ports

| Service | Port |
|---------|------|
| Flask API (local Docker) | 5000 |
| Expo web dev server | 8081 |

## Domain Model

Specs live at `.spec/` (relative to this file). Aggregates, bounded contexts, and ubiquitous language are defined there — agents must read the glossary before writing any domain code.

| Artifact | Path |
|----------|------|
| Glossary | `.spec/glossary.md` |
| Bounded contexts | `.spec/bounded-contexts/` |
| Aggregates | `.spec/aggregates/` |

## Architecture Conventions
<!-- To be completed by the Architect agent after spec phase -->

## Directory Structure
<!-- To be completed by the Architect agent after spec phase -->
