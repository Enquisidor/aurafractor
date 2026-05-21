Resume a running background agent by delivering a message to it via SendMessage. Use when an agent was re-invoked fresh via the Agent tool instead of being continued — the fresh agent will have halted and told you to use this command. Also use any time you need to forward a message to a specific running agent by name or role.

> **Prerequisite:** `SendMessage` requires the environment variable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` to be set. If the tool is not available, ask the user to set that variable and restart their Claude Code session.

---

## Protocol

1. **Identify the target agent.** Determine which agent to resume:
   - If a stale re-invocation message is visible in the conversation (e.g., the orchestrator halted and said "use SendMessage to the original agent"), the target is the most recently spawned background agent matching that role.
   - If invoked with an explicit agent name or role (e.g., "/resume-agents architect"), use that.
   - If unclear, ask: "Which agent do you want to resume? (e.g. orchestrator, architect, backend engineer)"

2. **Find the agent's runtime ID.** Look back through the conversation history for the background agent card matching the target role. The runtime ID is displayed when a background agent is started. Use the most recent one for the target role.

   If the ID cannot be determined from conversation history, check `.scratch/session-state.yml` for any agent IDs recorded there. If still not found, tell the user: "I can't find the runtime ID for the [role] agent in the conversation history. Look for the background agent panel in your Claude Code session — the ID should be visible there." Ask them to provide it.

3. **Identify the message to deliver.** This is whatever message the user intended to send to the agent:
   - If a stale re-invocation occurred, it's the message that triggered the fresh startup.
   - If invoked explicitly, ask: "What message should I send to the [role] agent?"

4. **Send via `SendMessage`.** Deliver the message to the agent's runtime ID.

5. **Confirm:**
   > Message delivered to the running [role] agent (ID: `[id]`). It will continue from where it left off.
