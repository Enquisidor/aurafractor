#!/usr/bin/env python3
"""
PreToolUse hook for the Agent tool — blocks duplicate agent invocations.

Fires before every Agent tool call. Reads .scratch/session-state.yml and checks:
  1. active_tasks — if the target agent role is already running, block.
  2. artifacts.issues — if the target issue is already completed, block.

Exits 0 (allow) when session-state.yml does not exist, cannot be parsed,
or no conflict is found. Exits 2 (block) and writes the reason to stderr
when a duplicate is detected.

Requires PyYAML. If unavailable, exits 0 (fails open — never crash the pipeline).
"""

import json
import sys
import pathlib

try:
    import yaml
except ImportError:
    sys.exit(0)


def normalise(s: str) -> str:
    return (s or "").strip().lower()


def roles_overlap(a: str, b: str) -> bool:
    """True if two role strings refer to the same agent (prefix or exact match)."""
    a, b = normalise(a), normalise(b)
    if not a or not b:
        return False
    return a == b or a.startswith(b) or b.startswith(a)


def main() -> None:
    data = json.load(sys.stdin)
    cwd = pathlib.Path(data.get("cwd", "."))
    tool_input = data.get("tool_input", {})

    subagent_type = normalise(tool_input.get("subagent_type", ""))
    description = normalise(tool_input.get("description", ""))
    prompt = normalise(tool_input.get("prompt", ""))

    state_file = cwd / ".scratch" / "session-state.yml"
    if not state_file.exists():
        return

    try:
        state = yaml.safe_load(state_file.read_text(encoding="utf-8"))
    except Exception:
        return

    if not state:
        return

    # ── 1. Check active_tasks (already running) ──────────────────────────────
    for task in state.get("active_tasks") or []:
        agent = normalise(task.get("agent", ""))
        if not agent:
            continue

        if roles_overlap(agent, subagent_type) or (description and agent in description):
            task_id = task.get("task_id", "unknown")
            issue = task.get("issue", "")
            started = task.get("started", "")

            reason = f"Duplicate agent invocation blocked: '{agent}' is already running"
            if task_id != "unknown":
                reason += f" (task {task_id}"
                if issue:
                    reason += f", issue {issue}"
                if started:
                    reason += f", started {started}"
                reason += ")"
            reason += ". Use /resume-agents to deliver a message to it instead."

            sys.stderr.write(reason + "\n")
            sys.exit(2)

    # ── 2. Check artifacts.issues (already completed) ────────────────────────
    for issue_entry in (state.get("artifacts") or {}).get("issues") or []:
        issue_id = normalise(issue_entry.get("id", ""))
        status = normalise(issue_entry.get("status", ""))
        assigned_to = normalise(issue_entry.get("assigned_to", ""))

        if status != "completed" or not issue_id:
            continue

        # Only flag if this invocation appears to target this specific issue
        targets_issue = issue_id in prompt or issue_id in description
        if not targets_issue:
            continue

        # And the agent role matches (or we have no agent info to check against)
        agent_matches = (
            not assigned_to
            or roles_overlap(assigned_to, subagent_type)
            or (description and assigned_to in description)
        )
        if not agent_matches:
            continue

        artifact_file = issue_entry.get("file", "")
        reason = (
            f"Duplicate invocation blocked: issue {issue_entry.get('id')} "
            f"is already completed"
        )
        if artifact_file:
            reason += f" (see {artifact_file})"
        reason += ". Reply 'yes, re-run [issue ID]' to confirm re-running, or cancel."

        sys.stderr.write(reason + "\n")
        sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never crash the pipeline over a hook failure — fail open
        sys.exit(0)
