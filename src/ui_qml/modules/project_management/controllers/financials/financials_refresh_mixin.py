from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_financials_baseline_variance_view_models,
    serialize_financials_collection_view_model,
    serialize_financials_commitment_summary_view_model,
    serialize_financials_detail_view_model,
    serialize_financials_forecast_view_model,
    serialize_financials_overview_view_model,
    serialize_selector_options,
    serialize_workspace_view_model,
)


class FinancialsRefreshMixin:
    def _refresh(self) -> None:
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(
                    self._workspace_presenter.build_view_model()
                )
            )
            workspace_state = self._financials_workspace_presenter.build_workspace_state(
                selected_project_id=self._selected_project_id or None,
                budget_line_page=self._budget_line_page,
                rate_line_page=self._rate_line_page,
                planned_cost_line_page=self._planned_cost_line_page,
                configuration_page_size=self._configuration_page_size,
            )
            self._set_overview(
                serialize_financials_overview_view_model(workspace_state.overview)
            )
            self._set_project_options(
                serialize_selector_options(workspace_state.project_options)
            )
            self._set_task_options(
                serialize_selector_options(workspace_state.task_options)
            )
            self._set_manual_actual_options(
                {
                    "currencyCode": workspace_state.manual_actual_options.currency_code,
                    "costCodes": serialize_selector_options(
                        workspace_state.manual_actual_options.cost_codes
                    ),
                    "entryKinds": serialize_selector_options(
                        workspace_state.manual_actual_options.entry_kinds
                    ),
                }
            )
            self._set_selected_project_id(workspace_state.selected_project_id)
            self._set_cashflow(
                serialize_financials_collection_view_model(workspace_state.cashflow)
            )
            self._set_ledger(
                serialize_financials_collection_view_model(workspace_state.ledger)
            )
            self._set_source_analytics(
                serialize_financials_collection_view_model(
                    workspace_state.source_analytics
                )
            )
            self._set_cost_type_analytics(
                serialize_financials_collection_view_model(
                    workspace_state.cost_type_analytics
                )
            )
            self._set_notes(list(workspace_state.notes))
            self._set_empty_state(workspace_state.empty_state)
            self._set_forecast(
                serialize_financials_forecast_view_model(workspace_state.forecast)
            )
            self._set_commitment_summary(
                serialize_financials_commitment_summary_view_model(
                    workspace_state.commitment_summary
                )
            )
            self._set_baseline_variance(
                serialize_financials_baseline_variance_view_models(
                    workspace_state.baseline_variance
                )
            )
            self._set_financial_profile(
                serialize_financials_detail_view_model(workspace_state.financial_profile)
            )
            self._set_budget_versions(
                serialize_financials_collection_view_model(workspace_state.budget_versions)
            )
            self._set_budget_lines(
                serialize_financials_collection_view_model(workspace_state.budget_lines)
            )
            self._set_rate_cards(
                serialize_financials_collection_view_model(workspace_state.rate_cards)
            )
            self._set_rate_lines(
                serialize_financials_collection_view_model(workspace_state.rate_lines)
            )
            self._set_planned_cost_versions(
                serialize_financials_collection_view_model(
                    workspace_state.planned_cost_versions
                )
            )
            self._set_planned_cost_lines(
                serialize_financials_collection_view_model(workspace_state.planned_cost_lines)
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(
            "project",
            "project_tasks",
            "project_costs",
            "project_budget",
            "project_planned_cost",
            scope_code="project_management",
        )


__all__ = ["FinancialsRefreshMixin"]
