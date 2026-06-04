from dataclasses import dataclass
from src.core.modules.project_management.domain.enums import DependencyType


@dataclass(frozen=True)
class SchedulingDependencyTypeDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class SchedulingProjectDependencyDto:
    id: str
    predecessor_task_id: str
    predecessor_task_name: str
    successor_task_id: str
    successor_task_name: str
    dependency_type: str
    dependency_type_label: str
    lag_days: int


@dataclass(frozen=True)
class SchedulingDependencyDto:
    id: str
    direction: str
    direction_label: str
    related_activity_id: str
    related_activity_name: str
    dependency_type: str
    dependency_type_label: str
    lag_days: int
    relationship_label: str
    status_label: str


__all__ = [
    "SchedulingDependencyDto",
    "SchedulingDependencyTypeDescriptor",
    "SchedulingProjectDependencyDto",
]
