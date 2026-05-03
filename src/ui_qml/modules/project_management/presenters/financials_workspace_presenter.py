from __future__ import annotations

from datetime import date
from typing import Any

from src.core.modules.project_management.api.desktop import (
    FinancialCreateCommand,
    FinancialUpdateCommand,
    ProjectManagementFinancialsDesktopApi,
    build_project_management_financials_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsMetricViewModel,
    FinancialsOverviewViewModel,
    FinancialsRecordViewModel,
    FinancialsSelectorOptionViewModel,
    FinancialsWorkspaceViewModel,
)


class ProjectFinancialsWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementFinancialsDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_financials_desktop_api()

    def build_workspace_state(
        self,
        *,
        selected_project_id: str | None = None,
        selected_cost_type: str = "all",
        search_text: str = "",
        selected_cost_id: str | None = None,
    ) -> FinancialsWorkspaceViewModel:
        project_options = tuple(
            FinancialsSelectorOptionViewModel(value=option.value, label=option.label)
            for option in self._desktop_api.list_projects()
        )
        resolved_project_id = self._resolve_selected_project_id(
            selected_project_id,
            project_options,
        )
        cost_type_options = (
            FinancialsSelectorOptionViewModel(value="all", label="All categories"),
            *(
                FinancialsSelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_cost_types()
            ),
        )
        task_options = (
            FinancialsSelectorOptionViewModel(value="", label="Not linked to a task"),
            *(
                FinancialsSelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_tasks(resolved_project_id)
            ),
        )
        normalized_search = (search_text or "").strip()
        normalized_cost_type = self._normalize_cost_type_filter(
            selected_cost_type,
            cost_type_options,
        )
        all_costs = self._desktop_api.list_cost_items(resolved_project_id)
        filtered_costs = tuple(
            cost
            for cost in all_costs
            if self._matches_cost_type(cost, normalized_cost_type)
            and self._matches_search(cost, normalized_search)
        )
        resolved_selected_cost_id = self._resolve_selected_cost_id(
            selected_cost_id,
            filtered_costs,
        )
        selected_cost = next(
            (cost for cost in filtered_costs if cost.id == resolved_selected_cost_id),
            None,
        )
        snapshot = self._desktop_api.get_finance_snapshot(resolved_project_id)
        empty_state = self._build_empty_state(
            project_options=project_options,
            all_costs=all_costs,
            filtered_costs=filtered_costs,
            selected_project_id=resolved_project_id,
            search_text=normalized_search,
            selected_cost_type=normalized_cost_type,
        )
        return FinancialsWorkspaceViewModel(
            overview=self._build_overview(
                project_options=project_options,
                selected_project_id=resolved_project_id,
                snapshot=snapshot,
                all_costs=all_costs,
                filtered_costs=filtered_costs,
            ),
            project_options=project_options,
            cost_type_options=cost_type_options,
            task_options=task_options,
            selected_project_id=resolved_project_id,
            selected_cost_type=normalized_cost_type,
            search_text=normalized_search,
            costs=FinancialsCollectionViewModel(
                title="Cost Items",
                subtitle="Manage planned, committed, and actual cost lines for the selected project.",
                empty_state=empty_state,
                items=tuple(self._to_cost_record_view_model(cost) for cost in filtered_costs),
            ),
            selected_cost_id=resolved_selected_cost_id,
            selected_cost_detail=self._build_detail_view_model(selected_cost),
            cashflow=self._build_cashflow_collection(snapshot),
            ledger=self._build_ledger_collection(snapshot),
            source_analytics=self._build_analytics_collection(
                title="Source Breakdown",
                subtitle="Expense exposure grouped by source.",
                rows=snapshot.by_source,
            ),
            cost_type_analytics=self._build_analytics_collection(
                title="Cost Type Breakdown",
                subtitle="Expense exposure grouped by category.",
                rows=snapshot.by_cost_type,
            ),
            notes=tuple(snapshot.notes),
            empty_state=empty_state,
        )

    def create_cost_item(self, payload: dict[str, Any]) -> None:
        command = FinancialCreateCommand(
            project_id=self._require_text(
                payload,
                "projectId",
                "Select a project before creating a cost item.",
            ),
            description=self._require_text(
                payload,
                "description",
                "Description is required.",
            ),
            planned_amount=self._required_float(
                payload,
                "plannedAmount",
                "Planned amount must be a valid number.",
            ),
            task_id=self._optional_text(payload, "taskId"),
            cost_type=self._optional_text(payload, "costType") or "OVERHEAD",
            committed_amount=self._optional_float(
                payload,
                "committedAmount",
                "Committed amount must be a valid number.",
            ),
            actual_amount=self._optional_float(
                payload,
                "actualAmount",
                "Actual amount must be a valid number.",
            ),
            incurred_date=self._optional_date(payload, "incurredDate"),
            currency_code=self._optional_text(payload, "currency"),
        )
        self._desktop_api.create_cost_item(command)

    def update_cost_item(self, payload: dict[str, Any]) -> None:
        command = FinancialUpdateCommand(
            cost_id=self._require_text(
                payload,
                "costId",
                "Cost item ID is required for updates.",
            ),
            description=self._require_text(
                payload,
                "description",
                "Description is required.",
            ),
            planned_amount=self._required_float(
                payload,
                "plannedAmount",
                "Planned amount must be a valid number.",
            ),
            task_id=self._optional_text(payload, "taskId"),
            cost_type=self._optional_text(payload, "costType") or "OVERHEAD",
            committed_amount=self._optional_float(
                payload,
                "committedAmount",
                "Committed amount must be a valid number.",
            ),
            actual_amount=self._optional_float(
                payload,
                "actualAmount",
                "Actual amount must be a valid number.",
            ),
            incurred_date=self._optional_date(payload, "incurredDate"),
            currency_code=self._optional_text(payload, "currency"),
            expected_version=self._optional_int(payload, "expectedVersion"),
        )
        self._desktop_api.update_cost_item(command)

    def delete_cost_item(self, cost_id: str) -> None:
        normalized_value = (cost_id or "").strip()
        if not normalized_value:
            raise ValueError("Cost item ID is required to delete a cost item.")
        self._desktop_api.delete_cost_item(normalized_value)

    @staticmethod
    def _resolve_selected_project_id(
        selected_project_id: str | None,
        project_options: tuple[FinancialsSelectorOptionViewModel, ...],
    ) -> str:
        normalized_value = (selected_project_id or "").strip()
        if normalized_value and any(
            option.value == normalized_value for option in project_options
        ):
            return normalized_value
        if project_options:
            return project_options[0].value
        return ""

    @staticmethod
    def _normalize_cost_type_filter(
        selected_cost_type: str,
        cost_type_options: tuple[FinancialsSelectorOptionViewModel, ...],
    ) -> str:
        normalized_value = (selected_cost_type or "all").strip().upper()
        available = {option.value.upper(): option.value for option in cost_type_options}
        return available.get(normalized_value, "all")

    @staticmethod
    def _resolve_selected_cost_id(
        selected_cost_id: str | None,
        filtered_costs,
    ) -> str:
        normalized_value = (selected_cost_id or "").strip()
        if normalized_value and any(cost.id == normalized_value for cost in filtered_costs):
            return normalized_value
        if filtered_costs:
            return filtered_costs[0].id
        return ""

    @staticmethod
    def _matches_cost_type(cost, selected_cost_type: str) -> bool:
        if selected_cost_type == "all":
            return True
        return cost.cost_type == selected_cost_type

    @staticmethod
    def _matches_search(cost, search_text: str) -> bool:
        if not search_text:
            return True
        normalized_search = search_text.casefold()
        haystacks = (
            cost.description or "",
            cost.task_name or "",
            cost.cost_type_label or "",
            cost.currency_code or "",
        )
        return any(normalized_search in value.casefold() for value in haystacks)

    def _build_overview(
        self,
        *,
        project_options,
        selected_project_id: str,
        snapshot,
        all_costs,
        filtered_costs,
    ) -> FinancialsOverviewViewModel:
        project_label = next(
            (option.label for option in project_options if option.value == selected_project_id),
            "Financials",
        )
        return FinancialsOverviewViewModel(
            title="Financials",
            subtitle=(
                f"{project_label} cost control, budget health, ledger, and cashflow."
                if selected_project_id
                else "Select a project to review cost control and finance exposure."
            ),
            metrics=(
                FinancialsMetricViewModel(
                    label="Budget",
                    value=snapshot.budget_label,
                    supporting_text="Planned budget available to the selected project.",
                ),
                FinancialsMetricViewModel(
                    label="Planned",
                    value=snapshot.planned_label,
                    supporting_text=f"{len(all_costs)} cost items loaded; {len(filtered_costs)} shown.",
                ),
                FinancialsMetricViewModel(
                    label="Committed",
                    value=snapshot.committed_label,
                    supporting_text="Committed exposure recorded on the selected project.",
                ),
                FinancialsMetricViewModel(
                    label="Actual",
                    value=snapshot.actual_label,
                    supporting_text="Actual spend captured in the project ledger.",
                ),
                FinancialsMetricViewModel(
                    label="Available",
                    value=snapshot.available_label,
                    supporting_text="Remaining headroom after current exposure.",
                ),
            ),
        )

    def _build_detail_view_model(self, cost) -> FinancialsDetailViewModel:
        if cost is None:
            return FinancialsDetailViewModel(
                title="No cost item selected",
                empty_state="Select a cost item to inspect financial detail or adjust the entry.",
            )
        state = self._build_cost_state(cost)
        return FinancialsDetailViewModel(
            id=cost.id,
            title=cost.description,
            status_label=cost.cost_type_label,
            subtitle=cost.task_name,
            description=(
                "Track planned, committed, and actual amounts for this selected cost line."
            ),
            fields=(
                FinancialsDetailFieldViewModel(
                    label="Planned",
                    value=cost.planned_amount_label,
                    supporting_text="Baseline expected amount.",
                ),
                FinancialsDetailFieldViewModel(
                    label="Committed",
                    value=cost.committed_amount_label,
                    supporting_text="Committed commercial exposure.",
                ),
                FinancialsDetailFieldViewModel(
                    label="Actual",
                    value=cost.actual_amount_label,
                    supporting_text="Actual recognized spend.",
                ),
                FinancialsDetailFieldViewModel(
                    label="Task",
                    value=cost.task_name,
                ),
                FinancialsDetailFieldViewModel(
                    label="Incurred date",
                    value=cost.incurred_date_label,
                ),
                FinancialsDetailFieldViewModel(
                    label="Version",
                    value=str(cost.version),
                ),
            ),
            state=state,
        )

    def _build_cashflow_collection(self, snapshot) -> FinancialsCollectionViewModel:
        return FinancialsCollectionViewModel(
            title="Cashflow",
            subtitle="Forecast, actuals, and exposure grouped by period.",
            empty_state="No finance periods are available for the selected project.",
            items=tuple(
                FinancialsRecordViewModel(
                    id=row.period_key,
                    title=row.period_key,
                    status_label=row.forecast_label,
                    subtitle=f"Planned {row.planned_label} | Committed {row.committed_label}",
                    supporting_text=f"Actual {row.actual_label} | Exposure {row.exposure_label}",
                    meta_text="Monthly period rollup",
                    can_primary_action=False,
                    can_secondary_action=False,
                    state={},
                )
                for row in snapshot.cashflow
            ),
        )

    def _build_ledger_collection(self, snapshot) -> FinancialsCollectionViewModel:
        return FinancialsCollectionViewModel(
            title="Ledger Trail",
            subtitle="Recent entries that feed the selected project's finance view.",
            empty_state="No ledger rows are available for the selected project.",
            items=tuple(
                FinancialsRecordViewModel(
                    id=f"{index}",
                    title=row.reference_label,
                    status_label=row.amount_label,
                    subtitle=f"{row.source_label} | {row.stage}",
                    supporting_text=f"{row.task_name} | {row.resource_name}",
                    meta_text=(
                        f"{row.occurred_on_label} | "
                        + ("Included in policy" if row.included_in_policy else "Outside policy")
                    ),
                    can_primary_action=False,
                    can_secondary_action=False,
                    state={},
                )
                for index, row in enumerate(snapshot.ledger[:10], start=1)
            ),
        )

    def _build_analytics_collection(
        self,
        *,
        title: str,
        subtitle: str,
        rows,
    ) -> FinancialsCollectionViewModel:
        return FinancialsCollectionViewModel(
            title=title,
            subtitle=subtitle,
            empty_state=f"No {title.lower()} data is available for the selected project.",
            items=tuple(
                FinancialsRecordViewModel(
                    id=f"{row.dimension}:{row.key}",
                    title=row.label,
                    status_label=row.exposure_label,
                    subtitle=f"Planned {row.planned_label} | Forecast {row.forecast_label}",
                    supporting_text=f"Committed {row.committed_label} | Actual {row.actual_label}",
                    meta_text=f"Exposure {row.exposure_label}",
                    can_primary_action=False,
                    can_secondary_action=False,
                    state={},
                )
                for row in rows[:8]
            ),
        )

    @staticmethod
    def _build_cost_state(cost) -> dict[str, object]:
        return {
            "costId": cost.id,
            "projectId": cost.project_id,
            "taskId": cost.task_id or "",
            "description": cost.description,
            "plannedAmount": f"{cost.planned_amount:.2f}",
            "committedAmount": f"{cost.committed_amount:.2f}",
            "actualAmount": f"{cost.actual_amount:.2f}",
            "costType": cost.cost_type,
            "currency": cost.currency_code or "",
            "incurredDate": cost.incurred_date.isoformat() if cost.incurred_date else "",
            "version": cost.version,
        }

    def _to_cost_record_view_model(self, cost) -> FinancialsRecordViewModel:
        return FinancialsRecordViewModel(
            id=cost.id,
            title=cost.description,
            status_label=cost.cost_type_label,
            subtitle=cost.task_name,
            supporting_text=(
                f"Planned {cost.planned_amount_label} | "
                f"Committed {cost.committed_amount_label} | "
                f"Actual {cost.actual_amount_label}"
            ),
            meta_text=f"{cost.incurred_date_label} | {cost.currency_code or 'Default currency'}",
            state=self._build_cost_state(cost),
        )

    @staticmethod
    def _build_empty_state(
        *,
        project_options,
        all_costs,
        filtered_costs,
        selected_project_id: str,
        search_text: str,
        selected_cost_type: str,
    ) -> str:
        if not project_options:
            return "No projects are available yet. Create a project before managing financials."
        if not selected_project_id:
            return "Select a project to review financial controls."
        if filtered_costs:
            return ""
        if not all_costs:
            return "No cost items are available for the selected project."
        if search_text or selected_cost_type != "all":
            return "No cost items match the current filters."
        return "No cost items are available for the selected project."

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
    def _required_float(payload: dict[str, Any], key: str, message: str) -> float:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            raise ValueError(message)
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(message) from exc

    @staticmethod
    def _optional_float(payload: dict[str, Any], key: str, message: str) -> float:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            return 0.0
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(message) from exc

    @staticmethod
    def _optional_int(payload: dict[str, Any], key: str) -> int | None:
        value = payload.get(key)
        if value in (None, ""):
            return None
        return int(value)

    @staticmethod
    def _optional_date(payload: dict[str, Any], key: str) -> date | None:
        raw_value = str(payload.get(key, "") or "").strip()
        if not raw_value:
            return None
        try:
            return date.fromisoformat(raw_value)
        except ValueError as exc:
            raise ValueError("Incurred date must use YYYY-MM-DD.") from exc


__all__ = ["ProjectFinancialsWorkspacePresenter"]
