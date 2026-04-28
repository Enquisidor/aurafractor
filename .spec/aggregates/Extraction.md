## Aggregate: Extraction

**Bounded context:** Extraction
**Purpose:** Represents a single ML separation job — from label input through Cloud Tasks queueing to completed stems — and enforces the credit cost and job lifecycle invariants.

---

### Aggregate Root

**Entity name:** Extraction
**Identity type:** UUID v4 (`extraction_id`)
**Description:** Created when a user submits an extraction request. Encapsulates the sources requested (labels + NLP params), job status, credit cost, and optional reference to a parent extraction (for re-extractions). Results are stored in ExtractionResult once the worker completes.

**Invariants enforced by the root:**
- `PositiveCreditCost`: credit_cost must be > 0
- `ValidStatus`: status must be one of (queued, processing, completed, failed)
- `ImmutableSourcesOnceQueued`: sources_requested must not change after the job is queued
- `CompletedRequiresResult`: an extraction in status=completed must have an associated ExtractionResult

---

### Child Entities

| Entity | Identity Type | Purpose | Relationship to Root |
|---|---|---|---|
| ExtractionResult | UUID v4 (result_id) | Stores completed stem URLs and waveform data | An Extraction has at most one ExtractionResult; created only on completion |

---

### Value Objects

| Value Object | Attributes | Validation Rules | Notes |
|---|---|---|---|
| SourceRequest | label: string, model: enum, nlp_params: JSON, timestamps: JSON | label non-empty; model valid | Immutable after creation |
| ExtractionStatus | value: enum (queued\|processing\|completed\|failed) | Must be one of four values | |
| NlpParams | parsed extraction parameters | [PLACEHOLDER] | Derived from label by NLP engine |
| AmbiguityScore | value: float | >= 0 | Labels above threshold require user confirmation and surcharge |

---

### Domain Events

| Event Name (past tense) | Trigger Condition | Key Payload Fields | Scope |
|---|---|---|---|
| ExtractionQueued | When job is submitted to Cloud Tasks | extraction_id, track_id, user_id, credit_cost | Published to Credits |
| ExtractionCompleted | When worker delivers results | extraction_id, sources (stem URLs) | Internal |
| ExtractionFailed | When worker reports failure | extraction_id, error_message | Published to Credits (refund) |

---

### Repository Interface

- `findById(extraction_id: UUID)` → `Extraction | null`
- `findByTrackId(track_id: UUID)` → `Extraction[]`
- `findByJobId(job_id: string)` → `Extraction | null` — used by worker webhook
- `save(extraction: Extraction)` → `void`
- `findByUserId(user_id: UUID, page: int, per_page: int)` → `Extraction[]`

---

### Lifecycle

**States:** queued, processing, completed, failed
**Transitions:**
- queued → processing: when worker picks up the Cloud Tasks job
- processing → completed: when worker delivers stems successfully
- processing → failed: when worker reports an error

**Terminal states:** completed, failed — no further transitions

**Invalid transitions:**
- completed → any state: not permitted
- failed → any state: not permitted (re-extraction creates a new Extraction with iteration_id reference)

---

### Persistence Notes

- **Storage model:** Relational (PostgreSQL); `sources_requested` and result `sources` stored as JSONB
- **Soft delete:** No — extractions are immutable records
- **Optimistic concurrency:** Not required — status transitions are driven by the worker callback only
- **Indexing:** `idx_extractions_status`, `idx_extractions_job_id`, `idx_extractions_track_id`
- **PII:** No direct PII; sources_requested may contain user-typed labels

---

### Open Questions

- [ ] Should failed extractions be retried automatically by Cloud Tasks, or is manual re-extraction (new Extraction) the only path? — Assigned to: Architect
- [ ] What is the worker timeout? What status does the extraction take if the worker never calls back? — Assigned to: Architect
