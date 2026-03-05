# BACKEND INSTANCE - System Prompt

## Mission
Build a production-ready backend for a music source separation tool with the following core features:
- Audio upload & processing
- Instrument extraction using Demucs and Spleeter
- AI-powered label suggestions
- User feedback → re-extraction pipeline
- NLP-based label interpretation
- Credit/subscription system
- Privacy-preserving training data collection

## Architecture Overview

```
PostgreSQL ← Flask API ↔ GCS (audio storage)
                  ↓
            Cloud Tasks (job queue)
                  ↓
        Demucs & Spleeter Workers
```

## Stack
- **Language**: Python 3.10+
- **Framework**: Flask
- **Database**: PostgreSQL
- **Job Queue**: Google Cloud Tasks
- **Storage**: Google Cloud Storage
- **Models**: Demucs + Spleeter

## Key Constraints
1. **All 1-word labels are valid** (e.g., "vocals", "drums", "synth")
2. **Labels are for re-labeling only** - not commentary
3. **Max 4 concurrent extractions** at any time
4. **Mock responses for local development** - no real GCS calls needed initially
5. **Privacy-first**: training data is anonymized, opt-in for model improvement
6. **Credit-based usage**: ambiguous labels cost extra credits

## Current State
You have:
- ✅ PostgreSQL schema (schema.sql)
- ✅ Flask starter app with endpoints (app.py)
- ✅ NLP rule engine + ambiguity scoring
- ✅ Mock response system
- ✅ All 10 core endpoints stubbed

## What You're Building (This Instance)
1. **Real database integration** - replace mock responses with actual PostgreSQL queries
2. **Cloud Tasks integration** - queue extraction jobs properly
3. **Model wrapper layer** - abstract Demucs/Spleeter interfaces
4. **GCS integration** - upload/download audio, handle signed URLs
5. **Credit system logic** - deduct credits, enforce limits
6. **Instrument classifier** - detect instruments from audio
7. **Full error handling** - validation, retry logic, graceful failures
8. **Comprehensive testing** - unit tests + integration tests

## Phase 1 Implementation Order (Weeks 1-7)

### Week 1-2: Foundation
- Set up PostgreSQL (local + cloud)
- Implement database connection pooling
- Create database helpers (query builders, transaction management)
- Implement user lifecycle (register, auth, credits)
- Test: auth flow end-to-end

### Week 3-4: Core Extraction
- Implement audio upload → GCS storage
- Wrap Demucs model (load, inference, parameter mapping)
- Wrap Spleeter model (same)
- Cloud Tasks integration (queue jobs, worker endpoint)
- Implement webhook handler (worker → API callback)
- Test: upload, suggest labels, queue extraction

### Week 5-6: NLP + Feedback
- Enhance instrument classifier (spectrum analysis)
- Label suggestion endpoint (real classifier output)
- Feedback recording + re-extraction queueing
- Credit deduction + enforcement
- Training data pipeline (anonymization, storage)
- Test: full feedback loop, label refinement

### Week 7: Polish + Observability
- Error handling (validation, retries, timeouts)
- Logging (structured, GCP Cloud Logging compatible)
- Monitoring (extraction success rate, queue depth, latency)
- Rate limiting + abuse prevention
- Deployment setup (Terraform, CI/CD)
- Test: load testing, edge cases

## Important Details

### NLP Ambiguity Scoring
```
Scores 0.0 (clear) to 1.0 (very ambiguous)
- Single word like "vocals", "drums" → 0.1 (clear)
- Multi-word like "lead vocals" → 0.2 (clear)
- Vague like "thing" → 0.95 (very ambiguous)
- Unknown single word → 0.4 (moderate)

If score > 0.6 → flag to user, costs extra credit to proceed
```

### Credit Costs
```
Basic extraction: 5 credits
Multi-source: 10 credits
Complex/re-extraction: 20 credits
Ambiguous label clarification: 1 credit (to refine label)
Model switch: 0 credits (free)

Free tier: 100 credits/month
Pro tier: 500 credits/month
Studio tier: unlimited
```

### Label → Parameters Pipeline
```
User inputs: "lead vocals without reverb"
  ↓
parse_label_to_params() 
  ↓
{
  source: "vocal",
  vocal_type: "lead",
  isolation_level: 0.9,
  dryness: 0.95,
  preserve_reverb: False
}
  ↓
Send to Demucs/Spleeter with these parameters
  ↓
Extract & store results
```

### Cloud Tasks Workflow
```
1. API receives extraction request
2. Validates user has credits
3. Deducts credits
4. Creates task payload
5. Queues to Cloud Tasks
6. Worker polls for tasks
7. Worker runs extraction (Demucs or Spleeter)
8. Worker uploads stems to GCS
9. Worker POSTs webhook: /webhooks/extraction-complete
10. API updates database, marks extraction as done
11. User polls /extraction/{id} → sees results
```

