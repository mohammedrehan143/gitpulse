"""GitPulse Git Integration Tools."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


class GitTools:
    """Tooling interface for git inspections and version control operations."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = Path(workspace_root or ".").resolve()

    def _run_git(self, args: List[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git"] + args,
            cwd=str(self.workspace_root),
            capture_output=True,
            text=True,
            check=False,
        )

    def get_status(self) -> Dict[str, Any]:
        """Returns untracked, modified, and staged files."""
        res = self._run_git(["status", "--porcelain"])
        if res.returncode != 0:
            return {"is_git": False, "error": res.stderr}

        modified = []
        untracked = []
        staged = []

        for line in res.stdout.splitlines():
            if not line:
                continue
            status = line[:2]
            filename = line[3:].strip()
            if status == "??":
                untracked.append(filename)
            elif status[0] in ("M", "A", "D"):
                staged.append(filename)
            elif status[1] in ("M", "D"):
                modified.append(filename)

        return {
            "is_git": True,
            "is_clean": len(modified) == 0 and len(staged) == 0 and len(untracked) == 0,
            "modified": modified,
            "untracked": untracked,
            "staged": staged,
        }

    def get_diff(self, staged: bool = False) -> str:
        """Returns the current git diff."""
        args = ["diff", "--cached"] if staged else ["diff"]
        res = self._run_git(args)
        return res.stdout

    def get_current_branch(self) -> str:
        """Returns the name of the current active branch."""
        res = self._run_git(["branch", "--show-current"])
        return res.stdout.strip() or "main"
