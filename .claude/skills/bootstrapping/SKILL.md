---
name: bootstrapping
description: Day-zero project setup workflow. Run once at project start to produce spec artifacts, assembled personas, and a failing test skeleton. Completes Phases 1–4 of the orchestrator's TDD/BDD pipeline so the orchestrator can enter at Phase 5 (Implementation).
user-invocable: false
allowed-tools: Read
---

# Bootstrapping Workflow (Day Zero)

Run this workflow once at project start. It produces the spec artifacts, assembled personas, and failing test skeleton that the TDD/BDD development sequence requires as inputs.

**Prerequisite:** The configurator must run before this workflow begins. The configurator produces `.agents/config.yml`, `../.claude/agents/assembled/`, and pre-populated `.spec/` stubs. This workflow builds on those outputs — it does not replace them. If the configurator has not run yet, start there.

After this workflow completes, the project enters the TDD/BDD sequence at **Phase 5 (Implementation)** with all upstream prerequisites in place.

---

## Overview

| Step | Who | Output | Gate |
|---|---|---|---|
| Pre | Configurator | `../.claude/agents/`, `.spec/` stubs | Configurator complete |
| 1 | PM (human) | `.handoffs/requirements-brief.md` | PM confirms brief is complete |
| 2 | PO Agent *(optional)* | `.features/*.feature` | PM approves feature files |
| 3 | Architect | `.spec/` filled in + approval summary | **Tech Lead approval — hard gate** |
| 4 | QA Strategist | `.test-plans/` | Optional PM spot-check |
| 5 | Test Engineer | Failing test suite | All new tests must fail |

---

## Step 1: Requirements intake

**Who:** PM (human)

Consolidate all available requirements into a structured brief. This is the Architect's primary input — it must be complete enough to model the domain. Gaps here propagate to every downstream artifact.

**Output: `.handoffs/requirements-brief.md`** containing:
- Core user stories or feature descriptions (numbered, not prose)
- Known constraints: technical (stack, integrations, platform limits), business (regulatory, SLA, compliance), financial
- Non-functional requirements with specific measurable targets: "p95 response time under 200ms", "99.9% monthly uptime"
- Scope flags: which review pipeline dimensions are active, whether auto-fix is permitted
- Technology choices already made, if any

**Gate:** PM confirms the brief is complete enough to model the domain before proceeding.

---

## Step 2: Gherkin authoring *(optional)*

**Who:** PO Agent — or skip this step

This step is optional. Whether to include it depends on what requirements exist going in:

| Situation | Action |
|---|---|
| Client has provided Gherkin `.feature` files | Place them in `.features/` and skip to Step 3 |
| PM has user stories but no formal acceptance criteria | Run PO Agent — it converts stories to Gherkin |
| No product-layer specifications exist yet | Skip — QA Strategist derives test coverage from API contracts and domain model in Step 4 |

**Input:** `.handoffs/requirements-brief.md` + any existing user stories or product documents

**Output:** `.features/<feature-area>.feature` files covering the first milestone's scope

**Gate:** PM reviews and approves feature files. Feature files must represent what was actually specified — not invented scope.

---

## Step 3: Domain modeling

**Who:** Architect agent

**Input:**
- `.handoffs/requirements-brief.md`
- `.features/` (if produced in Step 2 or provided by the client)
- `.spec/` stubs pre-populated by the configurator — start here, do not start from blank templates

**Task:** The configurator has already created the structure. The Architect's job is to make the decisions that fill it in:

- **`.spec/domain-model.md`** — bounded context map, aggregate definitions, entity relationships, invariants, domain events, context integration patterns
- **`.spec/glossary.md`** — every domain term with a precise, implementation-authoritative definition
- **`.spec/schema.md`** — database schema with column types, constraints, indexes, PII column annotations
- **`.spec/api-contracts.md`** — every endpoint for the first milestone: path, method, full request/response schema, all status codes, auth requirements, pagination contracts
- **`.spec/issues/`** — one file per independently deployable unit of work for the first milestone, with implementation guidance and acceptance criteria the Test Engineer can derive assertions from

Also produce **`.handoffs/architect-approval-summary.md`**: a summary of the key decisions made, trade-offs considered, open questions for the tech lead, and any significant deviations from what the requirements brief implied.

**Gate: HUMAN — Tech Lead reviews and approves all `.spec/` artifacts.** This is the highest-stakes gate in the bootstrapping workflow. The domain model and API contracts are the foundation everything else builds on — errors here multiply through every downstream agent's output.

- On approval: update `.scratch/session-state.yml`, proceed to Step 4
- On rejection: Architect revises. Multiple rounds are expected and normal. Each round produces an updated approval summary documenting what changed and why.

---

## Step 4: Test plan

**Who:** QA Strategist agent

**Input:** Approved `.spec/` artifacts + `.features/` (if available)

**Task:** Produce test plans in `.test-plans/` for the first milestone. Coverage must include:
- All Gherkin scenarios (if feature files exist): happy paths, user flows, business rules
- All API contracts for the first milestone: every endpoint's error conditions, validation rules, auth requirements, and pagination behavior
- Boundary conditions for every field with a defined constraint

When no feature files exist, derive all test cases from the API contracts and domain model invariants. Coverage is still required — the absence of Gherkin is not a reason to produce fewer test cases.

**Output:** `.test-plans/<feature-area>.md` per feature area

**Gate:** Automated format validation. The PM may optionally request to review the test plan before implementation begins — recommended for the first milestone of a new project.

---

## Step 5: Skeleton tests

**Who:** Test Engineer agent (Phase 1)

**Input:** `.test-plans/` files + `.spec/api-contracts.md`

**Task:** Write skeleton test files in the project's test directory. Every test case in every test plan maps to a test stub. Run the full suite immediately after writing.

**Gate: All new tests must fail.** A new test that passes before implementation means either the test doesn't actually assert anything, or test code has leaked from a previous project. Either is a blocker — do not proceed. Escalate to the orchestrator with the specific test IDs and failure output.

**Output:** `.test-reports/phase1-<timestamp>.md` — each test listed with its failure reason, confirming the failure is a correct assertion failure (not a setup error or import failure).

---

## End state

After Step 5, the project is ready for the TDD/BDD development sequence:

```
../.claude/agents/assembled/     — all agent personas ready
.spec/                 — complete, tech-lead-approved spec artifacts
.features/             — Gherkin feature files (if applicable)
.test-plans/           — full coverage test plans
.test-reports/         — phase-1 report confirming all tests fail
```

Hand off to the orchestrator. Begin at **Phase 5 (Implementation)** — Phases 1 through 4 are already complete.

---

## Re-running for subsequent milestones

Use the `milestone-kickoff` workflow instead. Do not re-run this workflow for features added to a project that already has a populated `.spec/` directory and a test suite — that is scope creep into existing project state, not a fresh bootstrap.
