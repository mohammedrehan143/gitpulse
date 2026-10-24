"""GitPulse Permission-Aware Filesystem Tools."""

from __future__ import annotations

from pathlib import Path

from agent_runtime.shared.permissions import PermissionManager


class FilesystemTools:
    """Tooling interface for sandboxed filesystem operations."""

    def __init__(
        self,
        workspace_root: Path | None = None,
        permission_manager: PermissionManager | None = None,
    ):
        self.workspace_root = Path(workspace_root or ".").resolve()
        self.permission_manager = permission_manager or PermissionManager(self.workspace_root)

    def read_file(self, target_path: str | Path) -> str:
        """Reads contents of a file within the workspace."""
        path = (self.workspace_root / target_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {target_path}")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def write_file(self, agent_id: str, target_path: str | Path, content: str) -> Path:
        """Writes content to file after verifying agent write authorization."""
        self.permission_manager.check_write_permission(agent_id, target_path)

        path = (self.workspace_root / target_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def list_files(self, sub_dir: str = ".", pattern: str = "*") -> list[str]:
        """Lists files matching pattern within a directory."""
        dir_path = (self.workspace_root / sub_dir).resolve()
        if not dir_path.exists():
            return []
        return [
            p.relative_to(self.workspace_root).as_posix()
            for p in dir_path.glob(pattern)
            if p.is_file()
        ]

    def file_exists(self, target_path: str | Path) -> bool:
        """Checks if a file exists relative to workspace."""
        return (self.workspace_root / target_path).exists()
