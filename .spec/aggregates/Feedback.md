## Aggregate: Feedback

**Bounded context:** Feedback
**Purpose:** Represents a user's quality assessment of a specific time segment within an extracted stem, optionally requesting re-extraction with a refined label.

---

### Aggregate Root

**Entity name:** Feedback
**Identity type:** UUID v4 (`feedback_id`)
**Description:** Created when a user submits a rating on an extracted stem segment. Contains the feedback type, the time segment assessed, and optionally a refined label for re-extraction. Immutable after creation.

**Invariants enforced by the root:**
- `ValidSegment`: segment_start_seconds must be < segment_end_seconds
- `ValidFeedbackType`: feedback_type must be one of (too_much, too_little, artifacts, good)
- `RefinedLabelRequiresReextraction`: if reextraction_id is set, refined_label should be present

---

### Child Entities

n/a

---

### Value Objects

| Value Object | Attributes | Validation Rules | Notes |
|---|---|---|---|
| Segment | start_seconds: int, end_seconds: int | start < end; both >= 0 | Time range within the stem being assessed |
| FeedbackType | value: enum (too_much\|too_little\|artifacts\|good) | Must be one of four values | |
| RefinedLabel | value: string (max 255) | Optional; non-empty if present | User's corrected label for re-extraction |

---

### Domain Events

| Event Name (past tense) | Trigger Condition | Key Payload Fields | Scope |
|---|---|---|---|
| FeedbackSubmitted | When feedback record is persisted | feedback_id, extraction_id, user_id, feedback_type, refined_label | Published to Extraction if re-extraction requested |
| TrainingDataRecorded | When opt-in feedback is anonymized and stored | training_id, user_id_anon | Internal |

---

### Repository Interface

- `findById(feedback_id: UUID)` → `Feedback | null`
- `findByExtractionId(extraction_id: UUID)` → `Feedback[]`
- `findByUserId(user_id: UUID)` → `Feedback[]`
- `save(feedback: Feedback)` → `void`

---

### Lifecycle

**States:** submitted (single terminal state — feedback is immutable)

**Invalid transitions:** Feedback cannot be edited after submission; corrections require a new Feedback record.

---

### Persistence Notes

- **Storage model:** Relational (PostgreSQL)
- **Soft delete:** No — feedback is immutable; GDPR handled by anonymization or cascade delete
- **Optimistic concurrency:** Not required
- **Indexing:** `idx_feedback_extraction_id`, `idx_feedback_user_id`
- **PII:** Yes — `segment_label`, `refined_label`, `comment` may contain user-typed content; `user_id` is a PII reference

---

### Open Questions

- [ ] GDPR: should feedback rows be hard-deleted on UserDeleted, or should user_id be nulled and content retained for training? — Assigned to: Architect
