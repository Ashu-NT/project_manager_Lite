from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    FinancialCreateCommand,
    FinancialUpdateCommand,
    ProjectManagementFinancialsDesktopApi,
)

from .validation import (
    optional_date,
    optional_float,
    optional_int,
    optional_text,
    require_float,
    require_text,
)

def suggest_code(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    payload: dict[str, Any],
) -> str:
    from src.core.platform.common.code_generation import CodeGenerator

    project_id = optional_text(payload, "projectId")
    existing = {
        str(getattr(row, "code", "") or "").upper()
        for row in (desktop_api.list_cost_items(project_id) if project_id else [])
    }
    name = optional_text(payload, "description")
    return CodeGenerator().generate(
        "cost",
        exists=lambda code: code.upper() in existing,
        name=name or None,
        use_year=not bool(name),
    )

def create_cost_item(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = FinancialCreateCommand(
        project_id=require_text(payload, "projectId", "Select a project before creating a cost item."),
        description=require_text(payload, "description", "Description is required."),
        planned_amount=require_float(payload, "plannedAmount", "Planned amount must be a valid number."),
        task_id=optional_text(payload, "taskId"),
        cost_type=optional_text(payload, "costType") or "OVERHEAD",
        committed_amount=optional_float(payload, "committedAmount", "Committed amount must be a valid number."),
        actual_amount=optional_float(payload, "actualAmount", "Actual amount must be a valid number."),
        incurred_date=optional_date(payload, "incurredDate"),
        currency_code=optional_text(payload, "currency"),
        code=optional_text(payload, "costCode"),
    )
    desktop_api.create_cost_item(command)

def update_cost_item(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = FinancialUpdateCommand(
        cost_id=require_text(payload, "costId", "Cost item ID is required for updates."),
        description=require_text(payload, "description", "Description is required."),
        planned_amount=require_float(payload, "plannedAmount", "Planned amount must be a valid number."),
        task_id=optional_text(payload, "taskId"),
        cost_type=optional_text(payload, "costType") or "OVERHEAD",
        committed_amount=optional_float(payload, "committedAmount", "Committed amount must be a valid number."),
        actual_amount=optional_float(payload, "actualAmount", "Actual amount must be a valid number."),
        incurred_date=optional_date(payload, "incurredDate"),
        currency_code=optional_text(payload, "currency"),
        expected_version=optional_int(payload, "expectedVersion"),
        code=optional_text(payload, "costCode"),
    )
    desktop_api.update_cost_item(command)

def delete_cost_item(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    cost_id: str,
) -> None:
    normalized_value = (cost_id or "").strip()
    if not normalized_value:
        raise ValueError("Cost item ID is required to delete a cost item.")
    desktop_api.delete_cost_item(normalized_value)
