from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegisterProjectOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class RegisterEntryTypeDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class RegisterEntryStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class RegisterEntrySeverityDescriptor:
    value: str
    label: str


__all__ = [
    "RegisterEntrySeverityDescriptor",
    "RegisterEntryStatusDescriptor",
    "RegisterEntryTypeDescriptor",
    "RegisterProjectOptionDescriptor",
]
