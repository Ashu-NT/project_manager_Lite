"""Operational Task-code policy shared by Task lifecycle commands."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from src.core.modules.project_management.contracts.repositories.task import TaskRepository
from src.core.platform.common.code_generation import (
    CodeGenerator,
    assert_code_unique,
    normalize_manual_code,
)
from src.core.platform.common.exceptions import ValidationError


class TaskIdentityMixin:
    _task_repo: TaskRepository

    def _resolve_task_code(
        self,
        code: str,
        project_id: str,
        name: str,
        *,
        exclude_id: str | None = None,
    ) -> str:
        existing = {
            str(getattr(task, "code", "") or "").upper()
            for task in self._task_repo.list_by_project(project_id)
            if exclude_id is None or task.id != exclude_id
        }
        manual = normalize_manual_code(code)
        if manual:
            assert_code_unique(
                manual,
                exists=lambda candidate: candidate.upper() in existing,
                label="Task code",
            )
            return manual
        return CodeGenerator().generate(
            "task",
            exists=lambda candidate: candidate.upper() in existing,
            name=(name or "").strip() or None,
            use_year=not bool((name or "").strip()),
        )

    @staticmethod
    def _is_task_code_integrity_error(exc: IntegrityError) -> bool:
        message = " ".join(
            part
            for part in [
                str(getattr(exc, "orig", "") or ""),
                str(getattr(exc, "statement", "") or ""),
                str(exc),
            ]
            if part
        ).lower()
        return "ux_tasks_project_code" in message or "tasks.task_code" in message

    @staticmethod
    def _raise_task_code_duplicate(code: str, exc: IntegrityError) -> None:
        raise ValidationError(
            f"Task code '{code}' already exists.",
            code="CODE_DUPLICATE",
        ) from exc


__all__ = ["TaskIdentityMixin"]
