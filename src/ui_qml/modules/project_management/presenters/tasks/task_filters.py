from __future__ import annotations

import re
import shlex
from datetime import date, timedelta

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskSelectorOptionViewModel,
)


_ADVANCED_TASK_QUERY_PATTERN = re.compile(
    r"^(status|priority|progress|start|end|deadline)(:|<=|>=|=|<|>)(.+)$",
    flags=re.IGNORECASE,
)


def build_task_priority_options() -> tuple[TaskSelectorOptionViewModel, ...]:
    return (
        TaskSelectorOptionViewModel(value="all", label="All priorities"),
        TaskSelectorOptionViewModel(value="high", label="High (>= 70)"),
        TaskSelectorOptionViewModel(value="medium", label="Medium (30-69)"),
        TaskSelectorOptionViewModel(value="low", label="Low (< 30)"),
    )


def build_task_schedule_options() -> tuple[TaskSelectorOptionViewModel, ...]:
    return (
        TaskSelectorOptionViewModel(value="all", label="All schedule states"),
        TaskSelectorOptionViewModel(value="overdue", label="Overdue"),
        TaskSelectorOptionViewModel(value="due_7", label="Due 7 days"),
        TaskSelectorOptionViewModel(value="no_deadline", label="No deadline"),
    )


def normalize_task_filter(
    value: str,
    options: tuple[TaskSelectorOptionViewModel, ...],
    *,
    default_value: str = "all",
) -> str:
    normalized_value = (value or default_value).strip().lower()
    available_values = {
        option.value.lower(): option.value
        for option in options
    }
    return available_values.get(normalized_value, default_value)


def matches_task_filters(
    task: object,
    *,
    search_text: str,
    status_filter: str,
    priority_filter: str,
    schedule_filter: str,
    today: date | None = None,
) -> bool:
    if not _matches_status(task, status_filter):
        return False
    if not _matches_priority(task, priority_filter):
        return False
    if not _matches_schedule(task, schedule_filter, today=today):
        return False
    return _matches_search(task, search_text)


def parse_advanced_task_query(
    query: str,
) -> tuple[list[str], list[tuple[str, str, str]]]:
    terms: list[str] = []
    structured: list[tuple[str, str, str]] = []
    for token in shlex.split(query or ""):
        match = _ADVANCED_TASK_QUERY_PATTERN.match(token)
        if match is None:
            terms.append(token.lower())
            continue
        field, operator, value = match.groups()
        structured.append((field.lower(), operator, value.strip()))
    return terms, structured


def _matches_search(task: object, search_text: str) -> bool:
    normalized_search = (search_text or "").strip()
    if not normalized_search:
        return True
    free_terms, structured_terms = parse_advanced_task_query(normalized_search)
    haystack = " ".join(
        (
            str(getattr(task, "name", "") or ""),
            str(getattr(task, "description", "") or ""),
            str(getattr(task, "project_name", "") or ""),
        )
    ).lower()
    for term in free_terms:
        if term and term not in haystack:
            return False
    for field, operator, value in structured_terms:
        if field == "status":
            actual_status = _task_status_value(task).lower()
            expected_status = value.lower()
            if operator in {":", "="} and actual_status != expected_status:
                return False
            continue
        if field in {"priority", "progress"}:
            actual_number = (
                int(getattr(task, "priority", 0) or 0)
                if field == "priority"
                else float(getattr(task, "percent_complete", 0.0) or 0.0)
            )
            try:
                expected_number = float(value)
            except ValueError:
                return False
            if not _compare_numeric(actual_number, operator, expected_number):
                return False
            continue
        actual_date = _task_date_value(task, field)
        if actual_date is None:
            return False
        try:
            expected_date = date.fromisoformat(value)
        except ValueError:
            return False
        if not _compare_date(actual_date, operator, expected_date):
            return False
    return True


def _matches_status(task: object, status_filter: str) -> bool:
    if status_filter == "all":
        return True
    return _task_status_value(task) == status_filter


def _matches_priority(task: object, priority_filter: str) -> bool:
    if priority_filter == "all":
        return True
    priority_value = int(getattr(task, "priority", 0) or 0)
    if priority_filter == "high":
        return priority_value >= 70
    if priority_filter == "medium":
        return 30 <= priority_value <= 69
    if priority_filter == "low":
        return priority_value < 30
    return True


def _matches_schedule(
    task: object,
    schedule_filter: str,
    *,
    today: date | None = None,
) -> bool:
    if schedule_filter == "all":
        return True
    current_date = today or date.today()
    due_cutoff = current_date + timedelta(days=7)
    deadline = getattr(task, "deadline", None)
    if schedule_filter == "overdue":
        return deadline is not None and deadline < current_date
    if schedule_filter == "due_7":
        return deadline is not None and current_date <= deadline <= due_cutoff
    if schedule_filter == "no_deadline":
        return deadline is None
    return True


def _task_status_value(task: object) -> str:
    status_value = getattr(task, "status", "")
    return str(getattr(status_value, "value", status_value) or "")


def _task_date_value(task: object, field: str) -> date | None:
    if field == "start":
        return getattr(task, "start_date", None)
    if field == "end":
        return getattr(task, "end_date", None)
    return getattr(task, "deadline", None)


def _compare_numeric(actual: float, operator: str, expected: float) -> bool:
    resolved_operator = "=" if operator == ":" else operator
    if resolved_operator == "=":
        return abs(actual - expected) < 1e-9
    if resolved_operator == ">=":
        return actual >= expected
    if resolved_operator == "<=":
        return actual <= expected
    if resolved_operator == ">":
        return actual > expected
    if resolved_operator == "<":
        return actual < expected
    return False


def _compare_date(actual: date, operator: str, expected: date) -> bool:
    resolved_operator = "=" if operator == ":" else operator
    if resolved_operator == "=":
        return actual == expected
    if resolved_operator == ">=":
        return actual >= expected
    if resolved_operator == "<=":
        return actual <= expected
    if resolved_operator == ">":
        return actual > expected
    if resolved_operator == "<":
        return actual < expected
    return False


__all__ = [
    "build_task_priority_options",
    "build_task_schedule_options",
    "matches_task_filters",
    "normalize_task_filter",
    "parse_advanced_task_query",
]
