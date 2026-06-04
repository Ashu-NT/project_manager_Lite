"""Dependency coercion and direction helpers."""

from src.core.modules.project_management.domain.enums import DependencyType


def coerce_dependency_type(value) -> DependencyType:
    if isinstance(value, DependencyType):
        return value
    normalized = str(value or DependencyType.FINISH_TO_START.value).strip().upper()
    try:
        return DependencyType(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported dependency type: {normalized}.") from exc


def coerce_dependency_direction(value: str | None) -> str:
    normalized = str(value or "PREDECESSOR").strip().upper()
    if normalized in {"PREDECESSOR", "SUCCESSOR"}:
        return normalized
    raise ValueError(f"Unsupported dependency direction: {normalized}.")


def dependency_direction(current_task_id: str, dependency) -> tuple[str, str]:
    if dependency.successor_task_id == current_task_id:
        return "PREDECESSOR", dependency.predecessor_task_id
    if dependency.predecessor_task_id == current_task_id:
        return "SUCCESSOR", dependency.successor_task_id
    return "", ""


__all__ = ["coerce_dependency_direction", "coerce_dependency_type", "dependency_direction"]
