---
description: Append a structured finding to .logs/issues.md. Invoke whenever you have identified a problem that needs tracking — a review finding, a spec inconsistency, a test failure requiring attention, or any issue that must be visible to the team.
user-invocable: false
allowed-tools: Read Write
---

## Protocol

1. **Read `.logs/issues.md`** to find the highest existing issue ID. Issue IDs follow the pattern `ISSUE-NNN` (zero-padded to three digits). If the file does not exist, create it with this header:
   ```
   # Issue Log
   ```

2. **Assign the next sequential ID.** If the highest existing ID is `ISSUE-014`, assign `ISSUE-015`. If the file is empty or newly created, start at `ISSUE-001`.

3. **Read `logs/issue-log-format.md`** to confirm the current required fields and structure before writing.

4. **Append the entry.** Write the complete issue entry. Do not truncate any field. Every required field in the format must be present — do not omit fields because they seem obvious or redundant.

5. **Return the assigned issue ID** to the calling context so it can be referenced in verdict messages and handoff summaries.

## Rules

- Never modify or delete existing entries.
- Never renumber existing entries.
- If `.logs/` does not exist, create the directory before writing.
- If you are logging multiple findings in one session, assign IDs sequentially in the order findings are logged — do not batch them.
