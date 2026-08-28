from __future__ import annotations

import logging
from time import perf_counter

from PySide6.QtCore import Qt

from src.core.shared.events.domain_events import domain_events
from src.ui_qml.modules.project_management.controllers.common import (
    serialize_financials_baseline_variance_view_models,
    serialize_financials_collection_view_model,
    serialize_financials_commitment_summary_view_model,
    serialize_financials_detail_view_model,
    serialize_financials_overview_view_model,
    serialize_selector_options,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.controllers.financials.financials_types import (
    default_collection,
    default_commitment_summary,
    default_detail,
    default_forecast,
    default_overview,
)


logger = logging.getLogger(__name__)


class FinancialsRefreshMixin:
    def _refresh(self) -> None:
        started = perf_counter()
        self._refresh_generation += 1
        generation = self._refresh_generation
        project_id = self._selected_project_id
        destination = self._active_destination
        subsection = self._active_subsection
        success = False
        logger.info(
            "PM financials refresh begin generation=%s project=%r destination=%s subsection=%s",
            generation,
            project_id,
            destination,
            subsection,
        )
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            if not self._workspace_loaded:
                self._set_workspace(
                    serialize_workspace_view_model(
                        self._workspace_presenter.build_view_model()
                    )
                )
                self._workspace_loaded = True
            if not self._shell_loaded:
                shell = self._financials_workspace_presenter.build_shell_state(
                    selected_project_id=self._selected_project_id or None,
                )
                if generation != self._refresh_generation:
                    return
                self._set_project_options(
                    serialize_selector_options(shell.project_options)
                )
                self._set_selected_project_id(shell.selected_project_id)
                self._set_empty_state(shell.empty_state)
                self._shell_loaded = True

            project_id = self._selected_project_id
            destination = self._active_destination
            subsection = self._active_subsection
            state = self._financials_workspace_presenter.build_destination_state(
                destination=destination,
                subsection=subsection,
                selected_project_id=project_id,
                selected_project_label=self._selected_project_label(),
                budget_line_page=self._budget_line_page,
                budget_version_page=self._budget_version_page,
                rate_line_page=self._rate_line_page,
                rate_card_page=self._rate_card_page,
                planned_cost_line_page=self._planned_cost_line_page,
                planned_cost_version_page=self._planned_cost_version_page,
                billing_preparation_page=self._billing_preparation_page,
                configuration_page_size=self._configuration_page_size,
                actual_page=self._actual_page,
                commitment_page=self._commitment_page,
                transaction_page_size=self._transaction_page_size,
                actual_sort_key=self._actual_sort_key,
                actual_sort_direction=self._sort_direction_name(
                    self._actual_sort_direction
                ),
                commitment_sort_key=self._commitment_sort_key,
                commitment_sort_direction=self._sort_direction_name(
                    self._commitment_sort_direction
                ),
                selected_forecast_id=self._selected_forecast_id or None,
                forecast_version_page=self._forecast_version_page,
                forecast_line_page=self._forecast_line_page,
                forecast_version_sort_key=self._forecast_version_sort_key,
                forecast_version_sort_direction=self._sort_direction_name(
                    self._forecast_version_sort_direction
                ),
                forecast_line_sort_key=self._forecast_line_sort_key,
                forecast_line_sort_direction=self._sort_direction_name(
                    self._forecast_line_sort_direction
                ),
                forecast_version_search=self._forecast_version_search,
                forecast_version_status=self._forecast_version_status,
                forecast_generation_mode=self._forecast_generation_mode,
                forecast_line_search=self._forecast_line_search,
                forecast_line_source_type=self._forecast_line_source_type,
                selected_rate_card_id=self._selected_rate_card_id or None,
                rate_card_sort_key=self._rate_card_sort_key,
                rate_card_sort_direction=self._sort_direction_name(
                    self._rate_card_sort_direction
                ),
                rate_line_sort_key=self._rate_line_sort_key,
                rate_line_sort_direction=self._sort_direction_name(
                    self._rate_line_sort_direction
                ),
                rate_card_search=self._rate_card_search,
                rate_card_scope=self._rate_card_scope,
                rate_card_status=self._rate_card_status,
                rate_line_search=self._rate_line_search,
                rate_line_rate_type=self._rate_line_rate_type,
                rate_line_status=self._rate_line_status,
                rate_line_effective_status=self._rate_line_effective_status,
                selected_budget_id=self._selected_budget_id or None,
                budget_version_sort_key=self._budget_version_sort_key,
                budget_version_sort_direction=self._sort_direction_name(
                    self._budget_version_sort_direction
                ),
                budget_line_sort_key=self._budget_line_sort_key,
                budget_line_sort_direction=self._sort_direction_name(
                    self._budget_line_sort_direction
                ),
                selected_planned_cost_version_id=(
                    self._selected_planned_cost_version_id or None
                ),
                planned_cost_version_sort_key=self._planned_cost_version_sort_key,
                planned_cost_version_sort_direction=self._sort_direction_name(
                    self._planned_cost_version_sort_direction
                ),
                planned_cost_line_sort_key=self._planned_cost_line_sort_key,
                planned_cost_line_sort_direction=self._sort_direction_name(
                    self._planned_cost_line_sort_direction
                ),
                selected_change_id=self._selected_change_id or None,
                change_page=self._change_page,
                impact_page=self._impact_page,
                change_sort_key=self._change_sort_key,
                change_sort_direction=self._sort_direction_name(
                    self._change_sort_direction
                ),
                impact_sort_key=self._impact_sort_key,
                impact_sort_direction=self._sort_direction_name(
                    self._impact_sort_direction
                ),
                change_search=self._change_search,
                change_status=self._change_status,
                change_approval_status=self._change_approval_status,
                change_applied_state=self._change_applied_state,
                impact_search=self._impact_search,
                impact_type=self._impact_type,
                impact_applied_state=self._impact_applied_state,
                selected_baseline_id=self._selected_baseline_id or None,
            )
            if (
                generation != self._refresh_generation
                or project_id != self._selected_project_id
                or destination != self._active_destination
                or subsection != self._active_subsection
            ):
                logger.debug(
                    "PM financials stale refresh ignored generation=%s current_generation=%s "
                    "project=%r current_project=%r destination=%s current_destination=%s "
                    "subsection=%s current_subsection=%s",
                    generation,
                    self._refresh_generation,
                    project_id,
                    self._selected_project_id,
                    destination,
                    self._active_destination,
                    subsection,
                    self._active_subsection,
                )
                return
            self._apply_destination_state(destination, subsection, state)
            self._loaded_destination_keys.add((project_id, destination, subsection))
            self._invalidated_destinations.discard(destination)
            success = True
        except Exception as exc:  # pragma: no cover - defensive QML boundary
            logger.exception(
                "PM financials refresh failed generation=%s project=%r "
                "destination=%s subsection=%s",
                generation,
                project_id,
                destination,
                subsection,
            )
            self._set_error_message(str(exc))
        finally:
            if generation == self._refresh_generation:
                self._set_is_loading(False)
                duration_ms = (perf_counter() - started) * 1000
                log_method = logger.warning if duration_ms > 500 else logger.info
                log_method(
                    "PM financials refresh complete generation=%s success=%s "
                    "duration_ms=%.1f project=%r destination=%s subsection=%s",
                    generation,
                    success,
                    duration_ms,
                    project_id,
                    destination,
                    subsection,
                )

    def _apply_destination_state(self, destination: str, subsection: str, state) -> None:
        self._set_empty_state(state.empty_state)
        if destination == "overview":
            self._set_overview(
                serialize_financials_overview_view_model(state.overview)
            )
            return

        if destination == "planning":
            if subsection == "budgets":
                self._set_selected_budget_id(state.selected_budget_id)
                self._set_budget_versions(
                    serialize_financials_collection_view_model(state.budget_versions)
                )
                self._set_budget_lines(
                    serialize_financials_collection_view_model(state.budget_lines)
                )
                self._budget_version_page = state.budget_versions.page
                self._budget_line_page = state.budget_lines.page
                self._configuration_page_size = state.budget_lines.page_size
                self._set_budget_sort_state(
                    version_key=state.budget_version_sort_key,
                    version_direction=state.budget_version_sort_direction,
                    line_key=state.budget_line_sort_key,
                    line_direction=state.budget_line_sort_direction,
                )
            elif subsection == "planned_costs":
                self._set_selected_planned_cost_version_id(
                    state.selected_planned_cost_version_id
                )
                self._set_planned_cost_versions(
                    serialize_financials_collection_view_model(
                        state.planned_cost_versions
                    )
                )
                self._set_planned_cost_lines(
                    serialize_financials_collection_view_model(
                        state.planned_cost_lines
                    )
                )
                self._planned_cost_line_page = state.planned_cost_lines.page
                self._planned_cost_version_page = state.planned_cost_versions.page
                self._configuration_page_size = state.planned_cost_lines.page_size
                self._set_planned_cost_sort_state(
                    version_key=state.planned_cost_version_sort_key,
                    version_direction=state.planned_cost_version_sort_direction,
                    line_key=state.planned_cost_line_sort_key,
                    line_direction=state.planned_cost_line_sort_direction,
                )
            else:
                self._set_selected_forecast_id(state.selected_forecast_id)
                self._set_selected_forecast(
                    serialize_financials_detail_view_model(state.selected_forecast)
                )
                self._set_forecast_versions(
                    serialize_financials_collection_view_model(
                        state.forecast_versions
                    )
                )
                self._set_forecast_lines(
                    serialize_financials_collection_view_model(state.forecast_lines)
                )
                self._forecast_version_page = state.forecast_versions.page
                self._forecast_line_page = state.forecast_lines.page
                self._configuration_page_size = state.forecast_lines.page_size
                self._set_forecast_query_state(state)
            return

        if destination == "costs":
            if subsection == "actuals":
                self._set_task_options(serialize_selector_options(state.task_options))
                self._set_manual_actual_options(
                    {
                        "currencyCode": state.manual_actual_options.currency_code,
                        "costCodes": serialize_selector_options(
                            state.manual_actual_options.cost_codes
                        ),
                        "entryKinds": serialize_selector_options(
                            state.manual_actual_options.entry_kinds
                        ),
                    }
                )
                self._set_ledger(
                    serialize_financials_collection_view_model(state.ledger)
                )
                self._actual_page = state.ledger.page
                self._transaction_page_size = state.ledger.page_size
                self._set_actual_sort_state(
                    state.actual_sort_key,
                    state.actual_sort_direction,
                )
            elif subsection == "commitments":
                self._set_commitment_summary(
                    serialize_financials_commitment_summary_view_model(
                        state.commitment_summary
                    )
                )
                self._set_commitments(
                    serialize_financials_collection_view_model(state.commitments)
                )
                self._commitment_page = state.commitments.page
                self._transaction_page_size = state.commitments.page_size
                self._set_commitment_sort_state(
                    state.commitment_sort_key,
                    state.commitment_sort_direction,
                )
            else:
                self._set_selected_rate_card_id(state.selected_rate_card_id)
                self._set_selected_rate_card(
                    serialize_financials_detail_view_model(state.selected_rate_card)
                )
                self._set_rate_cards(
                    serialize_financials_collection_view_model(state.rate_cards)
                )
                self._set_rate_lines(
                    serialize_financials_collection_view_model(state.rate_lines)
                )
                self._rate_line_page = state.rate_lines.page
                self._rate_card_page = state.rate_cards.page
                self._configuration_page_size = state.rate_lines.page_size
                self._set_rate_query_state(state)
            return

        if destination == "performance":
            if subsection == "variance":
                self._set_baseline_variance(
                    serialize_financials_baseline_variance_view_models(
                        state.baseline_variance
                    )
                )
                self._set_selected_baseline_id(state.selected_baseline_id)
                self._set_baseline_versions(
                    serialize_financials_collection_view_model(
                        state.baseline_versions
                    )
                )
                self._set_variance_basis(
                    serialize_financials_detail_view_model(state.variance_basis)
                )
            elif subsection == "cost_phasing":
                self._set_cashflow(
                    serialize_financials_collection_view_model(state.cashflow)
                )
                self._set_source_analytics(
                    serialize_financials_collection_view_model(
                        state.source_analytics
                    )
                )
                self._set_cost_type_analytics(
                    serialize_financials_collection_view_model(
                        state.cost_type_analytics
                    )
                )
                self._set_notes(list(state.notes))
            else:
                self._set_report_basis(
                    serialize_financials_detail_view_model(state.report_basis)
                )
            return

        if destination == "commercial":
            if subsection == "profitability":
                self._set_commercial_projection(
                    serialize_financials_detail_view_model(
                        state.commercial_projection
                    )
                )
                return
            self._set_billing_profile(
                serialize_financials_detail_view_model(state.billing_profile)
            )
            self._set_billing_schedule(
                serialize_financials_collection_view_model(state.billing_schedule)
            )
            self._set_billing_preparations(
                serialize_financials_collection_view_model(
                    state.billing_preparations
                )
            )
            self._billing_preparation_page = state.billing_preparations.page
            return

        if subsection == "setup":
            self._set_financial_profile(
                serialize_financials_detail_view_model(state.financial_profile)
            )
        elif subsection == "changes":
            self._set_selected_change_id(state.selected_change_id)
            self._set_selected_change(
                serialize_financials_detail_view_model(state.selected_change)
            )
            self._set_financial_changes(
                serialize_financials_collection_view_model(state.financial_changes)
            )
            self._change_page = state.financial_changes.page
            self._impact_page = state.financial_change_impacts.page
            self._set_financial_change_query_state(state)
            self._set_financial_change_impacts(
                serialize_financials_collection_view_model(
                    state.financial_change_impacts
                )
            )
        else:
            self._set_activity(
                serialize_financials_collection_view_model(state.activity)
            )

    def _reset_destination_state(self) -> None:
        self._set_overview(default_overview())
        self._set_task_options([])
        self._set_manual_actual_options(
            {"currencyCode": "", "costCodes": [], "entryKinds": []}
        )
        self._set_cashflow(default_collection())
        self._set_ledger(default_collection())
        self._set_activity(default_collection())
        self._set_source_analytics(default_collection())
        self._set_cost_type_analytics(default_collection())
        self._set_notes([])
        self._set_forecast(default_forecast())
        self._set_selected_forecast_id("")
        self._set_selected_forecast(default_detail())
        self._set_forecast_versions(default_collection())
        self._set_forecast_lines(default_collection())
        self._set_selected_change_id("")
        self._set_selected_change(default_detail())
        self._set_financial_changes(default_collection())
        self._set_financial_change_impacts(default_collection())
        self._set_commitment_summary(default_commitment_summary())
        self._set_commitments(default_collection())
        self._set_baseline_variance([])
        self._set_selected_baseline_id("")
        self._set_baseline_versions(default_collection())
        self._set_variance_basis(default_detail())
        self._set_report_basis(default_detail())
        self._set_financial_profile(default_detail())
        self._set_budget_versions(default_collection())
        self._set_budget_lines(default_collection())
        self._set_selected_budget_id("")
        self._set_rate_cards(default_collection())
        self._set_rate_lines(default_collection())
        self._set_selected_rate_card_id("")
        self._set_selected_rate_card(default_detail())
        self._set_planned_cost_versions(default_collection())
        self._set_planned_cost_lines(default_collection())
        self._set_selected_planned_cost_version_id("")
        self._set_billing_profile(default_detail())
        self._set_billing_schedule(default_collection())
        self._set_billing_preparations(default_collection())
        self._set_commercial_projection(default_detail())
        self._loaded_destination_keys.clear()

    def _selected_project_label(self) -> str:
        return next(
            (
                str(option.get("label", ""))
                for option in self._project_options
                if str(option.get("value", "")) == self._selected_project_id
            ),
            "",
        )

    @staticmethod
    def _sort_direction_name(direction: int) -> str:
        return "desc" if direction == Qt.DescendingOrder.value else "asc"

    def _invalidate_destinations(self, *destinations: str) -> None:
        self._invalidated_destinations.update(destinations)
        self._loaded_destination_keys = {
            key for key in self._loaded_destination_keys if key[1] not in destinations
        }
        if self._active_destination in destinations:
            self._request_domain_refresh()

    def _bind_domain_events(self) -> None:
        def _projects_changed(_payload: object) -> None:
            self._shell_loaded = False
            self._invalidate_destinations(*self._finance_destinations)

        def _tasks_changed(_payload: object) -> None:
            self._invalidate_destinations("planning", "costs", "performance")

        def _budgets_changed(_payload: object) -> None:
            self._invalidate_destinations("overview", "planning", "performance")

        def _planned_costs_changed(_payload: object) -> None:
            self._invalidate_destinations("planning", "performance")

        def _billing_changed(_payload: object) -> None:
            self._invalidate_destinations("commercial")

        subscriptions = (
            (domain_events.project_changed, _projects_changed),
            (domain_events.tasks_changed, _tasks_changed),
            (domain_events.budgets_changed, _budgets_changed),
            (domain_events.planned_costs_changed, _planned_costs_changed),
            (domain_events.billing_preparations_changed, _billing_changed),
        )
        for signal, callback in subscriptions:
            self._subscribe_domain_signal(signal, callback)


__all__ = ["FinancialsRefreshMixin"]
