from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskProjectOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class TaskStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class TaskProjectResourceOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class TaskDependencyTypeDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class TaskConstraintOptionDescriptor:
    """One entry in the Task editor's "Scheduling constraint" picker --
    ``value`` is "" for ASAP (see constraint_presentation.py's
    value=None -> ""), otherwise the real ConstraintType string."""

    value: str
    code: str
    label: str
    description: str
    requires_date: bool
    category: str


__all__ = [
    "TaskConstraintOptionDescriptor",
    "TaskDependencyTypeDescriptor",
    "TaskProjectOptionDescriptor",
    "TaskProjectResourceOptionDescriptor",
    "TaskStatusDescriptor",
]
