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

For each selected agent, spawn it as a sub-agent with:
- Its assembled persona from `../.claude/agents/assembled/review/<agent>.md` as the system prompt
- Only the files relevant to its concern (see each persona's Inputs section for scoping rules)
- Instruction to append findings to `.logs/issues.md` and end with its standard verdict block

Run in the order chosen in Step 2: all at once if parallel, one at a time if sequential.

## Step 6 — Summarize

After all selected agents complete, read `.logs/issues.md` and collect the verdict blocks.

Report:
- Each agent's verdict (PASS / PASS-WITH-FINDINGS / FAIL) and finding counts
- Overall result: FAIL if any agent returned FAIL, PASS-WITH-FINDINGS if any P2/P3 exist, PASS otherwise
- List all P0 and P1 issue IDs if any exist
