---
name: milestone-kickoff
description: Workflow for adding a new milestone to an existing project that already has a populated spec directory, assembled agents, and a running test suite. Use instead of bootstrapping for all milestones after the first.
user-invocable: false
allowed-tools: Read
---

# Milestone Kickoff Workflow

Use this workflow when adding a new milestone to an existing project that already has a populated `.spec/` directory, assembled agents, and a running test suite. Do not re-run the `bootstrapping` workflow — that is for day-zero only and would overwrite existing spec artifacts.

---

## When to use this workflow

- The project has shipped at least one milestone and you are beginning the next
- `.spec/` exists and is populated from a previous Architect run
- `../.claude/agents/assembled/` exists from a previous configurator run
- An existing test suite is in place (Phase 2 tests pass for the prior milestone)

---

## Steps

### Step 1: Requirements brief for the new milestone

**Who:** PM (human)

Write a new requirements brief scoped to the new milestone. Include:
- New user stories or features being added
- Any changes to existing behavior
- New non-functional requirements or updated targets
- Any new technology choices or integrations

**Output:** `.handoffs/requirements-brief-<milestone>.md`

---

### Step 2: Gherkin authoring *(optional — same rules as bootstrapping)*

**Who:** PO Agent, or skip

Same decision as bootstrapping Step 2: include if converting user stories to Gherkin; skip if the client has provided feature files or if coverage will come from contracts alone.

New `.feature` files go in `.features/`. Do not modify existing feature files unless the milestone explicitly changes prior behavior — modified scenarios require the Test Engineer to update the corresponding tests.

---

### Step 3: Architect updates `.spec/`

**Who:** Architect agent

The Architect **updates** existing `.spec/` artifacts — it does not replace them. Key constraints:

- **Glossary is extended, not replaced.** New terms are added. Existing terms may be refined but must not be renamed without explicit tech lead acknowledgment that this is a breaking change to existing implementation.
- **New aggregates** are added to the domain model. Existing aggregate definitions may only be modified if the change is backward-compatible, or if a migration path for existing data is specified.
- **Existing API contracts are not changed** without explicit flagging. A modification to an existing contract is a breaking change — it must be called out in the approval summary and reviewed separately from additive changes.
- **New `.spec/issues/`** are created for the new milestone's implementation scope.

**Output:** Updated `.spec/` artifacts + `.handoffs/architect-approval-summary-<milestone>.md`

**Gate:** Tech Lead reviews and approves. Breaking changes to existing contracts or aggregates receive explicit acknowledgment.

---

### Step 4: QA Strategist extends test plans

**Who:** QA Strategist agent

The QA Strategist **extends** `.test-plans/` for the new milestone's scope. Existing test plan files are not modified unless existing behavior is changing. New test case IDs continue the sequence from the highest existing ID.

---

### Step 5: Test Engineer adds skeleton tests

**Who:** Test Engineer agent (Phase 1)

The Test Engineer adds new test stubs for the new milestone's test cases. Existing tests are not deleted, skipped, or modified. Run the full suite: existing tests must still pass; new tests must fail.

A regression in an existing test at this stage — before any new implementation — is a blocker. It indicates a test authoring error or an accidental change to shared test infrastructure.

---

## End state

Same as bootstrapping: ready for the `tdd-bdd-sequence` workflow at Phase 5 (Implementation), with prior milestone tests still passing and new milestone tests failing.
