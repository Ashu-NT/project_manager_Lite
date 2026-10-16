from dataclasses import dataclass


@dataclass(frozen=True)
class SchedulingDependencyTypeDescriptor:
    value: str
    label: str


__all__ = [
    "SchedulingDependencyTypeDescriptor",
]
