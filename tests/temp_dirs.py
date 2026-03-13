from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from tests.path_rewrites import REPO_ROOT


TEST_TEMP_ROOT = REPO_ROOT / ".pytest_workspaces"


def create_test_workspace(prefix: str) -> Path:
    workspace = TEST_TEMP_ROOT / prefix / uuid4().hex
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def cleanup_test_workspace(workspace: Path) -> None:
    shutil.rmtree(workspace, ignore_errors=True)
    for candidate in (workspace.parent, TEST_TEMP_ROOT):
        try:
            candidate.rmdir()
        except OSError:
            pass


__all__ = ["TEST_TEMP_ROOT", "cleanup_test_workspace", "create_test_workspace"]
