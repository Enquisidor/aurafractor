---
description: Check prior session history, issue log, and decisions log before diagnosing or fixing a bug. Prevents re-investigating known problems and repeating failed approaches. Invoke at the start of any bug fix or pipeline investigation task.
user-invocable: false
allowed-tools: Read, Glob
---

# Check Prior Issues — Pre-flight for Bug Fixes

Before spending time diagnosing a problem, check whether it has already been seen and solved (or attempted) in this session.

## Protocol

### Step 1 — Check the issue log

Read `.logs/issues.md`. Search for entries related to the current problem by keyword (error message, file name, component name). If a matching entry exists:

- Note the issue ID (ISS-NNN), its status, and what was tried
- If status is `resolved`: the fix is documented — apply it directly rather than re-investigating
- If status is `open` or `attempted`: read the full entry to understand what was already tried and ruled out before forming a new hypothesis

### Step 2 — Check the session scratch state

Read `.scratch/session-state.yml` and any relevant agent scratch file (e.g. `.scratch/orchestrator.yml`, `.scratch/devops.yml`). Look for:

- Prior task entries for this problem (`notes` fields often contain diagnosis details)
- Any recorded root causes, failed approaches, or known constraints

### Step 3 — Check prior decisions

Read `.logs/decisions.md`. If a decision was made about the component or area being investigated (e.g. "chose explicit prisma generate over postinstall hook"), respect that decision — don't re-introduce the rejected approach.

### Step 4 — Report before proceeding

Before starting diagnosis, briefly state:

- What prior context was found (issue IDs, session notes)
- What approaches are already ruled out
- What your starting hypothesis is, informed by the prior context

If no prior context exists, state that and proceed with fresh investigation.

## Why this matters

Recurring errors are often the same root cause surfacing in a new job or context. Re-investigating from scratch wastes time and risks repeating the same failed approaches. A 30-second check of the issue log frequently surfaces the exact diagnosis needed.
