Run the milestone kickoff workflow when adding a new milestone to an existing project that already has a populated spec directory, assembled agents, and a running test suite. Use instead of `/bootstrap` for all milestones after the first.

---

## When to use this command

- The project has shipped at least one milestone and you are beginning the next
- `.spec/` exists and is populated from a previous Architect run
- `../.claude/agents/assembled/` exists from a previous configurator run
- An existing test suite is in place (Phase 2 tests pass for the prior milestone)

Do not re-run `/bootstrap` — that is for day-zero only and would overwrite existing spec artifacts.

---

## Step 1: Milestone requirements brief

**Who:** PM (human)

Write a brief scoped to this milestone's additions. This is a delta document — focus only on what is new, changed, or removed relative to the existing spec.

**Output: `.handoffs/requirements-brief-<milestone>.md`** containing:
- New user stories or changed acceptance criteria for this milestone
- API changes: new endpoints, modified contracts, deprecated endpoints
- Data model changes: new entities, schema migrations, relationship changes
- Constraints or non-functional requirements specific to this milestone

**Gate:** PM confirms the brief accurately scopes the milestone before proceeding.

---

## Step 2: Spec update

**Who:** Architect agent

**Input:**
- `.handoffs/requirements-brief-<milestone>.md`
- Existing `.spec/` artifacts (update in place — do not rewrite from scratch)
- Prior `.features/` if Gherkin is being extended

**Task:** Update the existing spec artifacts to cover the new milestone:
- Add new endpoints to `.spec/api-contracts.md`
- Add new aggregates, entities, or domain events to `.spec/domain-model.md`
- Add new terms to `.spec/glossary.md`
- Update `.spec/schema.md` with migration requirements
- Add new issue files to `.spec/issues/` for this milestone's work

Mark each changed section clearly (e.g., `<!-- milestone: <name> -->`) so reviewers know what is new.

Also produce **`.handoffs/architect-approval-summary-<milestone>.md`**: what changed, what was kept, key decisions, open questions.

**Gate: HUMAN — Tech Lead reviews and approves all spec changes.** Particular attention to: spec consistency between new and existing artifacts, migration safety, backward-compatibility of API changes.

---

## Step 3: Test plan update

**Who:** QA Strategist agent

**Input:** Updated `.spec/` artifacts + new `.features/` (if applicable)

**Task:** Produce test plans covering only the new milestone's scope. Do not rewrite existing test plans — add new files or clearly delimited sections.

**Output:** `.test-plans/<milestone>-<feature-area>.md`

---

## Step 4: Skeleton tests

**Who:** Test Engineer agent (Phase 1)

**Input:** New `.test-plans/` files + updated `.spec/api-contracts.md`

**Task:** Write skeleton test files for the new milestone. Run the full suite — both new and existing tests.

**Gate:**
- All **new** tests must fail (new functionality not yet implemented)
- All **existing** tests must still pass (no regression from spec updates)

A regression in existing tests at this stage means a spec change broke an invariant — escalate to the Architect before proceeding.

**Output:** `.test-reports/phase1-<milestone>-<timestamp>.md`

---

## End state

After Step 4, the project is ready for the development pipeline:

```
.spec/                 — updated with milestone additions, existing content intact
.test-plans/           — new test plans for this milestone
.test-reports/         — phase-1 report: new tests failing, existing tests passing
```

Same as `/bootstrap`: hand off to the orchestrator at **Phase 5 (Implementation)** with prior milestone tests still passing and new milestone tests failing.
