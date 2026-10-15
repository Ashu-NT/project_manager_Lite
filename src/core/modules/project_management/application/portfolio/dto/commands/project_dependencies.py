from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.domain.enums import DependencyType


@dataclass(frozen=True)
class PortfolioDependencyCreateCommand:
    predecessor_project_id: str
    successor_project_id: str
    dependency_type: str = DependencyType.FINISH_TO_START.value
    summary: str = ""


@dataclass(frozen=True)
class PortfolioDependencyRemoveCommand:
    dependency_id: str
