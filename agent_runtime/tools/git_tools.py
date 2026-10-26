"""GitPulse Git Integration Tools."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class GitTools:
    """Tooling interface for git inspections and version control operations."""

    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = Path(workspace_root or ".").resolve()

    def _run_git(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git"] + args,
            cwd=str(self.workspace_root),
            capture_output=True,
            text=True,
            check=False,
        )

    def get_status(self) -> dict[str, Any]:
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

    def commit(self, message: str, stage_all: bool = False) -> dict[str, Any]:
        """Commits changes with well-designed output formatting."""
        if stage_all:
            self._run_git(["add", "-A"])

        res = self._run_git(["commit", "-m", message])
        if res.returncode != 0:
            err = res.stderr.strip() or res.stdout.strip()
            return {
                "success": False,
                "error": err,
                "output": f"❌ [GitPulse] Commit failed: {err}",
            }

        sha_res = self._run_git(["rev-parse", "--short", "HEAD"])
        sha = sha_res.stdout.strip() if sha_res.returncode == 0 else "head"
        formatted_output = f"✨ [GitPulse] New git committed: \"{message}\" (SHA: {sha})"
        return {
            "success": True,
            "sha": sha,
            "message": message,
            "output": formatted_output,
            "raw": res.stdout.strip(),
        }

    def push(self, remote: str = "origin", branch: str | None = None) -> dict[str, Any]:
        """Pushes branch commits to remote repository with well-designed output."""
        target_branch = branch or self.get_current_branch()
        res = self._run_git(["push", remote, target_branch])
        if res.returncode != 0:
            err = res.stderr.strip() or res.stdout.strip()
            return {
                "success": False,
                "error": err,
                "output": f"❌ [GitPulse] Push failed: {err}",
            }

        formatted_output = f"🚀 [GitPulse] New git pushed: successfully pushed to {remote}/{target_branch}!"
        return {
            "success": True,
            "remote": remote,
            "branch": target_branch,
            "output": formatted_output,
            "raw": res.stdout.strip() or res.stderr.strip(),
        }

    def pull(self, remote: str = "origin", branch: str | None = None) -> dict[str, Any]:
        """Pulls latest updates from remote repository with well-designed output."""
        target_branch = branch or self.get_current_branch()
        res = self._run_git(["pull", remote, target_branch])
        if res.returncode != 0:
            err = res.stderr.strip() or res.stdout.strip()
            return {
                "success": False,
                "error": err,
                "output": f"❌ [GitPulse] Pull failed: {err}",
            }

        formatted_output = f"📥 [GitPulse] New git pulled: successfully pulled updates from {remote}/{target_branch}!"
        return {
            "success": True,
            "remote": remote,
            "branch": target_branch,
            "output": formatted_output,
            "raw": res.stdout.strip(),
        }
