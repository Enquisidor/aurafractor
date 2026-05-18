---
description: Resumes a running background agent by delivering a message to it via SendMessage. Use when an agent was re-invoked fresh via the Agent tool instead of being continued — the fresh agent will have halted and told the user to use SendMessage to the original. Also use any time a message needs to be forwarded to a specific running agent by name or role.
user-invocable: true
allowed-tools: Read, SendMessage
---

# Resume Agents

The `Agent` tool always starts a fresh agent with no prior context. When a running agent is accidentally re-invoked this way, it detects the mismatch and halts. This skill delivers the intended message to the correct running agent via `SendMessage`.

It also handles the general case: any time you need to send a message to a specific running background agent by name or role.

> **Prerequisite:** `SendMessage` requires the environment variable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` to be set. If the tool is not available, tell the user to set that variable and restart their Claude Code session.

---

## Protocol

1. **Identify the target agent.** Determine which agent to resume:
   - If a stale re-invocation message is visible in the conversation (e.g., the orchestrator halted and said "use SendMessage to the original agent"), the target is the most recently spawned background agent matching that role.
   - If invoked with an explicit agent name or role (e.g., "resume the architect"), use that.
   - If unclear, ask: "Which agent do you want to resume? (e.g. orchestrator, architect, backend engineer)"

2. **Find the agent's runtime ID.** Look back through the conversation history for the background agent card matching the target role. The runtime ID is displayed when a background agent is started. Use the most recent one for the target role.

   If the ID cannot be determined from conversation history, check `.scratch/session-state.yml` for any agent IDs recorded there. If still not found, tell the user: "I can't find the runtime ID for the [role] agent in the conversation history. Look for the background agent panel in your Claude Code session — the ID should be visible there." Ask them to provide it.

3. **Identify the message to deliver.** This is whatever message the user intended to send to the agent:
   - If a stale re-invocation occurred, it's the message that triggered the fresh startup.
   - If invoked explicitly, ask: "What message should I send to the [role] agent?"

4. **Send via `SendMessage`.** Deliver the message to the agent's runtime ID.

5. **Confirm:**
   > Message delivered to the running [role] agent (ID: `[id]`). It will continue from where it left off.
