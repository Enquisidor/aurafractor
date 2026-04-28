## Bounded Context: Feedback

**Purpose:** Responsible for capturing user quality assessments of extracted stems, optionally triggering re-extractions with refined labels, and feeding anonymized training data back into the ML pipeline.

**Owner:** Architect owns all contexts.

---

### Responsibility Boundary

**This context owns:**
- Feedback records (type, segment, label, refined label, comment)
- Re-extraction trigger (passes refined label back to Extraction)
- Anonymized training data records (non-reversible user hash, opt-in only)
- User opt-in preference for training data contribution

**This context explicitly does not own:**
- Extraction job lifecycle — belongs to Extraction
- Credit deduction for re-extractions — belongs to Credits (via Extraction)
- Original stems or audio — belongs to Audio / Extraction

---

### Core Model

**Aggregate roots:**
- [Feedback](../aggregates/Feedback.md): a single quality assessment for a specific segment of an extracted stem, with optional re-extraction request

**Value objects (context-level):**
- `FeedbackType`: enum (too_much | too_little | artifacts | good)
- `Segment`: {start_seconds, end_seconds} — time range within the stem being assessed; start must be < end
- `AnonymizedUserId`: 8-char non-reversible hash of user_id; used in training data only

**Domain events produced:**
- `FeedbackSubmitted`: triggered when feedback is recorded; payload: feedback_id, extraction_id, feedback_type, refined_label (if any); scope: Published to Extraction (if re-extraction requested)
- `TrainingDataRecorded`: triggered when opt-in feedback is anonymized and stored; payload: training_id; scope: Internal

**Domain events consumed:**
- `UserDeleted` from Identity: anonymize or delete feedback records per GDPR policy
- `ExtractionCompleted` from Extraction: makes extraction available for feedback

---

### Context Map

| Adjacent Context | Relationship Type | Integration Mechanism | Notes |
|---|---|---|---|
| Extraction | Customer–Supplier | sync — extraction_id FK + re-extraction trigger | Feedback is downstream; triggers re-extraction via Extraction API |
| Identity | Conformist | sync — user_id FK + opt_in_training_data flag | Respects user's training data opt-in at record time |

---

### Ubiquitous Language (context-specific terms)

| Term | Definition within this context | Anti-patterns (do not use) |
|---|---|---|
| Feedback | A structured user assessment of one segment of one stem | "rating", "review", "comment" |
| Refined Label | An updated source label the user provides to improve a re-extraction | "new label", "corrected label" |
| Training Data | Anonymized, opt-in feedback records used to improve the NLP label engine and ML models | "dataset", "training sample" |
| Segment | A time-bounded portion of a stem under assessment {start_seconds, end_seconds} | "clip", "range", "window" |

---

### Open Questions

- [ ] GDPR: on UserDeleted, should training_data rows be hard-deleted or have user_id_anon nulled? — Assigned to: Architect
