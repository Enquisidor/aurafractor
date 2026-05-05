---
description: Delegate a question or task to the most relevant domain expert agent rather than answering or solving it directly. Invoked by the orchestrator whenever the human asks a question or points out a task related to architecture, product, code, testing, security, infrastructure, or any other domain that belongs to a specific agent.
user-invocable: false
allowed-tools: Read Write, Agent
---

## When to use this skill

Use this skill whenever the human asks a question or points to a task during an orchestration session. The orchestrator is a coordinator, not a domain expert — delegate to the agent that holds the relevant expertise.

**Answer directly (do not invoke this skill) only when** the question or issue is about pipeline state, session status, gate status, or how the orchestration process itself works.

## Routing table

| Question/Task type | Agent | Persona path |
|---|---|---|
| Architecture, system design, technical trade-offs | Architect | `../.claude/agents/assembled/feature/architect.md` |
| Product requirements, scope, user stories, acceptance criteria | PO Agent | `../.claude/agents/assembled/feature/po.md` |
| Testing strategy, test coverage, QA approach | QA Strategist | `../.claude/agents/assembled/feature/qa.md` |
| Backend code, APIs, database, server-side behavior | Backend Engineer | `../.claude/agents/assembled/feature/backend.md` |
| Frontend code, UI behavior, component structure | Frontend Engineer | `../.claude/agents/assembled/feature/frontend.md` |
| Infrastructure, deployment, CI/CD | DevOps Engineer | `../.claude/agents/assembled/feature/devops.md` |
| Security risks, vulnerabilities, threat model | Security Reviewer | `../.claude/agents/assembled/review/security.md` |
| Code quality, patterns, refactoring | Code Quality Reviewer | `../.claude/agents/assembled/review/code-quality.md` |
| Accessibility | Accessibility Reviewer | `../.claude/agents/assembled/review/accessibility.md` |
| Architectural consistency across the codebase | Architectural Consistency Reviewer | `../.claude/agents/assembled/review/architectural-consistency.md` |

If the question clearly spans two agents, delegate to both and synthesize their responses.

## Protocol

1. **Choose the agent.** Using the routing table above, identify the single best agent for the question. If ambiguous, prefer the more specific agent over the more general one.

2. **Load the persona.** Read the assembled persona file from the path in the routing table. If the file does not exist, tell the human which persona is missing and instruct them to run the assembler.

3. **Construct the context payload.** Build a focused user message containing:
   - The human's question verbatim
   - Any directly relevant artifacts already loaded in the session (spec file paths, a code snippet, the issue being discussed) — reference by path rather than embedding full content unless the agent must read it to answer

4. **Invoke the agent.** Use the `Agent` tool with the assembled persona as the system prompt and the context payload as the user message.

5. **Return the response.** Present the agent's answer attributed by role:
   > **Architect:** [response]

   Do not paraphrase or editorialize. If the agent's response is long, present it in full — the human asked a question and deserves the complete answer.
