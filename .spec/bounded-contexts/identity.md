## Bounded Context: Identity

**Purpose:** Responsible for anonymous device-based user registration, session lifecycle, and JWT token issuance and refresh.

**Owner:** Architect owns all contexts.

---

### Responsibility Boundary

**This context owns:**
- User registration via device ID (anonymous, no email/password)
- Session tokens (JWT access + refresh tokens)
- Subscription tier assignment (free / pro / studio)
- GDPR deletion of user accounts

**This context explicitly does not own:**
- Credit balances — belongs to Credits
- Track or extraction data — belongs to Audio / Extraction
- Training opt-in preference setting (storage owned here, but the opt-in decision is a Feedback concern)

---

### Core Model

**Aggregate roots:**
- [User](../aggregates/User.md): represents a registered anonymous device; owns subscription tier and credit balance metadata
- [Session](../aggregates/Session.md): a live authenticated session with access and refresh tokens

**Value objects (context-level):**
- `DeviceId`: opaque string uniquely identifying a device; immutable after registration
- `SubscriptionTier`: enum (free | pro | studio); determines monthly credit allowance

**Domain events produced:**
- `UserRegistered`: triggered when a new device_id is registered; payload: user_id, subscription_tier, credits_monthly_allowance; scope: Published to Credits
- `UserDeleted`: triggered when GDPR deletion is requested; payload: user_id; scope: Published to all contexts

**Domain events consumed:**
- n/a

---

### Context Map

| Adjacent Context | Relationship Type | Integration Mechanism | Notes |
|---|---|---|---|
| Credits | Customer–Supplier | sync — user_id foreign key | Identity is the supplier; Credits reads user tier to set allowance |
| Audio | Customer–Supplier | sync — user_id foreign key | Identity supplies user identity; Audio stores user_id on tracks |
| Extraction | Customer–Supplier | sync — user_id foreign key | Identity supplies authenticated user_id to all extraction operations |
| Feedback | Customer–Supplier | sync — user_id foreign key | Identity supplies user_id; Feedback stores opt_in_training_data preference |

---

### Ubiquitous Language (context-specific terms)

| Term | Definition within this context | Anti-patterns (do not use) |
|---|---|---|
| User | An anonymous registered device identity; not a human account in the traditional sense | "account", "member", "profile" |
| DeviceId | The opaque client-provided string that uniquely identifies a device; the only registration credential | "username", "login" |
| Session | A live authentication context consisting of an access JWT and a refresh token | "login session", "auth token" |
| SubscriptionTier | The plan level (free/pro/studio) that controls monthly credit allowance | "plan", "tier level" |

---

### Open Questions

- [ ] Should studio-tier dev device IDs (DEV_DEVICE_IDS env var) be formalized as a first-class concept or remain an env-var override? — Assigned to: Architect
