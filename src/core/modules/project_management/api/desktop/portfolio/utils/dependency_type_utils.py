"""Dependency type coercion and label utilities."""

from __future__ import annotations
from src.core.modules.project_management.domain.enums import DependencyType

_DEPENDENCY_TYPE_LABELS = {
    DependencyType.FINISH_TO_START: "Finish -> Start",
    DependencyType.FINISH_TO_FINISH: "Finish -> Finish",
    DependencyType.START_TO_START: "Start -> Start",
    DependencyType.START_TO_FINISH: "Start -> Finish",
}


def coerce_dependency_type(value: str | DependencyType | None) -> DependencyType:
    if isinstance(value, DependencyType):
        return value
    normalized = str(value or DependencyType.FINISH_TO_START.value).strip().upper()
    try:
        return DependencyType(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported portfolio dependency type: {normalized}.") from exc


def dependency_type_label(dependency_type: DependencyType) -> str:
    return _DEPENDENCY_TYPE_LABELS.get(dependency_type, dependency_type.value)


__all__ = ["coerce_dependency_type", "dependency_type_label"]
