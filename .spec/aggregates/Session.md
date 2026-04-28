## Aggregate: Session

**Bounded context:** Identity
**Purpose:** Represents a live authenticated session; issues and validates JWT access tokens and refresh tokens.

---

### Aggregate Root

**Entity name:** Session
**Identity type:** UUID v4 (`session_id`)
**Description:** Created on successful registration or token refresh. Contains an access token (short-lived JWT) and a refresh token (long-lived opaque string). Expires at a fixed time.

**Invariants enforced by the root:**
- `SessionTokenUnique`: session_token must be unique across all sessions
- `RefreshTokenUnique`: refresh_token must be unique across all sessions
- `ExpiryInFuture`: expires_at must be after created_at at creation time

---

### Child Entities

n/a

---

### Value Objects

| Value Object | Attributes | Validation Rules | Notes |
|---|---|---|---|
| JwtToken | value: string (max 512) | Non-null; must be a valid signed JWT | Access token; short-lived |
| RefreshToken | value: string (max 512) | Non-null, unique | Long-lived opaque string for token refresh |

---

### Domain Events

| Event Name (past tense) | Trigger Condition | Key Payload Fields | Scope |
|---|---|---|---|
| SessionCreated | When a user registers or refreshes their token | session_id, user_id, expires_at | Internal |
| SessionExpired | When a session passes its expires_at timestamp | session_id, user_id | Internal |

---

### Repository Interface

- `findById(session_id: UUID)` → `Session | null`
- `findBySessionToken(token: string)` → `Session | null`
- `findByRefreshToken(token: string)` → `Session | null`
- `save(session: Session)` → `void`
- `deleteByUserId(user_id: UUID)` → `void` — invalidates all sessions on user deletion

---

### Lifecycle

**States:** active, expired
**Transitions:**
- active → expired: when current time > expires_at

**Terminal states:** expired

**Invalid transitions:** expired → active is not permitted (must create a new session via refresh)

---

### Persistence Notes

- **Storage model:** Relational (PostgreSQL)
- **Soft delete:** No — expired sessions may be hard-deleted on cleanup
- **Optimistic concurrency:** Not required
- **Indexing:** `idx_sessions_session_token`, `idx_sessions_expires_at`
- **PII:** Yes — session tokens are authentication credentials; subject to GDPR deletion

---

### Open Questions

- [ ] What is the access token TTL? What is the refresh token TTL? — Assigned to: Architect
