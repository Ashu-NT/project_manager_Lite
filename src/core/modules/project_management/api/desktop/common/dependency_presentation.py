"""Single canonical source for Task dependency-type/direction presentation
and input coercion, shared across the Tasks, Scheduling, and Portfolio
desktop-API workspaces. See
docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
Phase M -- previously four independently-maintained copies of this same
label map and coercion logic existed and had already drifted from one
another (e.g. scheduling's copy silently dropped SF from CPM handling
until Phase C/D fixed the underlying math; the label maps themselves were
identical by luck, not by construction).
"""
from __future__ import annotations

from src.core.modules.project_management.domain.enums import DependencyType

_DEPENDENCY_TYPE_LABELS: dict[DependencyType, str] = {
    DependencyType.FINISH_TO_START: "Finish -> Start",
    DependencyType.START_TO_START: "Start -> Start",
    DependencyType.FINISH_TO_FINISH: "Finish -> Finish",
    DependencyType.START_TO_FINISH: "Start -> Finish",
}


def coerce_dependency_type(value: str | DependencyType | None) -> DependencyType:
    if isinstance(value, DependencyType):
        return value
    normalized = str(value or DependencyType.FINISH_TO_START.value).strip().upper()
    try:
        return DependencyType(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported dependency type: {normalized}.") from exc


def dependency_type_label(value: DependencyType | str) -> str:
    dependency_type = coerce_dependency_type(value)
    return _DEPENDENCY_TYPE_LABELS[dependency_type]


def coerce_dependency_direction(value: str | None) -> str:
    normalized = str(value or "PREDECESSOR").strip().upper()
    if normalized in {"PREDECESSOR", "SUCCESSOR"}:
        return normalized
    raise ValueError(f"Unsupported dependency direction: {normalized}.")


def dependency_direction(current_task_id: str, dependency) -> tuple[str, str]:
    if current_task_id == dependency.successor_task_id:
        return ("PREDECESSOR", dependency.predecessor_task_id)
    if current_task_id == dependency.predecessor_task_id:
        return ("SUCCESSOR", dependency.successor_task_id)
    return ("", "")


__all__ = [
    "coerce_dependency_direction",
    "coerce_dependency_type",
    "dependency_direction",
    "dependency_type_label",
]