### Database Patterns to Use
- Connection pooling (already stubbed)
- Prepared statements (prevent SQL injection)
- Transactions (for credit deduction)
- Indexes on common queries (user_id, created_at, status)
- Views for complex queries (credit summary, track history)

## Testing Strategy

### Unit Tests
- NLP parameter mapping (labels → params)
- Ambiguity scoring
- Credit logic (deduction, enforcement)
- Privacy anonymization

### Integration Tests
- Auth flow (register → tokens → refresh)
- Full extraction: upload → suggest → extract → feedback → re-extract
- Multi-model: Demucs vs Spleeter on same track
- Job queue: task creation, worker pickup, webhook callback
- Credit transactions (deduct, refund on failure)

### Load Tests
- 100 concurrent uploads
- 50 concurrent extractions in queue
- Worker scaling under load

## Key Files to Create/Modify

```
backend/
├── app.py                    # Main Flask app (keep existing, enhance)
├── requirements.txt          # Dependencies
├── .env.example             # Environment template
│
├── database/
│   ├── __init__.py
│   ├── connection.py        # Connection pooling + helpers
│   ├── models.py            # SQLAlchemy-style models or raw queries
│   └── migrations.py        # Schema management
│
├── services/
│   ├── __init__.py
│   ├── auth.py              # User registration, tokens
│   ├── extraction.py        # Extraction logic
│   ├── feedback.py          # Feedback recording
│   ├── credits.py           # Credit deduction, enforcement
│   ├── nlp.py               # Label interpretation, classification
│   └── storage.py           # GCS upload/download
│
├── models/
│   ├── demucs_wrapper.py    # Demucs inference
│   ├── spleeter_wrapper.py  # Spleeter inference
│   └── classifier.py        # Instrument classifier
│
├── workers/
│   ├── extraction_worker.py # Cloud Tasks worker code
│   └── callbacks.py         # Webhook handlers
│
├── utils/
│   ├── logging.py           # Structured logging
│   ├── monitoring.py        # Metrics/observability
│   ├── validation.py        # Input validation
│   └── decorators.py        # Reusable decorators (@require_auth, etc)
│
├── tests/
│   ├── test_auth.py
│   ├── test_extraction.py
│   ├── test_nlp.py
│   ├── test_credits.py
│   └── test_integration.py
│
├── schema.sql               # Database schema
├── Dockerfile               # Container image
├── docker-compose.yml       # Local dev (postgres, redis, etc)
└── terraform/
    ├── main.tf
    ├── cloud_run.tf
    ├── cloud_tasks.tf
    └── gcs.tf
```

## Success Criteria for This Instance

By the end, you should have:
✅ Full API implementation (not mocks)
✅ Database queries working
✅ Audio upload/storage working
✅ Cloud Tasks integration working
✅ Instrument classifier functional
✅ NLP label interpretation working
✅ Credit system enforced
✅ Comprehensive error handling
✅ Privacy data anonymization pipeline
✅ 80%+ code coverage in tests
✅ Deployable to Cloud Run
✅ Documented API (OpenAPI/Swagger optional but nice)

## Important Notes for Claude Code

1. **Use prepared statements** - prevent SQL injection
2. **Transaction management** - credit deduction must be atomic
3. **Proper error handling** - user-facing errors vs internal errors
4. **Logging** - every important operation should log (debug, info, error)
5. **Type hints** - use Python typing for clarity
6. **Docstrings** - every function needs clear docs
7. **Async where appropriate** - Cloud Tasks calls should be async
8. **Graceful degradation** - if GCS fails, queue for retry, don't lose data
9. **Security** - validate all inputs, use parameterized queries, CORS headers
10. **Testing** - write tests as you go, don't leave for the end

## Privacy Implementation Checklist

- [ ] Anonymization: hash user_id for training data
- [ ] Retention: delete original audio after 7 days
- [ ] Opt-in: training data collection is opt-in by default
- [ ] GDPR: user can delete all their data with DELETE /track/{id}
- [ ] Audit: log all data accesses
- [ ] Encryption: GCS encryption at rest + HTTPS in transit

## Next Phase (NLP Instance)

After this backend instance is done and documented, the NLP Instance will:
- Build on top of this API
- Implement rule-based NLP with learned weights
- Create training data pipeline
- Implement ambiguity detection
- Optional: fine-tune transformer if time allows

For handoff: write API_CONTRACT.md documenting all endpoints for NLP instance to consume.

## Start Here

1. Read schema.sql - understand the data model
2. Read app.py - understand the endpoint structure
3. Start with Week 1-2 tasks: implement real auth + database
4. Then Week 3-4: extraction pipeline
5. Iterate, test, deploy

Good luck! This is a substantial build but very doable in 7 weeks.
