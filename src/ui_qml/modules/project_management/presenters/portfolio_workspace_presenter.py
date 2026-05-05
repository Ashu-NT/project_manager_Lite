from __future__ import annotations

from datetime import date
from typing import Any

from src.core.modules.project_management.api.desktop import (
    PortfolioDependencyCreateCommand,
    PortfolioIntakeCreateCommand,
    PortfolioScenarioCreateCommand,
    PortfolioTemplateCreateCommand,
    ProjectManagementPortfolioDesktopApi,
    build_project_management_portfolio_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioCollectionViewModel,
    PortfolioMetricViewModel,
    PortfolioOverviewViewModel,
    PortfolioRecordViewModel,
    PortfolioSelectorOptionViewModel,
    PortfolioSummaryFieldViewModel,
    PortfolioSummaryViewModel,
    PortfolioWorkspaceViewModel,
)


class ProjectPortfolioWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementPortfolioDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_portfolio_desktop_api()

    def build_workspace_state(
        self,
        *,
        intake_status_filter: str = "all",
        selected_scenario_id: str | None = None,
        base_compare_scenario_id: str | None = None,
        compare_scenario_id: str | None = None,
    ) -> PortfolioWorkspaceViewModel:
        templates = self._desktop_api.list_templates()
        intake_items = self._desktop_api.list_intake_items()
        scenarios = self._desktop_api.list_scenarios()
        heatmap = self._desktop_api.list_heatmap()
        dependencies = self._desktop_api.list_dependencies()
        recent_actions = self._desktop_api.list_recent_actions(limit=12)
        intake_status_options = (
            PortfolioSelectorOptionViewModel(value="all", label="All statuses"),
            *(
                PortfolioSelectorOptionViewModel(
                    value=option.value,
                    label=option.label,
                )
                for option in self._desktop_api.list_intake_statuses()
            ),
        )
        template_options = tuple(
            PortfolioSelectorOptionViewModel(value=option.id, label=option.name)
            for option in templates
        )
        project_options = tuple(
            PortfolioSelectorOptionViewModel(value=option.value, label=option.label)
            for option in self._desktop_api.list_projects()
        )
        scenario_options = tuple(
            PortfolioSelectorOptionViewModel(value=option.id, label=option.name)
            for option in scenarios
        )
        dependency_type_options = tuple(
            PortfolioSelectorOptionViewModel(value=option.value, label=option.label)
            for option in self._desktop_api.list_dependency_types()
        )
        normalized_intake_status_filter = self._normalize_filter(
            intake_status_filter,
            intake_status_options,
            default_value="all",
        )
        filtered_intake_items = tuple(
            item
            for item in intake_items
            if normalized_intake_status_filter == "all"
            or item.status == normalized_intake_status_filter
        )
        resolved_scenario_id = self._resolve_selected_id(selected_scenario_id, scenarios)
        resolved_base_compare_id = self._resolve_selected_id(
            base_compare_scenario_id,
            scenarios,
            preferred_fallback_index=0,
        )
        resolved_compare_scenario_id = self._resolve_compare_id(
            compare_scenario_id,
            scenarios,
            disallowed_id=resolved_base_compare_id,
        )
        active_template = next(
            (template for template in templates if template.is_active),
            None,
        )
        evaluation = self._build_evaluation_summary(resolved_scenario_id)
        comparison = self._build_comparison_summary(
            base_scenario_id=resolved_base_compare_id,
            compare_scenario_id=resolved_compare_scenario_id,
        )
        empty_state = self._build_empty_state(
            filtered_intake_items=filtered_intake_items,
            all_intake_items=intake_items,
            intake_status_filter=normalized_intake_status_filter,
            templates=templates,
            scenarios=scenarios,
        )
        hot_projects = sum(1 for row in heatmap if row.pressure_label == "Hot")
        return PortfolioWorkspaceViewModel(
            overview=PortfolioOverviewViewModel(
                title="Portfolio",
                subtitle="Portfolio planning, intake scoring, scenario comparison, and cross-project delivery pressure.",
                metrics=(
                    PortfolioMetricViewModel(
                        label="Intake",
                        value=str(len(filtered_intake_items)),
                        supporting_text=f"{len(intake_items)} total ideas in the current PM portfolio.",
                    ),
                    PortfolioMetricViewModel(
                        label="Scenarios",
                        value=str(len(scenarios)),
                        supporting_text="Saved what-if portfolios ready for evaluation.",
                    ),
                    PortfolioMetricViewModel(
                        label="Hot projects",
                        value=str(hot_projects),
                        supporting_text="Projects currently marked with delivery pressure.",
                    ),
                    PortfolioMetricViewModel(
                        label="Dependencies",
                        value=str(len(dependencies)),
                        supporting_text="Cross-project sequencing links tracked at portfolio level.",
                    ),
                    PortfolioMetricViewModel(
                        label="Active template",
                        value=active_template.name if active_template else "None",
                        supporting_text=active_template.weight_summary if active_template else "Create or activate a scoring template.",
                    ),
                ),
            ),
            intake_status_options=intake_status_options,
            template_options=template_options,
            project_options=project_options,
            scenario_options=scenario_options,
            dependency_type_options=dependency_type_options,
            selected_intake_status_filter=normalized_intake_status_filter,
            selected_scenario_id=resolved_scenario_id,
            selected_base_scenario_id=resolved_base_compare_id,
            selected_compare_scenario_id=resolved_compare_scenario_id,
            intake_items=PortfolioCollectionViewModel(
                title="Portfolio Intake",
                subtitle="Capture proposed work, budgets, and capacity demand before it becomes committed project scope.",
                empty_state=(
                    "No intake items match the current filter."
                    if intake_items and not filtered_intake_items
                    else "No intake items are available yet."
                ),
                items=tuple(self._to_intake_record(item) for item in filtered_intake_items),
            ),
            templates=PortfolioCollectionViewModel(
                title="Scoring Templates",
                subtitle="Keep one active scoring model for intake decisions and swap it only when governance rules change.",
                empty_state="No scoring templates are available yet.",
                items=tuple(self._to_template_record(item) for item in templates),
            ),
            scenarios=PortfolioCollectionViewModel(
                title="Scenario Library",
                subtitle="Review saved what-if portfolios and compare their budget, capacity, and intake impact.",
                empty_state="No portfolio scenarios are available yet.",
                items=tuple(self._to_scenario_record(item) for item in scenarios),
            ),
            evaluation=evaluation,
            comparison=comparison,
            heatmap=PortfolioCollectionViewModel(
                title="Portfolio Heatmap",
                subtitle="Cross-project delivery pressure across the accessible PM portfolio.",
                empty_state="No heatmap rows are available yet.",
                items=tuple(self._to_heatmap_record(item) for item in heatmap),
            ),
            dependencies=PortfolioCollectionViewModel(
                title="Cross-project Dependencies",
                subtitle="Shared delivery links that shape sequencing across project boundaries.",
                empty_state="No cross-project dependencies are available yet.",
                items=tuple(self._to_dependency_record(item) for item in dependencies),
            ),
            recent_actions=PortfolioCollectionViewModel(
                title="Recent Actions",
                subtitle="The latest project, task, baseline, approval, timesheet, and portfolio events worth executive review.",
                empty_state="No recent PM actions are available yet.",
                items=tuple(self._to_recent_action_record(item) for item in recent_actions),
            ),
            active_template_summary=(
                f"Active template: {active_template.name}. {active_template.weight_summary}"
                if active_template
                else "No active scoring template."
            ),
            empty_state=empty_state,
        )

    def create_template(self, payload: dict[str, Any]) -> None:
        command = PortfolioTemplateCreateCommand(
            name=self._require_text(payload, "name", "Template name is required."),
            summary=self._optional_text(payload, "summary") or "",
            strategic_weight=self._optional_int(payload, "strategicWeight") or 3,
            value_weight=self._optional_int(payload, "valueWeight") or 2,
            urgency_weight=self._optional_int(payload, "urgencyWeight") or 2,
            risk_weight=self._optional_int(payload, "riskWeight") or 1,
            activate=bool(payload.get("activate")),
        )
        self._desktop_api.create_scoring_template(command)

    def activate_template(self, template_id: str) -> None:
        normalized_template_id = (template_id or "").strip()
        if not normalized_template_id:
            raise ValueError("Choose a scoring template to activate.")
        self._desktop_api.activate_scoring_template(normalized_template_id)

    def create_intake_item(self, payload: dict[str, Any]) -> None:
        command = PortfolioIntakeCreateCommand(
            title=self._require_text(payload, "title", "Intake title is required."),
            sponsor_name=self._require_text(payload, "sponsorName", "Sponsor is required."),
            summary=self._optional_text(payload, "summary") or "",
            requested_budget=self._optional_float(payload, "requestedBudget") or 0.0,
            requested_capacity_percent=self._optional_float(payload, "requestedCapacityPercent") or 0.0,
            target_start_date=self._optional_date(payload, "targetStartDate"),
            strategic_score=self._optional_int(payload, "strategicScore") or 3,
            value_score=self._optional_int(payload, "valueScore") or 3,
            urgency_score=self._optional_int(payload, "urgencyScore") or 3,
            risk_score=self._optional_int(payload, "riskScore") or 3,
            scoring_template_id=self._optional_text(payload, "scoringTemplateId"),
            status=self._optional_text(payload, "status") or "PROPOSED",
        )
        self._desktop_api.create_intake_item(command)

    def create_scenario(self, payload: dict[str, Any]) -> None:
        command = PortfolioScenarioCreateCommand(
            name=self._require_text(payload, "name", "Scenario name is required."),
            budget_limit=self._optional_float(payload, "budgetLimit"),
            capacity_limit_percent=self._optional_float(payload, "capacityLimitPercent"),
            project_ids=tuple(self._list_text_values(payload.get("projectIds"))),
            intake_item_ids=tuple(self._list_text_values(payload.get("intakeItemIds"))),
            notes=self._optional_text(payload, "notes") or "",
        )
        self._desktop_api.create_scenario(command)

    def create_dependency(self, payload: dict[str, Any]) -> None:
        command = PortfolioDependencyCreateCommand(
            predecessor_project_id=self._require_text(
                payload,
                "predecessorProjectId",
                "Choose a predecessor project.",
            ),
            successor_project_id=self._require_text(
                payload,
                "successorProjectId",
                "Choose a successor project.",
            ),
            dependency_type=self._optional_text(payload, "dependencyType") or "FINISH_TO_START",
            summary=self._optional_text(payload, "summary") or "",
        )
        self._desktop_api.create_project_dependency(command)

    def remove_dependency(self, dependency_id: str) -> None:
        normalized_dependency_id = (dependency_id or "").strip()
        if not normalized_dependency_id:
            raise ValueError("Choose a dependency to remove.")
        self._desktop_api.remove_project_dependency(normalized_dependency_id)

    def _build_evaluation_summary(self, scenario_id: str) -> PortfolioSummaryViewModel:
        if not scenario_id:
            return PortfolioSummaryViewModel(
                title="Scenario Evaluation",
                empty_state="Select a scenario to review budget, capacity, and intake impact.",
            )
        evaluation = self._desktop_api.evaluate_scenario(scenario_id)
        return PortfolioSummaryViewModel(
            title=f"Scenario Evaluation: {evaluation.scenario_name}",
            subtitle=evaluation.summary,
            fields=(
                PortfolioSummaryFieldViewModel(
                    label="Projects",
                    value=evaluation.selected_projects_label,
                ),
                PortfolioSummaryFieldViewModel(
                    label="Intake items",
                    value=evaluation.selected_intake_items_label,
                ),
                PortfolioSummaryFieldViewModel(
                    label="Budget",
                    value=evaluation.total_budget_label,
                    supporting_text=f"Limit: {evaluation.budget_limit_label}",
                ),
                PortfolioSummaryFieldViewModel(
                    label="Capacity",
                    value=evaluation.total_capacity_label,
                    supporting_text=f"Limit: {evaluation.capacity_limit_label}",
                ),
                PortfolioSummaryFieldViewModel(
                    label="Available capacity",
                    value=evaluation.available_capacity_label,
                ),
                PortfolioSummaryFieldViewModel(
                    label="Intake score",
                    value=evaluation.intake_score_label,
                    supporting_text=evaluation.status_label,
                ),
            ),
        )

    def _build_comparison_summary(
        self,
        *,
        base_scenario_id: str,
        compare_scenario_id: str,
    ) -> PortfolioSummaryViewModel:
        if not base_scenario_id or not compare_scenario_id:
            return PortfolioSummaryViewModel(
                title="Scenario Comparison",
                empty_state="Select two saved scenarios to compare budget, capacity, and selection changes.",
            )
        comparison = self._desktop_api.compare_scenarios(
            base_scenario_id,
            compare_scenario_id,
        )
        added_projects = ", ".join(comparison.added_project_names) or "None"
        removed_projects = ", ".join(comparison.removed_project_names) or "None"
        added_intake = ", ".join(comparison.added_intake_titles) or "None"
        removed_intake = ", ".join(comparison.removed_intake_titles) or "None"
        return PortfolioSummaryViewModel(
            title=(
                f"Scenario Comparison: {comparison.base_scenario_name} vs "
                f"{comparison.candidate_scenario_name}"
            ),
            subtitle=comparison.summary,
            fields=(
                PortfolioSummaryFieldViewModel(
                    label="Budget delta",
                    value=comparison.budget_delta_label,
                ),
                PortfolioSummaryFieldViewModel(
                    label="Capacity delta",
                    value=comparison.capacity_delta_label,
                ),
                PortfolioSummaryFieldViewModel(
                    label="Projects delta",
                    value=comparison.selected_projects_delta_label,
                    supporting_text=f"Added: {added_projects} | Removed: {removed_projects}",
                ),
                PortfolioSummaryFieldViewModel(
                    label="Intake delta",
                    value=comparison.selected_intake_items_delta_label,
                    supporting_text=f"Added: {added_intake} | Removed: {removed_intake}",
                ),
                PortfolioSummaryFieldViewModel(
                    label="Score delta",
                    value=comparison.intake_score_delta_label,
                ),
            ),
        )

    @staticmethod
    def _to_intake_record(item) -> PortfolioRecordViewModel:
        return PortfolioRecordViewModel(
            id=item.id,
            title=item.title,
            status_label=item.status_label,
            subtitle=f"Sponsor: {item.sponsor_name}",
            supporting_text=(
                f"Budget {item.requested_budget_label} | Capacity {item.requested_capacity_label} | "
                f"Template {item.scoring_template_name}"
            ),
            meta_text=item.summary or f"Composite score: {item.composite_score}",
            can_primary_action=False,
            can_secondary_action=False,
            state={
                "intakeItemId": item.id,
                "status": item.status,
                "scoringTemplateId": item.scoring_template_id,
                "version": item.version,
            },
        )

    @staticmethod
    def _to_template_record(item) -> PortfolioRecordViewModel:
        return PortfolioRecordViewModel(
            id=item.id,
            title=item.name,
            status_label="Active" if item.is_active else "Available",
            subtitle=item.weight_summary,
            supporting_text=item.summary or "No template summary recorded.",
            meta_text=(
                "This template currently drives composite intake scoring."
                if item.is_active
                else "Activate this template to make it the portfolio scoring baseline."
            ),
            can_primary_action=not item.is_active,
            can_secondary_action=False,
            state={"templateId": item.id, "isActive": item.is_active},
        )

    @staticmethod
    def _to_scenario_record(item) -> PortfolioRecordViewModel:
        return PortfolioRecordViewModel(
            id=item.id,
            title=item.name,
            status_label="Scenario",
            subtitle=(
                f"Budget limit: {item.budget_limit_label} | Capacity limit: {item.capacity_limit_label}"
            ),
            supporting_text=(
                f"Projects: {len(item.project_ids)} | Intake items: {len(item.intake_item_ids)}"
            ),
            meta_text=item.notes or f"Created: {item.created_at_label}",
            can_primary_action=False,
            can_secondary_action=False,
            state={"scenarioId": item.id},
        )

    @staticmethod
    def _to_heatmap_record(item) -> PortfolioRecordViewModel:
        return PortfolioRecordViewModel(
            id=item.project_id,
            title=item.project_name,
            status_label=item.pressure_label,
            subtitle=item.project_status_label,
            supporting_text=(
                f"Late {item.late_tasks} | Critical {item.critical_tasks} | "
                f"Peak util {item.peak_utilization_label}"
            ),
            meta_text=f"Cost variance {item.cost_variance_label}",
            can_primary_action=False,
            can_secondary_action=False,
            state={"projectId": item.project_id},
        )

    @staticmethod
    def _to_dependency_record(item) -> PortfolioRecordViewModel:
        return PortfolioRecordViewModel(
            id=item.dependency_id,
            title=f"{item.predecessor_project_name} -> {item.successor_project_name}",
            status_label=item.pressure_label,
            subtitle=item.dependency_type_label,
            supporting_text=(
                f"Predecessor {item.predecessor_project_status_label} | "
                f"Successor {item.successor_project_status_label}"
            ),
            meta_text=item.summary or f"Created: {item.created_at_label}",
            can_primary_action=True,
            can_secondary_action=False,
            state={"dependencyId": item.dependency_id},
        )

    @staticmethod
    def _to_recent_action_record(item) -> PortfolioRecordViewModel:
        return PortfolioRecordViewModel(
            id=f"{item.occurred_at_label}-{item.project_name}-{item.action_label}",
            title=item.action_label,
            status_label=item.project_name,
            subtitle=f"{item.actor_username} | {item.occurred_at_label}",
            supporting_text=item.summary,
            meta_text="",
            can_primary_action=False,
            can_secondary_action=False,
        )

    @staticmethod
    def _normalize_filter(value: str, options, *, default_value: str) -> str:
        normalized_value = (value or default_value).strip().lower()
        available_values = {
            str(option.value or "").strip().lower(): option.value
            for option in options
        }
        return available_values.get(normalized_value, default_value)

    @staticmethod
    def _resolve_selected_id(
        selected_id: str | None,
        rows,
        *,
        preferred_fallback_index: int = 0,
    ) -> str:
        normalized_id = (selected_id or "").strip()
        available_ids = [str(getattr(row, "id", "") or "") for row in rows]
        if normalized_id and normalized_id in available_ids:
            return normalized_id
        if not rows:
            return ""
        fallback_index = min(max(preferred_fallback_index, 0), len(rows) - 1)
        return str(getattr(rows[fallback_index], "id", "") or "")

    @staticmethod
    def _resolve_compare_id(compare_id: str | None, rows, *, disallowed_id: str) -> str:
        normalized_id = (compare_id or "").strip()
        available_ids = [
            str(getattr(row, "id", "") or "")
            for row in rows
            if str(getattr(row, "id", "") or "") != disallowed_id
        ]
        if normalized_id and normalized_id in available_ids:
            return normalized_id
        return available_ids[0] if available_ids else ""

    @staticmethod
    def _build_empty_state(
        *,
        filtered_intake_items,
        all_intake_items,
        intake_status_filter: str,
        templates,
        scenarios,
    ) -> str:
        if filtered_intake_items:
            return ""
        if all_intake_items:
            if intake_status_filter != "all":
                return "No intake items match the current status filter."
            return ""
        if not templates:
            return "No scoring templates or intake items are available yet. Start by creating the first scoring template."
        if not scenarios:
            return "No portfolio scenarios are available yet. Create intake items and save the first scenario."
        return "No portfolio planning data is available yet."

    @staticmethod
    def _require_text(payload: dict[str, Any], key: str, message: str) -> str:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            raise ValueError(message)
        return value

    @staticmethod
    def _optional_text(payload: dict[str, Any], key: str) -> str | None:
        value = str(payload.get(key, "") or "").strip()
        return value or None

    @staticmethod
    def _optional_int(payload: dict[str, Any], key: str) -> int | None:
        value = payload.get(key)
        if value in (None, ""):
            return None
        return int(value)

    @staticmethod
    def _optional_float(payload: dict[str, Any], key: str) -> float | None:
        value = payload.get(key)
        if value in (None, ""):
            return None
        return float(value)

    @staticmethod
    def _optional_date(payload: dict[str, Any], key: str) -> date | None:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Dates must use YYYY-MM-DD.") from exc

    @staticmethod
    def _list_text_values(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [normalized for normalized in (part.strip() for part in value.split(",")) if normalized]
        if isinstance(value, (list, tuple, set)):
            return [normalized for normalized in (str(part or "").strip() for part in value) if normalized]
        return []


__all__ = ["ProjectPortfolioWorkspacePresenter"]
