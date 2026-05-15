---
description: Startup orientation skill. Invoked at the beginning of every agent session to read prior activity, session state, and decisions relevant to the current task. Prevents agents from re-doing completed work or re-investigating resolved issues.
user-invocable: false
allowed-tools: Read, Glob
---

# Read Session Logs — Startup Orientation

Invoke this skill once, at the very start of your session, before doing any work. Its purpose is to orient you: what has already happened, what has been decided, and whether you have worked on this task before in a prior invocation.

Do not invoke it again mid-task. It is a startup check, not a progress tracker.

---

## Protocol

### Step 1 — Read session state

Read `.scratch/session-state.yml`. Extract:
- Current phase
- Which gates have been approved
- Which issues are in-progress or completed
- Your own prior entries in `active_tasks` (if any — this means you've been invoked before for this task)

If the file does not exist, note "new session" and proceed.

### Step 2 — Scan the activity log for your own prior work

Read `.logs/activity.md`. **Scan only — do not ingest the full file.** Look for entries where `Agent:` matches your role. For each matching entry:
- Note the task ID and status
- If status is `Completed` for the same task you are about to work on: you have already done this work. Stop and report to the orchestrator before proceeding.
- If status is `Blocked`: extract what was blocking so you don't hit the same wall again.

Ignore all entries from other agents.

### Step 3 — Scan the decisions log for relevant decisions

Read `.logs/decisions.md` if it exists. **Scan decision titles only.** Read the full body only for decisions that directly relate to the component or area you are about to work on. Note any decisions that constrain your approach.

### Step 4 — Read your scratch state

Read `.scratch/<your-agent-name>.yml` if it exists. This is your own prior state from earlier in this session — tasks attempted, notes left for yourself, blockers encountered.

### Step 5 — Report and proceed

Output a brief orientation summary (3–5 lines):
- Prior work found for this task: [yes — task ID and status / none]
- Relevant decisions: [list titles, or "none"]
- Blockers to be aware of: [list, or "none"]
- Starting from: [fresh / resuming prior work]

Then proceed with your task.

---

## Rules

- Invoke once at startup. Do not re-invoke mid-task.
- Scan before ingesting. Never read entire log files in full — extract only what pertains to your task.
- If you find your own completed entry for the same task, **stop and surface it to the orchestrator** rather than re-doing the work.
