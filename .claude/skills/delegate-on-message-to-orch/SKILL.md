---
description: Delegate any mid-pipeline message — an agent output, a surfaced error, a blocker, a domain question that emerged during execution — to the correct domain agent. Invoked by the orchestrator during active pipeline phases when something arises that needs a domain expert, not when routing an initial user request (that is route-from-orchestrator's job).
user-invocable: false
allowed-tools: Read, Agent
---

# Delegate on Message

This skill is the orchestrator's mid-pipeline delegator. It handles domain content that surfaces *during* pipeline execution: an agent's output triggers a follow-up, an error needs routing to the right fixer, a blocker requires a domain decision, or a question emerges from an artifact being reviewed.

It is not invoked on initial user messages — `route-from-orchestrator` handles those before the orchestrator processes anything.

---

## When to use this skill

Use this skill when, during an active pipeline phase, the orchestrator encounters any of the following:

- An agent output contains a domain question the orchestrator cannot answer (architecture, code, product, testing)
- A gate failure or test failure needs to be routed to the responsible implementation agent
- A spec conflict, ambiguity, or gap surfaces and needs an architect's decision
- A domain question arrives mid-pipeline from the human (after `route-from-orchestrator` has already passed control back to the orchestrator)
- An agent returns `Status: Blocked` and the block is a domain question, not a pipeline process question

**Do not use this skill for:**
- Initial user messages (those go through `route-from-orchestrator`)
- Pipeline coordination decisions (phase sequencing, gate evaluation, session state) — handle those directly
- Questions about how the orchestration process itself works — answer those directly

---

## Routing table

| Content type | Correct agent | Persona path |
|---|---|---|
| Architecture, system design, technical trade-offs, spec gaps | Architect | `../.claude/agents/assembled/feature/architect.md` |
| Product requirements, scope, acceptance criteria, user story questions | PO Agent | `../.claude/agents/assembled/feature/po.md` |
| Testing strategy, coverage gaps, test plan questions | QA Strategist | `../.claude/agents/assembled/feature/qa.md` |
| Test failures, broken tests, test infrastructure issues | Test Engineer | `../.claude/agents/assembled/feature/test.md` |
| Backend code, APIs, database, server-side errors or questions | Backend Engineer | `../.claude/agents/assembled/feature/backend.md` |
| Frontend code, UI behavior, component errors or questions | Frontend Engineer | `../.claude/agents/assembled/feature/frontend.md` |
| Infrastructure, deployment, CI/CD errors or questions | DevOps Engineer | `../.claude/agents/assembled/feature/devops.md` |
| Security findings, vulnerabilities identified mid-pipeline | Security Reviewer | `../.claude/agents/assembled/review/security.md` |
| Code quality issues identified mid-pipeline | Code Quality Reviewer | `../.claude/agents/assembled/review/code-quality.md` |
| Architectural drift identified mid-pipeline | Architectural Consistency Reviewer | `../.claude/agents/assembled/review/architectural-consistency.md` |

If the content clearly spans two agents, delegate to both in parallel and synthesize their responses.

---

## Protocol

1. **Identify the content.** Determine what the message or signal contains — an error, a question, a finding, a blocker — and which agent owns that domain.

2. **Choose the agent** from the routing table. If ambiguous, prefer the more specific agent.

3. **Load the persona.** Read the assembled persona file from the path in the routing table. If the file does not exist, stop and tell the human: "The [agent] persona file is missing. Run the assembler first."

4. **Construct the context payload.** Include:
   - The specific content to delegate (verbatim error output, exact question, finding text)
   - The current pipeline phase and what the agent was doing when this surfaced
   - Relevant artifact paths (spec sections, failing test file, issue being worked) — by reference, not embedded, unless the agent must read it to respond

5. **Invoke the agent** using the `Agent` tool with the assembled persona as the system prompt, the context payload as the user message, and `run_in_background: true` so the user can observe the agent's work.

6. **Return the response** attributed by role:
   > **[Agent role]:** [response]

   Do not paraphrase or editorialize. Return the full response — the orchestrator will decide next steps based on it.
