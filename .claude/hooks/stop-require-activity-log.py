#!/usr/bin/env python3
"""
Stop hook — blocks the agent from stopping until it has written an activity log entry.

Fires each time the agent tries to stop. Scans the session transcript for a Write or
Edit call whose file_path includes "activity.md". If none is found AND a pipeline
session is active (.scratch/session-state.yml exists), exits 2 with a reminder.
The agent then writes its activity log and tries to stop again; this hook passes.

The stop_hook_active flag is checked to prevent infinite blocking if the agent
cannot produce the entry (e.g., it is running outside the pipeline context).
"""

import json
import sys
import pathlib


def transcript_has_activity_write(transcript_path: str) -> bool:
    """Return True if any Write/Edit in the transcript targeted activity.md."""
    path = pathlib.Path(transcript_path)
    if not path.exists():
        return False

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            entry = json.loads(raw_line)
        except json.JSONDecodeError:
            continue

        # Tool uses are inside message.content as a list of typed items
        msg = entry.get("message", {})
        content = msg.get("content") or []
        if not isinstance(content, list):
            continue

        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "tool_use":
                continue
            if item.get("name") not in ("Write", "Edit"):
                continue
            file_path = (item.get("input") or {}).get("file_path", "")
            if "activity.md" in file_path:
                return True

    return False


def pipeline_session_active(cwd: pathlib.Path) -> bool:
    """Return True only when there is an active pipeline session to log against."""
    return (cwd / ".scratch" / "session-state.yml").exists()


def main() -> None:
    data = json.load(sys.stdin)

    # If the hook has already blocked multiple times this stop cycle, let it through
    # to avoid an infinite loop when the agent genuinely cannot write the entry.
    if data.get("stop_hook_active", False):
        return

    cwd = pathlib.Path(data.get("cwd", "."))

    # Only enforce inside an active pipeline session
    if not pipeline_session_active(cwd):
        return

    transcript_path = data.get("transcript_path", "")
    if transcript_has_activity_write(transcript_path):
        return  # Entry found — allow stop

    # No entry found — block and remind
    print(json.dumps({
        "additionalContext": (
            "Activity log entry not written yet. "
            "Before stopping, append an entry to `.logs/activity.md` "
            "following the log-activity protocol in your instructions. "
            "Include task status, inputs, outputs, decisions, and issues."
        )
    }))
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never block a stop over a hook failure — fail open
        sys.exit(0)
