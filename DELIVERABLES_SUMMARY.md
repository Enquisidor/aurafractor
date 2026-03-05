# Backend Design - Complete Deliverables Summary

You now have everything you need to start building the Backend Instance. Here's what's been created and how to use it.

---

## 📦 What You Have

### Documentation (Read These First)
1. **README.md** - Project overview, quick start, architecture
2. **BACKEND_DESIGN.md** - Complete system design (API contracts, database schema, NLP engine, deployment)
3. **BACKEND_INITIAL_PROMPT.md** - Detailed implementation roadmap for Claude Code (phases, tasks, testing strategy)
4. **QUICKSTART.md** - Local development setup and API testing examples

### Code (Ready to Use)
5. **app.py** - Flask app with all 10 endpoints stubbed (mock responses)
6. **schema.sql** - Complete PostgreSQL database schema
7. **requirements.txt** - All Python dependencies
8. **.env.example** - Environment variables template

### Local Development (Docker)
9. **docker-compose.yml** - PostgreSQL + Flask API + pgAdmin
10. **Dockerfile.dev** - Development container with auto-reload

### Testing
11. **tests/test_example.py** - Example test patterns (27 tests showing how to test each part)

### NLP Rules (Baked In)
The app.py includes a complete **NLP rule engine** with:
- 40+ label rules (vocals, drums, bass, synth, guitar, etc.)
- Descriptor modifiers (dry, tight, isolated, with, without, just)
- **Ambiguity scoring function** (0.0 = clear, 1.0 = ambiguous)
- Label parsing → extraction parameters

---

## 🚀 How to Use This

### Phase 1: Read & Understand

```
1. Start with README.md (get the overview)
2. Skim BACKEND_DESIGN.md (understand the full scope)
3. Deep read BACKEND_INITIAL_PROMPT.md (this is your roadmap)
4. Check QUICKSTART.md (see how to test locally)
```

This takes ~1 hour and gives you the mental model.

### Phase 2: Set Up Local Development

```bash
# Clone/create backend repo with all the files above
git init
cp -r <outputs>/* .

# Start services
docker-compose up -d

# Verify
curl http://localhost:5000/health
```

Takes ~5 minutes.

### Phase 3: Spin Up Backend Instance

When ready to implement, provide Claude Code with:

```
Your task: Build the Backend Instance according to BACKEND_INITIAL_PROMPT.md

Context files (read first):
- BACKEND_DESIGN.md (reference this for API contracts)
- BACKEND_INITIAL_PROMPT.md (this is your detailed roadmap)
- schema.sql (understand the database structure)
- app.py (understand the endpoint structure)

Current status:
- All endpoints are stubbed with mock responses
- NLP rule engine is implemented
- Database schema is designed
- Test examples are provided

Your job:
Replace mocks with real implementations following the 7-week roadmap.
```

---

## 🎯 Key Concepts (Important!)

### 1. Labels are Flexible & Free-Form
- "vocals" ✅ (single word, perfectly valid)
- "lead vocals" ✅ (multi-word)
- "lead vocals without reverb" ✅ (descriptive)
- "thing" ❌ (ambiguous, flagged, costs extra)

### 2. NLP Ambiguity Scoring
```python
compute_ambiguity_score("vocals")      # → 0.1 (clear)
compute_ambiguity_score("lead vocals") # → 0.2 (clear)
compute_ambiguity_score("thing")       # → 0.95 (ambiguous)
compute_ambiguity_score("")            # → 1.0 (maximally ambiguous)

If score > 0.6 → flag to user, costs 1 extra credit
```

### 3. Label → Parameters Pipeline
```python
parse_label_to_params("lead vocals without reverb")
# Returns:
{
  'source': 'vocal',
  'vocal_type': 'lead',
  'isolation_level': 0.9,
  'dryness': 0.95,
  'preserve_reverb': False
}
```

These parameters guide Demucs/Spleeter extraction.

### 4. Feedback Loop
```
User hears extraction
  ↓
Marks segment as "good" OR provides feedback
  ↓
If "good" → move on
If feedback (too_much, too_little, artifacts) → can refine label
  ↓
Refined label gets stored as training signal
  ↓
Next extraction learns from previous feedback
```

### 5. Credit System
```
Free tier:
  - 100 credits/month
  - Each extraction: 5 credits (basic) or 20 credits (re-extraction)
  - Ambiguous label: +1 credit penalty
  - Result: ~20 extractions/month

Pro tier:
  - 500 credits/month (~100 extractions)

Studio tier:
  - Unlimited
```

---

## 📋 Implementation Roadmap (Your Claude Code Tasks)

When you spin up Backend Instance, it will follow this:

### Week 1-2: Foundation
- PostgreSQL integration (replace mock responses)
- User registration & auth (real JWT)
- Database query builders
- Connection pooling

### Week 3-4: Extraction Pipeline
- Audio upload → GCS
- Model wrappers (Demucs, Spleeter)
- Cloud Tasks integration
- Webhook handlers

### Week 5-6: NLP & Feedback
- Instrument classifier (from audio features)
- Label suggestion endpoint (real predictions)
- Feedback recording & re-extraction
- Credit deduction & enforcement

