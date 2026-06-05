from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceWorkerTypeDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class ResourceCategoryDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class ResourceEmployeeOptionDescriptor:
    value: str
    label: str
    name: str
    title: str
    contact: str
    context: str
    is_active: bool


__all__ = [
    "ResourceCategoryDescriptor",
    "ResourceEmployeeOptionDescriptor",
    "ResourceWorkerTypeDescriptor",
]
