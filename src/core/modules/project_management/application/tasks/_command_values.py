"""Normalize task command values at the application boundary."""

from src.core.modules.project_management.domain.enums import (
    ConstraintType,
    DependencyType,
    TaskStatus,
)


def task_status(value: str | None) -> TaskStatus:
    if isinstance(value, TaskStatus):
        return value
    normalized = str(value or TaskStatus.TODO.value).strip().upper()
    try:
        return TaskStatus(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported task status: {normalized}.") from exc


def constraint_type(value: str | None) -> ConstraintType | None:
    if value is None or value == "":
        return None
    if isinstance(value, ConstraintType):
        return value
    return ConstraintType(str(value).strip())


def dependency_type(value: str | None) -> DependencyType:
    if isinstance(value, DependencyType):
        return value
    normalized = str(value or DependencyType.FINISH_TO_START.value).strip().upper()
    try:
        return DependencyType(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported dependency type: {normalized}.") from exc


def dependency_direction(value: str | None) -> str:
    normalized = str(value or "PREDECESSOR").strip().upper()
    if normalized not in {"PREDECESSOR", "SUCCESSOR"}:
        raise ValueError(f"Unsupported dependency direction: {normalized}.")
    return normalized
