"""Project, task, and cost-type option builders."""

from __future__ import annotations
from datetime import date

from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.api.desktop.financials.models.options import (
    FinancialCostTypeDescriptor,
    FinancialProjectOptionDescriptor,
    FinancialTaskOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.financials.formatters.enum_formatter import format_enum_label


def build_project_options(project_service=None) -> tuple[FinancialProjectOptionDescriptor, ...]:
    if project_service is None:
        return ()
    projects = sorted(project_service.list_projects(), key=lambda p: (p.name or "").casefold())
    return tuple(FinancialProjectOptionDescriptor(value=p.id, label=p.name) for p in projects)


def build_task_options(project_id: str, task_service=None) -> tuple[FinancialTaskOptionDescriptor, ...]:
    if task_service is None or not project_id:
        return ()
    tasks = sorted(
        task_service.list_tasks_for_project(project_id),
        key=lambda t: (t.start_date or date.max, (t.name or "").casefold()),
    )
    return tuple(FinancialTaskOptionDescriptor(value=t.id, label=t.name) for t in tasks)


def build_cost_type_options() -> tuple[FinancialCostTypeDescriptor, ...]:
    return tuple(
        FinancialCostTypeDescriptor(value=ct.value, label=format_enum_label(ct.value))
        for ct in CostType
    )


__all__ = ["build_cost_type_options", "build_project_options", "build_task_options"]
