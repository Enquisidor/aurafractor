## Aggregate: CreditTransaction

**Bounded context:** Credits
**Purpose:** An immutable ledger entry recording a single credit debit or refund event, with before/after balances for auditability.

---

### Aggregate Root

**Entity name:** CreditTransaction
**Identity type:** UUID v4 (`transaction_id`)
**Description:** Created atomically alongside every CreditAccount debit or refund. Never updated or deleted. Provides a full audit trail of all credit movements for a user.

**Invariants enforced by the root:**
- `ImmutableOnceCreated`: no fields may change after creation
- `BalanceConsistency`: balance_after must equal balance_before + amount (amount is negative for debits)
- `NonZeroAmount`: amount must not be 0

---

### Child Entities

n/a

---

### Value Objects

| Value Object | Attributes | Validation Rules | Notes |
|---|---|---|---|
| TransactionAmount | value: int | Non-zero; negative = debit, positive = credit/refund | |
| CreditReason | value: string (max 255) | Non-null, non-empty | Human-readable reason (e.g., "single-source extraction", "monthly reset") |

---

### Domain Events

n/a — CreditTransaction is itself the event record; no further events are produced.

---

### Repository Interface

- `findByUserId(user_id: UUID, page: int, per_page: int)` → `CreditTransaction[]`
- `findByExtractionId(extraction_id: UUID)` → `CreditTransaction[]`
- `save(transaction: CreditTransaction)` → `void` — insert only; updates must be rejected

---

### Lifecycle

n/a — single terminal state: created. Immutable.

---

### Persistence Notes

- **Storage model:** Relational (PostgreSQL) — `credit_transactions` table
- **Soft delete:** No — ledger entries are permanent; never deleted even on GDPR user deletion (amount/reason may be anonymized, but the record is retained for financial auditability)
- **Optimistic concurrency:** Not required — append-only
- **Indexing:** `idx_credit_transactions_user_id`, `idx_credit_transactions_created_at`
- **PII:** `user_id` is a PII reference; `reason` may reference extraction context

---

### Open Questions

- [ ] GDPR: should credit transaction user_id be nulled on user deletion, or retained? (Financial record vs. privacy) — Assigned to: Architect
