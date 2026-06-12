from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    PortfolioDependencyCreateCommand,
    PortfolioIntakeCreateCommand,
    PortfolioScenarioCreateCommand,
    PortfolioTemplateCreateCommand,
    ProjectManagementPortfolioDesktopApi,
)

from .validation import (
    list_text_values,
    optional_date,
    optional_float,
    optional_int,
    optional_text,
    require_text,
)

def create_template(
    desktop_api: ProjectManagementPortfolioDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = PortfolioTemplateCreateCommand(
        name=require_text(payload, "name", "Template name is required."),
        summary=optional_text(payload, "summary") or "",
        strategic_weight=optional_int(payload, "strategicWeight") or 3,
        value_weight=optional_int(payload, "valueWeight") or 2,
        urgency_weight=optional_int(payload, "urgencyWeight") or 2,
        risk_weight=optional_int(payload, "riskWeight") or 1,
        activate=bool(payload.get("activate")),
    )
    desktop_api.create_scoring_template(command)

def activate_template(
    desktop_api: ProjectManagementPortfolioDesktopApi,
    template_id: str,
) -> None:
    normalized_id = (template_id or "").strip()
    if not normalized_id:
        raise ValueError("Choose a scoring template to activate.")
    desktop_api.activate_scoring_template(normalized_id)

def create_intake_item(
    desktop_api: ProjectManagementPortfolioDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = PortfolioIntakeCreateCommand(
        title=require_text(payload, "title", "Intake title is required."),
        sponsor_name=require_text(payload, "sponsorName", "Sponsor is required."),
        summary=optional_text(payload, "summary") or "",
        requested_budget=optional_float(payload, "requestedBudget") or 0.0,
        requested_capacity_percent=optional_float(payload, "requestedCapacityPercent") or 0.0,
        target_start_date=optional_date(payload, "targetStartDate"),
        strategic_score=optional_int(payload, "strategicScore") or 3,
        value_score=optional_int(payload, "valueScore") or 3,
        urgency_score=optional_int(payload, "urgencyScore") or 3,
        risk_score=optional_int(payload, "riskScore") or 3,
        scoring_template_id=optional_text(payload, "scoringTemplateId"),
        status=optional_text(payload, "status") or "PROPOSED",
    )
    desktop_api.create_intake_item(command)

def create_scenario(
    desktop_api: ProjectManagementPortfolioDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = PortfolioScenarioCreateCommand(
        name=require_text(payload, "name", "Scenario name is required."),
        budget_limit=optional_float(payload, "budgetLimit"),
        capacity_limit_percent=optional_float(payload, "capacityLimitPercent"),
        project_ids=tuple(list_text_values(payload.get("projectIds"))),
        intake_item_ids=tuple(list_text_values(payload.get("intakeItemIds"))),
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.create_scenario(command)

def create_dependency(
    desktop_api: ProjectManagementPortfolioDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = PortfolioDependencyCreateCommand(
        predecessor_project_id=require_text(
            payload,
            "predecessorProjectId",
            "Choose a predecessor project.",
        ),
        successor_project_id=require_text(
            payload,
            "successorProjectId",
            "Choose a successor project.",
        ),
        dependency_type=optional_text(payload, "dependencyType") or "FINISH_TO_START",
        summary=optional_text(payload, "summary") or "",
    )
    desktop_api.create_project_dependency(command)

def remove_dependency(
    desktop_api: ProjectManagementPortfolioDesktopApi,
    dependency_id: str,
) -> None:
    normalized_id = (dependency_id or "").strip()
    if not normalized_id:
        raise ValueError("Choose a dependency to remove.")
    desktop_api.remove_project_dependency(normalized_id)

def update_intake_item_status(
    desktop_api: ProjectManagementPortfolioDesktopApi,
    item_id: str,
    status: str,
) -> None:
    normalized_id = (item_id or "").strip()
    if not normalized_id:
        raise ValueError("Choose an intake item to update.")
    desktop_api.update_intake_item_status(normalized_id, status)
