## Bounded Context: Credits

**Purpose:** Responsible for managing each user's credit balance, enforcing balance invariants, computing extraction costs, and maintaining an immutable transaction ledger.

**Owner:** Architect owns all contexts.

---

### Responsibility Boundary

**This context owns:**
- Credit balance (current balance, monthly allowance, reset date)
- Credit deduction and refund operations
- Credit cost computation (single-source: 5, multi-source: 10, re-extraction: 20, ambiguity surcharge: +1/label)
- Immutable credit transaction log
- Monthly reset logic (allowance replenishment per tier)

**This context explicitly does not own:**
- Subscription tier definition — belongs to Identity (Credits reads it, does not own it)
- Extraction job lifecycle — belongs to Extraction
- Payment processing — not in scope

---

### Core Model

**Aggregate roots:**
- [CreditAccount](../aggregates/CreditAccount.md): a user's credit balance with its invariants and monthly allowance; the only place credits are debited or credited
- [CreditTransaction](../aggregates/CreditTransaction.md): an immutable ledger entry recording a single debit or credit event

**Value objects (context-level):**
- `CreditAmount`: non-negative integer; credits are whole units only
- `CreditReason`: description string explaining the transaction (e.g., "single-source extraction", "re-extraction", "monthly reset")

**Domain events produced:**
- `CreditDebited`: triggered when credits are deducted; payload: user_id, amount, balance_after, extraction_id; scope: Internal
- `CreditRefunded`: triggered when credits are returned (e.g., failed extraction); payload: user_id, amount, balance_after, extraction_id; scope: Internal
- `MonthlyAllowanceReset`: triggered on monthly reset; payload: user_id, new_balance, subscription_tier; scope: Internal

**Domain events consumed:**
- `UserRegistered` from Identity: initialize CreditAccount with tier's monthly allowance
- `ExtractionQueued` from Extraction: debit credits for the extraction cost
- `ExtractionFailed` from Extraction: refund credits for the failed job

---

### Context Map

| Adjacent Context | Relationship Type | Integration Mechanism | Notes |
|---|---|---|---|
| Identity | Conformist | sync — user_id FK; reads subscription_tier | Credits adopts Identity's tier model to determine allowance |
| Extraction | Customer–Supplier | sync REST call | Extraction calls Credits to debit; Credits enforces the balance invariant |

---

### Ubiquitous Language (context-specific terms)

| Term | Definition within this context | Anti-patterns (do not use) |
|---|---|---|
| CreditAccount | The authoritative record of a user's current credit balance and monthly allowance | "wallet", "balance row" |
| CreditTransaction | An immutable ledger entry recording one debit or credit event with before/after balances | "transaction log", "history entry" |
| Monthly Allowance | The number of credits replenished at each reset date, determined by subscription tier | "quota", "limit" |
| Debit | A reduction in credit balance in exchange for an extraction job | "charge", "spend", "use" |

---

### Open Questions

- [ ] Should partial failures (one stem fails in a multi-source extraction) trigger partial refunds? — Assigned to: Architect
