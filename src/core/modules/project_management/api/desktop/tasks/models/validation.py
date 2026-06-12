from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AssignmentValidationDesktopDto:
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
class AssignmentPreviewDesktopDto:
    task_id: str
    resource_id: str
    overallocation_pct: float
    conflict_projects: tuple[str, ...]
    skills_matched: bool
    certs_valid: bool
    has_warnings: bool
    warning_messages: tuple[str, ...]
    is_blocked: bool
    block_messages: tuple[str, ...]


__all__ = ["AssignmentPreviewDesktopDto", "AssignmentValidationDesktopDto"]
