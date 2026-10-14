"""Reproducibility helpers (PRD §10: every published number traceable to a SHA)."""
from __future__ import annotations

import subprocess


def current_git_sha() -> str | None:
    """Return the current git HEAD sha, or None if not in a git repo."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return out.stdout.strip() or None
    except Exception:
        return None