### Week 7: Polish & Deploy
- Error handling & validation
- Logging & monitoring
- Rate limiting
- Terraform configs

---

## 🧪 Testing Your Work

### Local Testing (No Cloud Needed)
```bash
# All mock responses work out of the box
curl -X POST http://localhost:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"device_id": "test", "app_version": "1.0.0"}'

# See QUICKSTART.md for full examples
```

### Unit Tests
```bash
pytest tests/test_example.py -v

# Tests included:
- Auth (register, refresh)
- NLP (label parsing, ambiguity scoring)
- Upload, extraction, feedback
- Credits, history
```

### Real Database Testing
```bash
# Once you implement real queries:
docker exec music-separation-db psql -U postgres -d music_separation
SELECT * FROM users;
SELECT * FROM extractions;
SELECT * FROM feedback;
```

---

## 🔑 Critical Implementation Points

### PostgreSQL
- Use **prepared statements** (prevent SQL injection)
- Implement **connection pooling** (already stubbed)
- Use **transactions** for credit deduction (atomic)
- Create indexes on common queries (user_id, created_at)

### NLP
- The rule engine is ready to use (don't reinvent)
- Ambiguity scoring should happen before queueing extraction
- If score > 0.6 → flag to user, they refine label, costs 1 credit
- Store feedback for training (anonymized)

### Credit System
- Deduct credits **before** queuing job (prevent refund complexity)
- Track all transactions in credit_transactions table
- Enforce monthly limits per subscription tier
- Handle free tier cutoff (can't extract if no credits)

### Privacy
- Hash user_id for training data (non-reversible)
- Delete original audio after 7 days
- Delete extracted stems after 30 days
- Keep anonymized feedback indefinitely
- Respect user opt-in preference

### Error Handling
- Validation: track_id, user_id format
- Graceful: if GCS fails, queue for retry, don't lose data
- Logging: every important operation
- Monitoring: extraction success rate, queue depth

---

## 📚 File Reference

| File | Purpose | Status |
|------|---------|--------|
| README.md | Project overview | ✅ Complete |
| BACKEND_DESIGN.md | System design | ✅ Complete |
| BACKEND_INITIAL_PROMPT.md | Implementation guide | ✅ Complete |
| QUICKSTART.md | Local testing | ✅ Complete |
| app.py | Flask app (mocks) | ✅ Complete |
| schema.sql | Database schema | ✅ Complete |
| requirements.txt | Dependencies | ✅ Complete |
| docker-compose.yml | Local dev | ✅ Complete |
| tests/test_example.py | Test patterns | ✅ Complete |
| services/*.py | (To implement) | ⏳ Next |
| models/*.py | (To implement) | ⏳ Next |
| terraform/*.tf | (To implement) | ⏳ Next |

---

## ✅ Checklist for Backend Instance

When spinning up Backend Instance, provide:

- [ ] These 4 core files:
  - [ ] README.md (overview)
  - [ ] BACKEND_DESIGN.md (reference)
  - [ ] BACKEND_INITIAL_PROMPT.md (your roadmap)
  - [ ] app.py (current state)

- [ ] This instruction:
  "Build according to BACKEND_INITIAL_PROMPT.md, weeks 1-7 timeline. Replace mocks with real database, Cloud Tasks, and models. See BACKEND_DESIGN.md for API contracts."

- [ ] Your decisions confirmed:
  - [ ] PostgreSQL ✅
  - [ ] 1-word labels allowed ✅
  - [ ] Max 4 concurrent extractions ✅
  - [ ] Privacy: opt-in training data ✅
  - [ ] Mock responses for local dev ✅
  - [ ] React Native for mobile (coming later) ✅

---

## 🎓 Next Steps

1. **Now**: Read README.md + BACKEND_INITIAL_PROMPT.md (1 hour)
2. **Soon**: Set up local dev with docker-compose (5 min)
3. **When Ready**: Spin up Backend Instance with BACKEND_INITIAL_PROMPT.md (7 weeks)
4. **After That**: Spin up NLP Instance using Backend's API (2-3 weeks)
5. **Then**: Mobile Instance using both Backend + NLP (4 weeks)

---

## 📞 Questions?

If something isn't clear:
- BACKEND_DESIGN.md has all API contracts
- BACKEND_INITIAL_PROMPT.md has detailed tasks
- QUICKSTART.md has testing examples
- schema.sql has the data model
- app.py has the endpoint structure

Everything is documented. You have a complete blueprint.

---

## 🎯 Success Criteria

By end of Backend Instance (Week 7), you'll have:

✅ Full PostgreSQL integration (no more mocks)
✅ Audio upload & GCS storage working
✅ Demucs + Spleeter model wrappers
✅ Cloud Tasks job queue operational
✅ Instrument classifier functional
✅ Feedback loop with re-extraction
✅ Credit system enforced
✅ Privacy pipeline (anonymization, deletion)
✅ 80%+ test coverage
✅ Deployable to Cloud Run
✅ Complete API documentation
✅ Monitoring & logging setup

Then NLP & Mobile instances can build on top of this solid foundation.

---

Good luck! 🚀
