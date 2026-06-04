"""Type coercion helpers for import row parsing."""

from __future__ import annotations

from datetime import date

from src.core.modules.project_management.domain.enums import CostType, ProjectStatus, TaskStatus


def required(row: dict[str, str], key: str) -> str:
    value = (row.get(key) or "").strip()
    if not value:
        raise ValueError(f"Missing required column '{key}'.")
    return value


def optional_date(value: str | None) -> date | None:
    text = str(value or "").strip()
    return date.fromisoformat(text) if text else None


def optional_int(value: str | None) -> int | None:
    text = str(value or "").strip()
    return int(text) if text else None


def optional_float(value: str | None) -> float | None:
    text = str(value or "").strip()
    return float(text) if text else None


def optional_bool(value: str | None, *, default: bool) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return default
    return text in {"1", "true", "yes", "y", "on"}


def optional_project_status(value: str | None) -> ProjectStatus | None:
    text = str(value or "").strip().upper()
    return ProjectStatus(text) if text else None


def optional_task_status(value: str | None) -> TaskStatus | None:
    text = str(value or "").strip().upper()
    return TaskStatus(text) if text else None


def optional_cost_type(value: str | None) -> CostType | None:
    text = str(value or "").strip().upper()
    return CostType(text) if text else None


__all__ = [
    "optional_bool",
    "optional_cost_type",
    "optional_date",
    "optional_float",
    "optional_int",
    "optional_project_status",
    "optional_task_status",
    "required",
]
