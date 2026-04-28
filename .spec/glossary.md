# Ubiquitous Language Glossary — Aurafractor

The Architect owns and maintains this file. All agents must use the canonical term from this file in code, API fields, comments, log messages, and inter-agent communication.

---

## How to use this glossary

- Every term used in `.spec/api-contracts.md`, `.spec/domain-model.md`, `.spec/schema.md`, or any implementation issue must have an entry here.
- When writing code: use the canonical identifier exactly (PascalCase for types, snake_case for fields and columns). No abbreviations, synonyms, or informal variations.
- When in doubt about a term: check this file before inventing a name.

---

## Core Terms (All Contexts)

---

### User · All Contexts

**Definition:** An anonymous registered device identity. Not a traditional user account — there is no email or password. A User is created the first time a device_id is seen, and all tracks, extractions, and credits are owned by this identity.

**Canonical identifier in code:** `User` (type), `user_id` (field)

**Related terms:**
- Session: a live authentication context belonging to a User
- DeviceId: the registration credential for a User

**Synonyms (DO NOT USE in code or communication):**
- "account": implies email/password auth which does not exist
- "member", "profile": not applicable

---

### Track · All Contexts

**Definition:** A single uploaded audio file owned by a User. The source material from which stems are extracted. Has format, duration, and a GCS storage path.

**Canonical identifier in code:** `Track` (type), `track_id` (field)

**Related terms:**
- Extraction: a job that processes a Track to produce Stems
- Stem: an output produced from a Track via Extraction

**Synonyms (DO NOT USE):**
- "song": too informal; a Track may not be a complete song
- "file": too generic; use Track when referring to domain objects

---

### Extraction · All Contexts

**Definition:** A single ML source separation job. Takes a Track and one or more SourceRequests (labels), runs the ML worker, and produces Stems. Has a lifecycle: queued → processing → completed | failed.

**Canonical identifier in code:** `Extraction` (type), `extraction_id` (field)

**Related terms:**
- Track: the source material for an Extraction
- Stem: an output produced by an Extraction
- Feedback: a quality assessment submitted against an Extraction

**Synonyms (DO NOT USE):**
- "job": use Extraction in domain language; "job" may appear in infrastructure code only
- "task": collides with Cloud Tasks infrastructure term

---

### Stem · All Contexts

**Definition:** A completed audio output produced by the ML worker for a single SourceRequest within an Extraction. Has an audio URL and waveform URL in GCS.

**Canonical identifier in code:** `Stem` (type in results context), `sources` (JSONB field in extraction_results)

**Related terms:**
- Extraction: the job that produced the Stem
- SourceRequest: the input specification that the Stem was produced from

**Synonyms (DO NOT USE):**
- "source": use SourceRequest for inputs, Stem for outputs — do not conflate
- "track": collides with the Track aggregate

---

### Label · All Contexts

**Definition:** Free-text user input describing an audio source to extract (e.g., "lead vocals without reverb", "tight kick"). Processed by the NLP engine to produce NlpParams.

**Canonical identifier in code:** `label` (field)

**Related terms:**
- NlpParams: the structured extraction parameters derived from a Label
- AmbiguityScore: a numeric measure of how vague a Label is

**Synonyms (DO NOT USE):**
- "tag": implies predefined taxonomy; Labels are free-form
- "description": too generic

---

### Credit · All Contexts

**Definition:** A unit of account consumed by extraction operations. Not a currency — credits cannot be purchased directly (they are granted by subscription tier on a monthly basis).

**Canonical identifier in code:** `credit` (singular), `credits_balance` (field)

**Synonyms (DO NOT USE):**
- "token": collides with authentication tokens
- "point": too informal

---

## Context-Specific Terms

### Identity

---

#### DeviceId · Identity

**Definition:** The opaque string provided by the client device at registration time. The sole credential for authentication — there is no password. Immutable after registration.

**Canonical identifier in code:** `device_id`

**Synonyms (DO NOT USE):** "username", "login", "client_id" (client_id is a separate Track deduplication field)

---

#### Session · Identity

**Definition:** A live authentication context consisting of a short-lived JWT access token and a long-lived refresh token. Created on registration or token refresh.

**Canonical identifier in code:** `Session` (type), `session_id` (field)

**Synonyms (DO NOT USE):** "login session", "auth token" (use "session token" or "access token" specifically)

---

### Audio

---

#### LabelSuggestion · Audio

**Definition:** An AI-generated instrument label recommendation produced by the spectral classifier for a given Track, before any Extraction is requested. Not the same as a user-provided Label.

**Canonical identifier in code:** `suggestion` (field in suggestions JSONB)

**Differs from Extraction usage:** In Extraction, "label" refers to the user-provided source description. A LabelSuggestion is a pre-extraction recommendation that may or may not be used.

---

### Extraction

---

#### SourceRequest · Extraction

**Definition:** The immutable input specification for a single source within an Extraction: {label, model, nlp_params, timestamps}. Created at job submission time and never modified.

**Canonical identifier in code:** `SourceRequest` (type), `sources_requested` (JSONB field)

**Differs from Feedback usage:** In Feedback, the user provides a RefinedLabel to correct a SourceRequest — but the SourceRequest itself is immutable.

---

#### Iteration · Extraction

**Definition:** A re-extraction that references a prior Extraction as its parent via `iteration_id`. Created when a user submits Feedback with a refined label requesting re-extraction.

**Canonical identifier in code:** `iteration_id` (FK field on Extraction)

**Synonyms (DO NOT USE):** "retry" (implies the original failed; an Iteration may refine a successful Extraction), "redo"

---

### Feedback

---

#### Segment · Feedback

**Definition:** A time-bounded portion of a Stem under assessment, defined by {start_seconds, end_seconds}. Invariant: start < end.

**Canonical identifier in code:** `segment_start_seconds`, `segment_end_seconds` (fields)

**Synonyms (DO NOT USE):** "clip", "range", "window"

---

#### RefinedLabel · Feedback

**Definition:** An updated source label provided by the user as part of Feedback, intended to improve a subsequent re-extraction.

**Canonical identifier in code:** `refined_label`

**Synonyms (DO NOT USE):** "new label", "corrected label", "updated tag"

---

### Credits

---

#### CreditAccount · Credits

**Definition:** The authoritative record of a user's current credit balance, monthly allowance, and reset date. The only place where credits are debited or credited.

**Canonical identifier in code:** `CreditAccount` (type); balance stored on `users` table as `credits_balance`

**Synonyms (DO NOT USE):** "wallet", "balance row"

---

#### CreditTransaction · Credits

**Definition:** An immutable ledger entry recording one credit debit or refund event, with before/after balances. Never updated or deleted.

**Canonical identifier in code:** `CreditTransaction` (type), `transaction_id` (field)

**Synonyms (DO NOT USE):** "transaction log entry", "history entry"

---

## Contested Terms

_(None currently — add entries here when ambiguity is discovered)_

---

## Retired Terms

_(None currently)_
