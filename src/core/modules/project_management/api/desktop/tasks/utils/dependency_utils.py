from __future__ import annotations

from src.core.modules.project_management.domain.enums import DependencyType


def coerce_dependency_type(value: str | DependencyType | None) -> DependencyType:
    if isinstance(value, DependencyType):
        return value
    normalized_value = str(value or DependencyType.FINISH_TO_START.value).strip().upper()
    try:
        return DependencyType(normalized_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported dependency type: {normalized_value}.") from exc


def coerce_dependency_direction(value: str | None) -> str:
    normalized_value = str(value or "predecessor").strip().upper()
    if normalized_value in {"PREDECESSOR", "CURRENT_DEPENDS_ON_OTHER"}:
        return "PREDECESSOR"
    if normalized_value in {"SUCCESSOR", "OTHER_DEPENDS_ON_CURRENT"}:
        return "SUCCESSOR"
    raise ValueError(f"Unsupported dependency direction: {normalized_value}.")


def dependency_direction(current_task_id: str, dependency) -> tuple[str, str]:
    if current_task_id == dependency.successor_task_id:
        return ("PREDECESSOR", dependency.predecessor_task_id)
    if current_task_id == dependency.predecessor_task_id:
        return ("SUCCESSOR", dependency.successor_task_id)
    return ("", dependency.successor_task_id)


def dependency_type_label(value: DependencyType | str) -> str:
    dependency_type = coerce_dependency_type(value)
    labels = {
        DependencyType.FINISH_TO_START: "Finish -> Start",
        DependencyType.FINISH_TO_FINISH: "Finish -> Finish",
        DependencyType.START_TO_START: "Start -> Start",
        DependencyType.START_TO_FINISH: "Start -> Finish",
    }
    return labels[dependency_type]


__all__ = [
    "coerce_dependency_direction",
    "coerce_dependency_type",
    "dependency_direction",
    "dependency_type_label",
]
