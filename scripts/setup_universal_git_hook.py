"""Universal Git Hook Installer for GitPulse.

Configures global Git hooks on your system so that ANY repository you push or commit to
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

    # Convert paths to forward slashes for cross-platform Git Bash compatibility
    python_posix = str(sys.executable).replace("\\", "/")
    notif_posix = str(notif_script).replace("\\", "/")
    root_posix = str(gitpulse_root).replace("\\", "/")

    # Read webhook URL from settings as fallback
    webhook_url = ""
    try:
        sys.path.insert(0, str(gitpulse_root))
        from backend.src.gitpulse.common.config import settings

        webhook_url = settings.DISCORD_WEBHOOK_URL or ""
    except Exception:
        pass

    webhook_arg = f'--webhook-url "{webhook_url}"' if webhook_url else ""

    log_file_posix = str(global_hooks_dir / "hook.log").replace("\\", "/")

    # 1. Create post-commit hook script
    post_commit_script = global_hooks_dir / "post-commit"
    post_commit_content = f"""#!/usr/bin/env bash
# GitPulse Universal Post-Commit Hook

REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [ -n "$REMOTE_URL" ]; then
    REPO_NAME=$(echo "$REMOTE_URL" | sed -E 's/.*github\\.com[:\\/](.*)\\.git/\\1/' | sed -E 's/.*github\\.com[:\\/](.*)/\\1/')
else
    REPO_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
PUSHER=$(git config user.name || echo "developer")
SHA=$(git rev-parse HEAD 2>/dev/null || echo "head")
MSG=$(git log -1 --pretty=%B 2>/dev/null | head -n 1 || echo "Commit update")

export PYTHONPATH="{root_posix}:$PYTHONPATH"
"{python_posix}" "{notif_posix}" \\
    {webhook_arg} \\
    --repo "$REPO_NAME" \\
    --pusher "$PUSHER" \\
    --branch "$BRANCH" \\
    --message "$MSG" \\
    --sha "$SHA" >> "{log_file_posix}" 2>&1 || true
"""
    post_commit_script.write_text(post_commit_content, encoding="utf-8")

    # 2. Create pre-push hook script (triggers on git push)
    pre_push_script = global_hooks_dir / "pre-push"
    pre_push_content = f"""#!/usr/bin/env bash
# GitPulse Universal Pre-Push Hook

REMOTE_NAME="$1"
REMOTE_URL="$2"

if [ -z "$REMOTE_URL" ]; then
    REMOTE_URL=$(git remote get-url "$REMOTE_NAME" 2>/dev/null || git remote get-url origin 2>/dev/null || echo "")
fi

if [ -n "$REMOTE_URL" ]; then
    REPO_NAME=$(echo "$REMOTE_URL" | sed -E 's/.*github\\.com[:\\/](.*)\\.git/\\1/' | sed -E 's/.*github\\.com[:\\/](.*)/\\1/')
else
    REPO_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
PUSHER=$(git config user.name || echo "developer")
SHA=$(git rev-parse HEAD 2>/dev/null || echo "head")
MSG=$(git log -1 --pretty=%B 2>/dev/null | head -n 1 || echo "Git push to remote")

export PYTHONPATH="{root_posix}:$PYTHONPATH"
"{python_posix}" "{notif_posix}" \\
    {webhook_arg} \\
    --repo "$REPO_NAME" \\
    --pusher "$PUSHER" \\
    --branch "$BRANCH" \\
    --message "$MSG" \\
    --sha "$SHA" >> "{log_file_posix}" 2>&1 || true

exit 0
"""
    pre_push_script.write_text(pre_push_content, encoding="utf-8")

    # Set executable permissions on Unix systems
    for script in (post_commit_script, pre_push_script):
        try:
            os.chmod(script, 0o755)
        except Exception:
            pass

    # Configure Git global hooksPath
    hook_path_str = str(global_hooks_dir).replace("\\", "/")
    cmd = ["git", "config", "--global", "core.hooksPath", hook_path_str]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode == 0:
        print(f"\n[SUCCESS] Universal hooks installed to: {hook_path_str}")
        print("  - post-commit: triggers Discord alert on every local commit")
        print("  - pre-push:    triggers Discord alert on every 'git push'")
        print("[SUCCESS] Configured: git config --global core.hooksPath")
        print("\nGitPulse is now active for EVERY repository on this machine!\n")
    else:
        print(f"\n[ERROR] Failed to configure git global hooksPath: {res.stderr}")


if __name__ == "__main__":
    main()
