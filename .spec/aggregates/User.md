## Aggregate: User

**Bounded context:** Identity
**Purpose:** Represents a registered anonymous device; the root identity to which all tracks, extractions, and credits belong.

---

### Aggregate Root

**Entity name:** User
**Identity type:** UUID v4 (`user_id`)
**Description:** Created on first device registration. Has no email or password — identified only by device_id. Owns subscription tier and a soft-delete flag for GDPR compliance.

**Invariants enforced by the root:**
- `BalanceNonNegative`: credits_balance must always be >= 0 (enforced by DB constraint and Credits context)
- `DeviceIdUnique`: device_id must be unique across all users
- `ValidSubscriptionTier`: subscription_tier must be one of (free, pro, studio)

---

### Child Entities

n/a — Sessions are a separate aggregate.

---

### Value Objects

| Value Object | Attributes | Validation Rules | Notes |
|---|---|---|---|
| DeviceId | value: string (max 255) | Non-null, non-empty, unique | Provided by client; opaque to the server |
| SubscriptionTier | value: enum (free\|pro\|studio) | Must be one of three values | Determines monthly credit allowance |

---

### Domain Events

| Event Name (past tense) | Trigger Condition | Key Payload Fields | Scope |
|---|---|---|---|
| UserRegistered | When a new device_id is registered for the first time | user_id, device_id, subscription_tier, credits_monthly_allowance | Published to Credits |
| UserDeleted | When GDPR deletion is requested (DELETE /track/{id} cascade or direct delete) | user_id | Published to all contexts |

---

### Repository Interface

- `findById(user_id: UUID)` → `User | null`
- `findByDeviceId(device_id: string)` → `User | null`
- `save(user: User)` → `void`
- `softDelete(user_id: UUID)` → `void` — sets deleted_at timestamp; cascades to tracks and sessions

---

### Lifecycle

**States:** active, deleted
**Transitions:**
- active → deleted: when GDPR deletion is requested

**Terminal states:** deleted — no further operations permitted; sessions invalidated, tracks cascade-deleted

**Invalid transitions:** deleted → active is not permitted

---

### Persistence Notes

- **Storage model:** Relational (PostgreSQL)
- **Soft delete:** Yes — `deleted_at TIMESTAMP NULL`; deleted users excluded from all queries via `WHERE deleted_at IS NULL`
- **Optimistic concurrency:** Not required — user updates are infrequent and not concurrent
- **Indexing:** `idx_users_device_id` (unique lookup on registration/login)
- **PII:** Yes — `device_id` is a device identifier; subject to GDPR deletion policy

---

### Open Questions

- [ ] Should reactivation of a soft-deleted user be possible? — Assigned to: Architect
