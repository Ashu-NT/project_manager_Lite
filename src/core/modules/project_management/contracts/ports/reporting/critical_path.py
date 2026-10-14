from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.application.scheduling.models.cpm import (
    CPMTaskInfo,
)


class CriticalPathReport(Protocol):
    def get_critical_path(self, project_id: str) -> list[CPMTaskInfo]: ...


__all__ = ["CriticalPathReport"]
