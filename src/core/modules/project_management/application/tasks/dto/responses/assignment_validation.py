"""Neutral assignment validation and preview outcomes."""

from dataclasses import dataclass

from src.core.modules.project_management.application.resources.capacity.task_assignment_capacity_service import (
    TaskAssignmentCapacityFact,
)


@dataclass(frozen=True)
class AssignmentValidationResponseDto:
    task_id: str
    resource_id: str
    is_valid: bool
    can_assign: bool
    requires_approval: bool
    is_blocked: bool
    has_warnings: bool
    violation_messages: tuple[str, ...]
    warning_messages: tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class AssignmentPreviewResponseDto:
    task_id: str
    resource_id: str
    overallocation_pct: float
    conflict_project_ids: tuple[str, ...]
    skills_matched: bool
    certs_valid: bool
    has_warnings: bool
    warning_messages: tuple[str, ...]
    is_blocked: bool
    block_messages: tuple[str, ...]
    capacity: TaskAssignmentCapacityFact | None = None
