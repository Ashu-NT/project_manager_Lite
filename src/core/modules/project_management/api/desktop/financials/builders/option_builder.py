"""Project and task option builders."""

from __future__ import annotations
from datetime import date

from src.core.modules.project_management.api.desktop.financials.models.options import (
    FinancialProjectOptionDescriptor,
    FinancialTaskOptionDescriptor,
)


def build_project_options(project_service=None) -> tuple[FinancialProjectOptionDescriptor, ...]:
    if project_service is None:
        return ()
    projects = sorted(project_service.list_projects(), key=lambda p: (p.name or "").casefold())
    return tuple(FinancialProjectOptionDescriptor(value=p.id, label=p.name) for p in projects)


def build_task_options(project_id: str, task_service=None) -> tuple[FinancialTaskOptionDescriptor, ...]:
    if task_service is None or not project_id:
        return ()
    list_hierarchy = getattr(task_service, "list_task_hierarchy", None)
    if callable(list_hierarchy):
        tasks = [node.task for node in list_hierarchy(project_id)]
    else:
        tasks = sorted(
            task_service.list_tasks_for_project(project_id),
            key=lambda t: (t.start_date or date.max, (t.name or "").casefold()),
        )
    return tuple(
        FinancialTaskOptionDescriptor(
            value=task.id,
            label=f"{getattr(task, 'wbs_code', '')}  {task.name}".strip(),
        )
        for task in tasks
    )


__all__ = ["build_project_options", "build_task_options"]
