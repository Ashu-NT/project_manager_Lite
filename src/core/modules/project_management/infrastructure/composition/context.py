"""Explicit repository ownership at the PM composition boundary."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.infrastructure.composition.dependencies.repositories import (
    ProjectManagementRepositories,
)
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
)


@dataclass(frozen=True)
class ProjectManagementRepositoryContext:
    pm: ProjectManagementRepositories
    platform: PlatformRepositories
