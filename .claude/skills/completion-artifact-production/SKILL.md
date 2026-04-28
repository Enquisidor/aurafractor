---
description: Produce and write a structured completion artifact when an implementation agent (Backend Engineer, Frontend Engineer, IaC/DevOps Engineer) finishes an issue. The artifact is written to .handoffs/ so the orchestrator and Test Engineer can consume it for phase-2 verification.
user-invocable: false
allowed-tools: Read Write
---

## Protocol

1. **Determine the output path:** `.handoffs/<agent-role>-completion-<issue-id>.md`
   - Examples: `.handoffs/backend-completion-ISS-007.md`, `.handoffs/frontend-completion-ISS-012.md`
   - Use kebab-case for agent role names.
   - If a file at that path already exists, read it before overwriting — confirm you are replacing a prior incomplete attempt, not a separate agent's artifact.

2. **Read `logs/activity-log-format.md`** and check whether the activity log entry has already been written. The completion artifact and the activity log entry are separate outputs — one does not replace the other.

3. **Collect the required fields.** Core fields required for all implementation agents:
   - **Issue ID and title** — the exact issue identifier from `.spec/issues/`
   - **Agent** — the agent role name
   - **Timestamp** — ISO 8601 UTC
   - **Files created or modified** — one entry per file with its path and a one-line description of the change
   - **Implementation summary** — 2–4 sentences: what was built and how it satisfies the acceptance criteria
   - **Deviations from spec** — any decision made that deviated from the Architect's spec, with the DEC-NNN reference for each. Write "None" if there were no deviations.
   - **Test suite result** — the exact command run, pass count, fail count, and the full error output for any failures

4. **Add agent-specific fields:**

   **Backend Engineer additionally includes:**
   - Any new dependencies added (library name, version, purpose)

   **Frontend Engineer additionally includes:**
   - Design gaps encountered and how each was resolved (or "None")

   **IaC/DevOps Engineer additionally includes:**
   - Environments affected (dev / staging / production)
   - Secrets required before first apply: name, purpose, and provisioning instructions for each (or "None")
   - Rollback procedure summary
   - Any sizing or configuration decisions proposed for tech lead review (or "None")
   - Self-check status for each module applied

5. **Write the artifact** to the determined path. End the file with:
   ```
   Status: READY FOR PHASE-2 VERIFICATION
   ```
   If there are unresolved spec deviations awaiting tech lead review, end with:
   ```
   Status: AWAITING TECH LEAD REVIEW — do not proceed to phase-2 until resolved
   ```

6. **Report the artifact path** to the orchestrator or calling context.

## Rules

- The completion artifact is not a substitute for the activity log entry. Both must be written.
- Do not write a completion artifact until all self-check modules have been applied. Record self-check status in the activity log entry, not here.
- Test suite results must be exact — do not paraphrase error output. If the full error output is very long, include the first and last 10 lines of each failure.
- If `.handoffs/` does not exist, create the directory before writing.
