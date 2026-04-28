## Aggregate: Track

**Bounded context:** Audio
**Purpose:** Represents a user-uploaded audio file; the source material from which stems are extracted.

---

### Aggregate Root

**Entity name:** Track
**Identity type:** UUID v4 (`track_id`)
**Description:** Created when a user uploads an audio file. Stores the GCS path, format metadata, and spectral analysis results. Soft-deleted on user request (GDPR) or when the user account is deleted.

**Invariants enforced by the root:**
- `ValidFormat`: format must be one of (mp3, wav, flac, ogg)
- `PositiveDuration`: duration_seconds must be > 0
- `GcsPathPresent`: gcs_path must be non-null and non-empty at creation
- `UniqueClientId`: (user_id, client_id) must be unique when client_id is non-null (deduplication)

---

### Child Entities

n/a — ExtractionResults are owned by Extraction, not by Track.

---

### Value Objects

| Value Object | Attributes | Validation Rules | Notes |
|---|---|---|---|
| AudioFormat | value: enum (mp3\|wav\|flac\|ogg) | Must be one of four values | |
| GcsPath | value: string (max 512) | Non-null, non-empty | Immutable after upload |
| SpectralHash | value: string (max 256) | Optional; used for deduplication detection | |

---

### Domain Events

| Event Name (past tense) | Trigger Condition | Key Payload Fields | Scope |
|---|---|---|---|
| TrackUploaded | When a track is successfully stored in GCS and the DB record created | track_id, user_id, duration_seconds, format, gcs_path | Published to Extraction |
| TrackDeleted | When soft-delete is applied (GDPR or cascade) | track_id, user_id | Published to Extraction, Feedback |

---

### Repository Interface

- `findById(track_id: UUID)` → `Track | null`
- `findByUserId(user_id: UUID, page: int, per_page: int)` → `Track[]`
- `findByClientId(user_id: UUID, client_id: string)` → `Track | null` — deduplication check
- `save(track: Track)` → `void`
- `softDelete(track_id: UUID)` → `void` — sets deleted_at; GCS cleanup is async

---

### Lifecycle

**States:** active, deleted
**Transitions:**
- active → deleted: when user requests deletion or user account is deleted

**Terminal states:** deleted — GCS file should be scheduled for cleanup

**Invalid transitions:** deleted → active is not permitted

---

### Persistence Notes

- **Storage model:** Relational (PostgreSQL)
- **Soft delete:** Yes — `deleted_at TIMESTAMP NULL`; active tracks require `WHERE deleted_at IS NULL`
- **Optimistic concurrency:** Not required
- **Indexing:** `idx_tracks_user_id`, `idx_tracks_uploaded_at`, `idx_tracks_user_client_id` (unique partial)
- **PII:** Yes — filename may contain PII; subject to GDPR deletion

---

### Open Questions

- [ ] Maximum file size is 200 MB — is this enforced at the API layer only or also in the aggregate? — Assigned to: Architect
