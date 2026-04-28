## Bounded Context: Extraction

**Purpose:** Responsible for translating user-provided source labels into ML extraction parameters, queuing async separation jobs via Cloud Tasks, and delivering completed stems back to users.

**Owner:** Architect owns all contexts.

---

### Responsibility Boundary

**This context owns:**
- NLP label → extraction parameters mapping (50+ rules, ambiguity scoring)
- Extraction job lifecycle (queued → processing → completed | failed)
- Credit cost computation and deduction (delegating deduction to Credits)
- Cloud Tasks job enqueueing and worker callback handling
- Stem audio results stored in GCS
- ExtractionResults (stems with audio URLs and waveform URLs)
- Re-extraction triggered by Feedback

**This context explicitly does not own:**
- Original audio track storage — belongs to Audio
- Recording of user feedback — belongs to Feedback
- Credit balance — belongs to Credits

---

### Core Model

**Aggregate roots:**
- [Extraction](../aggregates/Extraction.md): a single extraction job for one track; owns its job status, sources requested, and credit cost

**Value objects (context-level):**
- `SourceRequest`: {label, model, nlp_params, timestamps} — immutable specification for one stem to separate
- `NlpParams`: parsed extraction parameters derived from a free-text label
- `AmbiguityScore`: numeric score; labels above threshold require surcharge and user confirmation
- `ExtractionStatus`: enum (queued | processing | completed | failed)

**Domain events produced:**
- `ExtractionQueued`: triggered when job is enqueued; payload: extraction_id, track_id, user_id, credit_cost; scope: Published to Credits
- `ExtractionCompleted`: triggered when worker delivers results; payload: extraction_id, sources (stems); scope: Internal
- `ExtractionFailed`: triggered on worker failure; payload: extraction_id, error; scope: Internal → Credits (for refund)

**Domain events consumed:**
- `TrackUploaded` from Audio: makes track available for extraction requests
- `FeedbackSubmitted` from Feedback: triggers re-extraction with refined labels

---

### Context Map

| Adjacent Context | Relationship Type | Integration Mechanism | Notes |
|---|---|---|---|
| Audio | Conformist | sync — track_id FK | Extraction reads track metadata but does not own it |
| Credits | Customer–Supplier | sync REST call | Extraction requests deduction; Credits enforces balance invariant |
| Feedback | Customer–Supplier | async — re-extraction trigger | Feedback supplies refined labels; Extraction owns the resulting job |
| Identity | Conformist | sync — user_id FK | Extractions are owned by users; auth enforced at API boundary |

---

### Ubiquitous Language (context-specific terms)

| Term | Definition within this context | Anti-patterns (do not use) |
|---|---|---|
| Extraction | A complete job request to separate one or more sources from a track | "job", "task", "request" |
| Source | A single instrument or stem to be separated, defined by a label and model | "track" (collides with Audio), "stem" (use only for results) |
| Stem | A completed audio output produced by the ML worker for a single source | "source" (use "source" only for the input spec) |
| Label | Free-text user input describing a source (e.g., "lead vocals without reverb") | "tag", "description" |
| Iteration | A re-extraction that references a prior extraction_id as its parent | "retry", "redo" |

---

### Open Questions

- [ ] Should failed extractions auto-refund credits, or require user action? — Assigned to: Architect
- [ ] What is the retry policy for Cloud Tasks worker failures? — Assigned to: Architect
