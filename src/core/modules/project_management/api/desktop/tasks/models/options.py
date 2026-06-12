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


__all__ = [
    "TaskDependencyTypeDescriptor",
    "TaskProjectOptionDescriptor",
    "TaskProjectResourceOptionDescriptor",
    "TaskStatusDescriptor",
]
