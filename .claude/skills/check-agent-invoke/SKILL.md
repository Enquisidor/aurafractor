---
description: Pre-invocation guard called by the orchestrator before every Agent tool call. Checks session state for duplicate or already-running instances of the requested agent and blocks the invocation until the orchestrator confirms. Returns CLEAR to proceed or DUPLICATE with a description of the conflict.
user-invocable: false
allowed-tools: Read
---

# Check Agent Invoke

This skill runs before every `Agent` tool call. It prevents the same agent from being spawned twice for the same task, and prevents phases from being re-run when they are already complete or in progress.

---

## Protocol

1. **Read `.scratch/session-state.yml`.** If the file does not exist, return `CLEAR` — this is a fresh session with no history.

2. **Check for a currently running instance.** Look at `active_tasks`. If any entry matches the requested agent role AND the same issue or phase:

   Return:
   ```
   DUPLICATE: already running
   Agent: [role]
   Task: [task_id] — started [timestamp]
   Issue/Phase: [issue ID or phase name]
   ```
   Stop. The orchestrator must not invoke the agent until this is resolved.

3. **Check for already-completed work.** Depending on the agent type:

   - **PO Agent** — check `current_phase > 1` and `artifacts.feature_files` is populated
   - **Architect** — check `current_phase > 2` and `artifacts.spec_files` is populated
   - **QA Strategist** — check `current_phase > 3` and `artifacts.test_plans` is populated
   - **Test Engineer (phase 1)** — check `artifacts.phase1_report` is not null
   - **Test Engineer (phase 2)** — check `artifacts.phase2_report` is not null
   - **Implementation agents (Backend / Frontend / DevOps)** — check `artifacts.issues` for the specific issue: if `status: completed`, that issue is done
   - **Review agents** — check `current_phase > 6` or whether a review log entry for this agent already exists in `.logs/activity.md`

   If the check indicates the work is already complete, return:
   ```
   DUPLICATE: already completed
   Agent: [role]
   Issue/Phase: [issue ID or phase name]
   Artifact: [the file that already exists]
   ```
   Stop. The orchestrator must not invoke the agent until this is resolved.

4. **If no conflict found**, return:
   ```
   CLEAR
   ```
   The orchestrator may proceed with the invocation.

---

## Orchestrator response to DUPLICATE

When this skill returns DUPLICATE, the orchestrator must surface it to the human before doing anything:

> **Duplicate agent detected:** [role] has already [started / completed] [task/phase].
> - [If already running]: The agent is still active. Use `/resume-agents` to send it a message, or wait for it to complete.
> - [If already completed]: The work is done. Did you mean to re-run it? Reply "yes, re-run" to confirm, or "no" to cancel.

Do not invoke the agent. Wait for the human's explicit confirmation before proceeding.
