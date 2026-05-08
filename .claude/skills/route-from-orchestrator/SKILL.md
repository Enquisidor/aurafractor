---
description: Pre-flight gate invoked by the orchestrator at the start of every incoming message. Classifies the request as orchestration work (proceed) or domain work (delegate immediately). Prevents the orchestrator from responding to domain requests directly, regardless of how the request is phrased.
user-invocable: false
allowed-tools: Read, Agent
---

# Route from Orchestrator — Pre-flight Gate

This skill is the orchestrator's first action on every incoming message. It exists because domain requests are often phrased as direct asks ("write X", "fix Y", "design Z") rather than explicit delegation requests ("have an agent write X"). This skill catches both forms and enforces delegation unconditionally.

---

## Classification

Read the incoming message and classify it into exactly one of these categories:

### ORCHESTRATION — proceed normally

The message asks the orchestrator to coordinate, not to produce domain artifacts:
- Session status, phase status, gate status, session state questions
- Explicit pipeline instructions: "start the pipeline", "proceed to Phase 3", "re-run the test engineer"
- Gate evaluation: reviewing an artifact a human submitted, deciding whether to approve
- Handoff management, blocker escalation, context construction
- Questions about how the orchestration process works
- Acknowledging an agent's output and deciding the next step

### DOMAIN — delegate immediately

The message asks for domain artifacts or domain decisions — anything that would require generating content that belongs to a specific agent's role. This includes any phrasing:

| Domain request type | Correct agent |
|---|---|
| Write, generate, scaffold, create, implement any code (any language, any layer) | Backend Engineer, Frontend Engineer, or DevOps — based on what's being built |
| Fix a bug, resolve a test failure, debug a crash | The implementation agent that owns the failing code |
| Write, revise, or improve tests | Test Engineer |
| Write Gherkin, acceptance criteria, user stories, feature descriptions | PO Agent |
| Design architecture, define data model, design API, choose technical approach | Architect |
| Write spec files, domain model, bounded context definitions, glossary | Architect |
| Define a test strategy, coverage requirements, test plan | QA Strategist |
| Write infrastructure code, CI/CD pipelines, deployment config | DevOps Engineer |
| Answer a question about code, architecture, security, testing, UX | Use `delegate-question-or-task` |

**The phrasing does not matter.** "Can you write a login endpoint?" and "Write a login endpoint" and "We need a login endpoint" are all domain requests and all require delegation.

### AMBIGUOUS — clarify before proceeding

The message could be read as either orchestration or domain work. Return a clarifying question before doing anything.

---

## Protocol

### If ORCHESTRATION

Return:
```
ROUTING: ORCHESTRATION
Proceed normally.
```

The orchestrator handles the message as it normally would.

### If DOMAIN

1. **Identify the correct agent** from the classification table above.

2. **Load the assembled persona** for that agent from `../.claude/agents/assembled/<pipeline>/<role>.md`. If the file doesn't exist, stop and tell the human: "The [agent] persona file is missing. Run the assembler first: `python3 /path/to/library/build/assemble.py --config .agents/config.yml`"

3. **Construct the context payload**: the incoming message verbatim, plus any relevant context already present in the session (spec paths, current issue, relevant artifact paths — by reference, not by embedding content).

4. **Invoke the agent** using the `Agent` tool with the assembled persona as the system prompt, the context payload as the user message, and `run_in_background: true` so the user can observe the agent's work.

5. **Return the agent's response**, attributed by role:
   > **[Agent role]:** [response]

   Do not paraphrase, editorialize, or add commentary. The human asked a domain question; return the domain expert's answer.

### If AMBIGUOUS

Return one short clarifying question. Do not attempt any domain work or orchestration until the question is answered.

---

## What this skill is not

This skill does not replace `delegate-question-or-task`. That skill handles ongoing mid-session domain questions during normal orchestration flow. This skill is the mandatory first-pass gate that fires before the orchestrator processes any message at all — including messages that arrive during active pipeline phases.
