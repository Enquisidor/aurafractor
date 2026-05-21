#!/usr/bin/env python3
"""
SessionStart hook — injects session state and recent log tails as startup context.

Fires once when a Claude Code session starts (or resumes after compaction).
Reads .scratch/session-state.yml and recent .logs/ tails; outputs additionalContext
so every agent begins with the current pipeline state without needing to read files
manually.

Gracefully exits 0 with no output when the files do not exist (new project, first run).
"""

import json
import sys
import pathlib


MAX_CHARS = 2000  # max chars to inject per log file (tail)


def tail(path: pathlib.Path, max_chars: int) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return None
    if len(text) <= max_chars:
        return text
    # Snap to a line boundary so we don't cut mid-entry
    truncated = text[-max_chars:]
    newline = truncated.find("\n")
    return "…(truncated)\n" + (truncated[newline + 1:] if newline != -1 else truncated)


def main() -> None:
    data = json.load(sys.stdin)
    cwd = pathlib.Path(data.get("cwd", "."))

    parts: list[str] = []

    # Session state — full file (small, structured)
    state_file = cwd / ".scratch" / "session-state.yml"
    if state_file.exists():
        content = state_file.read_text(encoding="utf-8").strip()
        if content:
            parts.append(
                "**Current session state** (`.scratch/session-state.yml`):\n"
                f"```yaml\n{content}\n```"
            )

    # Activity log tail
    activity = tail(cwd / ".logs" / "activity.md", MAX_CHARS)
    if activity:
        parts.append(f"**Recent activity** (`.logs/activity.md` tail):\n{activity}")

    # Decisions log tail (shorter — just enough to surface recent choices)
    decisions = tail(cwd / ".logs" / "decisions.md", MAX_CHARS // 2)
    if decisions:
        parts.append(f"**Recent decisions** (`.logs/decisions.md` tail):\n{decisions}")

    if parts:
        context = "## Startup Orientation\n\n" + "\n\n".join(parts)
        print(json.dumps({"additionalContext": context}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never crash the session over a hook failure
        sys.exit(0)
