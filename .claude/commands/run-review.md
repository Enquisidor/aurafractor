Run the review pipeline on the current branch's changes.

## Step 1 — Choose agents

Read `.agents/config.yml` and list all review agents that are enabled. Present the list and ask:

> Which review agents would you like to run?
> Enabled: `[list from config]`
> Reply "all" to run all of them, or name specific ones.

Wait for the user's reply before continuing.

## Step 2 — Choose execution order

Ask:

> Run them in **parallel** (faster, results interleaved) or **sequential** (slower, one at a time, easier to follow)?
> `[ parallel / sequential ]`

Wait for the user's reply before continuing.

## Step 3 — Confirm assembled personas

For each selected agent, check that `../.claude/agents/assembled/review/<agent>.md` exists. Warn about any that are missing — the user must run the assembler before those agents can run.

## Step 4 — Determine changed files

Run: `git diff --name-only $(git merge-base HEAD main)..HEAD`

## Step 5 — Run agents

For each selected agent, invoke it using the `Agent` tool with:
- `subagent_type` set to the agent's name (e.g. `security-reviewer`, `code-quality-reviewer`, `accessibility-reviewer`, `architectural-consistency-reviewer`, `cicd-reviewer`, `document-consistency-reviewer`, `po-signoff`)
- `prompt` containing only the files relevant to its concern (see each persona's Inputs section for scoping rules) and instruction to append findings to `.logs/issues.md` and end with its standard verdict block
- `run_in_background: true`

Claude Code loads the agent's system prompt automatically from its assembled persona. Do not read persona files or pass them as a system prompt.

Run in the order chosen in Step 2: all at once if parallel, one at a time if sequential.

## Step 6 — Summarize

After all selected agents complete, read `.logs/issues.md` and collect the verdict blocks.

Report:
- Each agent's verdict (PASS / PASS-WITH-FINDINGS / FAIL) and finding counts
- Overall result: FAIL if any agent returned FAIL, PASS-WITH-FINDINGS if any P2/P3 exist, PASS otherwise
- List all P0 and P1 issue IDs if any exist
