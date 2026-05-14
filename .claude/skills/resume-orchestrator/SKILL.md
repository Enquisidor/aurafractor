---
description: Translates an orchestrator stale re-invocation message into a SendMessage command targeting the original running orchestrator. Invoke when the orchestrator reports it was re-invoked fresh into a live session and tells the user to use SendMessage.
user-invocable: true
allowed-tools: Read, SendMessage
---

# Resume Orchestrator

When the orchestrator detects it was re-invoked as a fresh agent into a live session, it halts and asks the user to send the message to the original agent via `SendMessage`. This skill does that — it finds the original orchestrator's agent ID and delivers the pending message to it.

---

## Protocol

1. **Identify the message to deliver.** This is whatever the user was trying to send when the stale re-invocation occurred — the message that triggered the startup check. Ask the user to confirm: "What message should I forward to the running orchestrator? (e.g. 'Gate 1 approved, proceed')"

2. **Locate the original orchestrator agent ID.** Look back through the current conversation history for the most recent subagent spawn that used the orchestrator persona. Its agent ID will appear in the conversation as the background agent that was started. If the ID is visible, use it directly.

   If the ID cannot be determined from the conversation history, read `.scratch/session-state.yml` — the orchestrator writes its session ID there at startup. Tell the user: "I found session ID `[id]` in session state, but I need the agent's runtime ID from the conversation history to send a message to it. Look for the background agent card in your conversation that shows the orchestrator running — its ID should be visible there."

3. **Send the message.** Use `SendMessage` with:
   - `to`: the orchestrator agent's ID
   - `message`: the user's pending message

4. **Confirm.** Tell the user:
   > Message forwarded to the running orchestrator (agent `[ID]`). It will continue from where it left off.
