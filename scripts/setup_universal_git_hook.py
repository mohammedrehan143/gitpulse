"""Universal Git Hook Installer for GitPulse.

Configures a global Git hook on your system so that ANY repository you push or commit to
automatically dispatches an engineering activity alert to your Discord channel via GitPulse.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main():
    print("=" * 65)
    print("  GitPulse Universal Git Push & Commit Notification Setup")
    print("=" * 65)

    home_dir = Path.home()
    global_hooks_dir = home_dir / ".gitpulse_global_hooks"
    global_hooks_dir.mkdir(parents=True, exist_ok=True)

    gitpulse_root = Path(__file__).resolve().parent.parent
    notif_script = (
        gitpulse_root / "backend" / "src" / "gitpulse" / "services" / "notification_service.py"
    )

    python_executable = sys.executable

    # Create post-commit hook script
    post_commit_script = global_hooks_dir / "post-commit"
    hook_content = f"""#!/usr/bin/env bash
# GitPulse Universal Activity Hook

REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [ -n "$REMOTE_URL" ]; then
    # Extract owner/repo from remote URL
    REPO_NAME=$(echo "$REMOTE_URL" | sed -E 's/.*github\\.com[:\\/](.*)\\.git/\\1/' | sed -E 's/.*github\\.com[:\\/](.*)/\\1/')
else
    REPO_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
PUSHER=$(git config user.name || echo "developer")
SHA=$(git rev-parse HEAD 2>/dev/null || echo "head")
MSG=$(git log -1 --pretty=%B 2>/dev/null | head -n 1 || echo "Commit update")

# Call GitPulse universal notification engine
"{python_executable}" "{notif_script}" \\
    --repo "$REPO_NAME" \\
    --pusher "$PUSHER" \\
    --branch "$BRANCH" \\
    --message "$MSG" \\
    --sha "$SHA" > /dev/null 2>&1 || true
"""

    post_commit_script.write_text(hook_content, encoding="utf-8")

    # Set executable permissions on Unix systems
    try:
        os.chmod(post_commit_script, 0o755)
    except Exception:
        pass

    # Configure Git global hooksPath
    hook_path_str = str(global_hooks_dir).replace("\\", "/")
    cmd = ["git", "config", "--global", "core.hooksPath", hook_path_str]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode == 0:
        print(f"\n[SUCCESS] Universal hook installed to: {hook_path_str}")
        print("[SUCCESS] Configured: git config --global core.hooksPath")
        print("\nFrom now on, whenever you commit or push in ANY repository on this machine,")
        print("GitPulse will automatically send an automated alert to your Discord channel!\n")
    else:
        print(f"\n[ERROR] Failed to configure git global hooksPath: {res.stderr}")


if __name__ == "__main__":
    main()
