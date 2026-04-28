## Aggregate: CreditAccount

**Bounded context:** Credits
**Purpose:** The authoritative record of a user's current credit balance; enforces the non-negative balance invariant and manages monthly allowance resets.

---

### Aggregate Root

**Entity name:** CreditAccount
**Identity type:** Natural key: `user_id` (UUID v4, FK to Identity.User)
**Description:** One CreditAccount per user. Tracks current balance, monthly allowance (set by subscription tier), and the next reset date. All debit and credit operations go through this aggregate to enforce invariants.

**Invariants enforced by the root:**
- `BalanceNonNegative`: credits_balance must always be >= 0; a debit that would produce a negative balance must be rejected
- `AllowanceMatchesTier`: credits_monthly_allowance must correspond to the user's current subscription tier (free: 100, pro: 500, studio: unlimited)
- `ResetDateConsistency`: credits_reset_date must be a future date or null

---

### Child Entities

n/a — CreditTransaction is a separate aggregate (immutable ledger).

---

### Value Objects

| Value Object | Attributes | Validation Rules | Notes |
|---|---|---|---|
| CreditAmount | value: int | Must be >= 0 | Credits are whole units only; no fractions |
| MonthlyAllowance | value: int | Must be > 0 | Derived from SubscriptionTier |

---

### Domain Events

| Event Name (past tense) | Trigger Condition | Key Payload Fields | Scope |
|---|---|---|---|
| CreditDebited | When credits are deducted for an extraction | user_id, amount, balance_before, balance_after, extraction_id | Internal |
| CreditRefunded | When credits are returned (e.g., failed extraction) | user_id, amount, balance_before, balance_after, extraction_id | Internal |
| MonthlyAllowanceReset | When the monthly reset date is reached | user_id, new_balance, subscription_tier | Internal |

---

### Repository Interface

- `findByUserId(user_id: UUID)` → `CreditAccount | null`
- `save(account: CreditAccount)` → `void` — uses optimistic concurrency (see below)
- `debit(user_id: UUID, amount: int, extraction_id: UUID)` → `CreditTransaction` — atomically deducts and records transaction
- `refund(user_id: UUID, amount: int, extraction_id: UUID)` → `CreditTransaction` — atomically credits and records transaction

---

### Lifecycle

n/a — CreditAccount has no terminal state; it persists for the lifetime of the user.

---

### Persistence Notes

- **Storage model:** Relational (PostgreSQL); balance stored on `users` table (`credits_balance`, `credits_monthly_allowance`, `credits_reset_date`)
- **Soft delete:** No — balance is reset to 0 on user deletion
- **Optimistic concurrency:** Required — concurrent extraction requests could race on the balance; use a transaction with SELECT FOR UPDATE or equivalent
- **Indexing:** Primary key is user_id (via users table)
- **PII:** No direct PII in balance columns

---

### Open Questions

- [ ] Studio tier is "unlimited" — how is this represented in the balance? (Very high ceiling integer vs. a flag?) — Assigned to: Architect
- [ ] Is monthly reset driven by a cron job or lazy-evaluated on each debit? — Assigned to: Architect
