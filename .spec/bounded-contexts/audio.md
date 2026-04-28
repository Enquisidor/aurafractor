## Bounded Context: Audio

**Purpose:** Responsible for accepting, validating, and storing user-uploaded audio tracks, and providing access to stored audio files via GCS.

**Owner:** Architect owns all contexts.

---

### Responsibility Boundary

**This context owns:**
- Audio file upload, validation (format, size, duration), and storage to GCS
- Track metadata (filename, format, duration, sample rate, spectral hash, genre/tempo detection)
- Instrument label suggestions (spectral classifier + user history cache)
- Track deletion (GDPR)

**This context explicitly does not own:**
- Extraction jobs — belongs to Extraction
- Feedback on extracted stems — belongs to Feedback
- Credit deduction for uploads — belongs to Credits

---

### Core Model

**Aggregate roots:**
- [Track](../aggregates/Track.md): an uploaded audio file with its metadata and GCS storage reference

**Value objects (context-level):**
- `AudioFormat`: enum (mp3 | wav | flac | ogg)
- `GcsPath`: immutable reference to a file in Google Cloud Storage
- `SpectralHash`: fingerprint derived from audio content for deduplication

**Domain events produced:**
- `TrackUploaded`: triggered when a track is successfully stored; payload: track_id, user_id, duration_seconds, format, gcs_path; scope: Published to Extraction
- `TrackDeleted`: triggered when a track is deleted (GDPR); payload: track_id, user_id; scope: Published to Extraction, Feedback

**Domain events consumed:**
- `UserDeleted` from Identity: cascade-delete all tracks for the user

---

### Context Map

| Adjacent Context | Relationship Type | Integration Mechanism | Notes |
|---|---|---|---|
| Identity | Conformist | sync — user_id FK | Adopts Identity's user model at the boundary |
| Extraction | Customer–Supplier | sync — track_id FK | Audio supplies track reference; Extraction owns job lifecycle |

---

### Ubiquitous Language (context-specific terms)

| Term | Definition within this context | Anti-patterns (do not use) |
|---|---|---|
| Track | A single uploaded audio file owned by a user | "song", "file", "audio" |
| Stem | NOT a concept in this context — stems are produced by Extraction | Do not use "stem" here |
| Label Suggestion | An AI-generated instrument label recommendation produced by the spectral classifier for a given track | "tag", "suggestion" |

---

### Open Questions

- [ ] Should duplicate track detection (via spectral_hash) reject uploads or warn? — Assigned to: Architect
