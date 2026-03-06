# Aurafractor — Deliverables Summary

Current development status across all project components.

---

## ✅ Backend (Complete)

Flask REST API running in Docker, fully tested.

| Item | Status |
|------|--------|
| PostgreSQL schema + connection pool | ✅ |
| Auth (device-ID register, JWT, refresh) | ✅ |
| Audio upload → GCS | ✅ |
| Spectral instrument classifier (librosa) | ✅ |
| NLP label engine (50+ rules, ambiguity scoring) | ✅ |
| Extraction orchestration → Cloud Tasks | ✅ |
| Demucs + Spleeter model wrappers | ✅ |
| Feedback loop + re-extraction | ✅ |
| Credit system (atomic deduction, tier enforcement) | ✅ |
| Privacy pipeline (opt-in, GDPR delete, anonymised training) | ✅ |
| Structured logging + `/metrics` endpoint | ✅ |
| Rate limiting | ✅ |
| 79 tests · 75%+ coverage · CI passing | ✅ |
| `DEV_DEVICE_IDS` env var → Studio tier for own devices | ✅ |

**Quick start:**
```bash
cd backend
docker-compose up        # postgres + api on :5001
curl http://localhost:5001/health
```

---

## ✅ UI (Complete — dev build pending)

Expo SDK 55 app running on iOS, Android, and web.

| Item | Status |
|------|--------|
| Anonymous device-ID auth | ✅ |
| Platform storage (SecureStore / localStorage) | ✅ |
| Audio file picker (native + web `<input>`) | ✅ |
| Upload → suggest labels → select → extract flow | ✅ |
| Extraction status polling (5 s) | ✅ |
| Stem audio playback + scrub bar | ✅ |
| Feedback form + re-extraction | ✅ |
| Track history (paginated, pull-to-refresh) | ✅ |
| Credit dashboard (balance, usage, transactions) | ✅ |
| Responsive web layout (max-width 600 px) | ✅ |
| 26 tests · CI passing | ✅ |

**Quick start:**
```bash
cd ui
npm install --legacy-peer-deps
npm run web     # http://localhost:8081
npm test
```

---

## ⏳ Remaining

| Item | Notes |
|------|-------|
| Terraform deployment | Cloud Run, GCS, Cloud Tasks configs exist in `terraform/` — not yet applied |
| Production `BASE_URL` in `ui/src/api/client.ts` | Replace `https://<your-cloud-run-host>` with real URL after deploy |
| Native device build | `expo prebuild` + `expo run:android` / `expo run:ios` |
| Load testing | Backend not yet stress-tested |

---

## File Reference

| Path | Description | Status |
|------|-------------|--------|
| `backend/` | Flask API, all services, workers, tests | ✅ |
| `backend/docker-compose.yml` | Local dev stack (Postgres + API) | ✅ |
| `backend/schema.sql` | PostgreSQL schema | ✅ |
| `ui/` | Expo React Native + web app | ✅ |
| `ui/app/` | Expo Router screens | ✅ |
| `ui/src/` | API client, components, hooks, storage | ✅ |
| `terraform/` | Cloud Run / GCS / Cloud Tasks IaC | ⏳ |
| `.github/workflows/ci.yml` | Backend + UI CI (lint, test, coverage) | ✅ |
| `docs/BACKEND_DESIGN.md` | System design, schema, NLP pipeline | ✅ |
| `docs/API_CONTRACT.md` | Endpoint reference | ✅ |
| `docs/QUICKSTART.md` | curl examples | ✅ |
