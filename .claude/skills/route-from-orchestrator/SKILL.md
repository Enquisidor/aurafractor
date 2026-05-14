---
description: Pre-flight gate invoked by the orchestrator at the start of every incoming message. Determines whether the message is pure pipeline coordination (handle directly) or anything else (delegate immediately). The default is delegation — ORCHESTRATION is the narrow exception.
user-invocable: false
allowed-tools: Read, Agent
---

# Route from Orchestrator — Pre-flight Gate

This skill is the orchestrator's first action on every incoming message. Its default answer is **delegate**. The only messages the orchestrator handles directly are those requiring nothing but pipeline mechanics — no domain knowledge, no reading files for content, no forming opinions about what the project should do.

**The test for ORCHESTRATION is strict:** could this be answered correctly by someone who knows nothing about the application, its code, its spec, or its domain — only about the pipeline's current state? If yes, ORCHESTRATION. If no, DOMAIN.

---

## ORCHESTRATION — the narrow exception

Handle directly only if the message requires nothing beyond pipeline state:

- "What phase are we in?" / "What's the session status?"
- "Has Gate 2 been approved?"
- "Proceed to the next phase" / "Start the pipeline"
- "Show me the activity log" / "What agents have run?"
- Questions about how the orchestration *process* works (sequencing, gates, what happens next in the pipeline)

**These look like orchestration but are not — delegate them:**

| Looks like orchestration | Why it's domain |
|---|---|
| "Read this file and tell me what it does" | Understanding code is the Backend/Frontend engineer's job |
| "Does this implementation look right?" | Evaluating code correctness requires domain expertise |
| "Is this spec complete?" | Assessing spec quality is the Architect's job |
| "Does this test cover the scenario?" | Test coverage judgment belongs to the QA Strategist or Test Engineer |
| "What do you think about this approach?" | Technical opinions belong to the relevant domain agent |
| "Summarize what the backend agent produced" | If it requires interpreting domain content, delegate |
| "Is this a good architecture?" | Architecture assessment is the Architect's job |
| Any question whose answer requires reading and reasoning about code, specs, tests, or infrastructure | Delegate |

When in doubt, delegate. The cost of an unnecessary delegation is one agent invocation. The cost of the orchestrator reasoning about domain content is a worse answer delivered by the wrong entity.

---

## DOMAIN — the default

Anything that requires domain knowledge, domain judgment, or reading any project artifact to form an opinion. This includes:

| Domain request type | Correct agent |
|---|---|
| Write, generate, scaffold, implement any code | Backend Engineer, Frontend Engineer, or DevOps |
| Fix a bug, resolve a test failure, debug a crash | The implementation agent that owns the failing code |
| Read and interpret code, explain what code does | Backend Engineer or Frontend Engineer based on the code |
| Write, revise, or improve tests | Test Engineer |
| Write Gherkin, acceptance criteria, user stories | PO Agent |
| Design architecture, define data model, design API | Architect |
| Assess whether a spec is complete or correct | Architect |
| Write or review spec files, domain model, glossary | Architect |
| Define or assess a test strategy, test coverage | QA Strategist |
| Write or review infrastructure code, CI/CD config | DevOps Engineer |
| Any security, accessibility, or code quality question | Respective reviewer agent |

**The phrasing does not matter.** "Can you glance at this file?" is a domain request if answering it requires reading and reasoning about project content.

---

## Protocol

### If ORCHESTRATION

Return:
```
ROUTING: ORCHESTRATION
Proceed normally.
```

### If DOMAIN

1. **Identify the correct agent** from the table above.

2. **Load the assembled persona** from `../.claude/agents/assembled/<pipeline>/<role>.md`. If the file doesn't exist, stop: "The [agent] persona file is missing. Run the assembler first."

3. **Construct the context payload**: the incoming message verbatim, plus any relevant artifact paths already present in the session — by reference, not embedded.

4. **Invoke the agent** using the `Agent` tool with the assembled persona as the system prompt, the context payload as the user message, and `run_in_background: true` so the user can observe the agent's work.

5. **Return the agent's response** attributed by role:
   > **[Agent role]:** [response]

   Do not paraphrase or editorialize.

### If genuinely ambiguous

Return one short clarifying question. Do not attempt any domain reasoning while waiting for the answer.

---

## Hard stop: do not reason about domain content to classify it

If you find yourself reading a file, evaluating code, or forming an opinion about project content *in order to decide whether to delegate* — stop. That reasoning is itself domain work. Classify based on the structure of the request, not by engaging with the content. When the content is what determines the answer, delegate.
