from __future__ import annotations

import logging
from time import perf_counter

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_dashboard_activity_feed_view_model,
    serialize_dashboard_chart_view_models,
    serialize_dashboard_health_card_view_models,
    serialize_dashboard_operational_tab_view_models,
    serialize_dashboard_operational_table_view_models,
    serialize_dashboard_overview_view_model,
    serialize_dashboard_panel_view_models,
    serialize_dashboard_section_view_models,
    serialize_selector_options,
)
from src.ui_qml.modules.project_management.controllers.dashboard.dashboard_types import (
    DASHBOARD_CONTROLLER_LOGGER_NAME,
)


logger = logging.getLogger(DASHBOARD_CONTROLLER_LOGGER_NAME)


class DashboardRefreshMixin:
    def _load_dashboard(self) -> None:
        if self._has_loaded:
            logger.debug("PM dashboard load skipped: already loaded")
            return
        if self._is_refreshing:
            logger.debug("PM dashboard load skipped: refresh already in progress")
            return
        self._load_count += 1
        logger.debug("PM dashboard load #%s", self._load_count)
        self._refresh_dashboard(source="load", mark_loaded=True)

    def _refresh_dashboard_from_qml(self) -> None:
        if not self._has_loaded:
            logger.debug("PM dashboard refresh requested before load; delegating to load()")
            self.load()
            return
        self._refresh_dashboard(source="refresh")

    def _refresh_dashboard(self, *, source: str, mark_loaded: bool = False) -> None:
        if self._is_refreshing:
            logger.debug(
                "PM dashboard refresh skipped: source=%s already refreshing",
                source,
            )
            return
        self._is_refreshing = True
        self._refresh_count += 1
        started = perf_counter()
        logger.debug(
            "PM dashboard refresh #%s source=%s project=%r baseline=%r period=%r view=%r",
            self._refresh_count,
            source,
            self._selected_project_id,
            self._selected_baseline_id,
            self._selected_period_key,
            self._selected_view_key,
        )
        self._set_is_loading(True)
        loaded_successfully = False
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            workspace_state = self._dashboard_workspace_presenter.build_workspace_state(
                project_id=self._selected_project_id or None,
                baseline_id=self._selected_baseline_id or None,
                period_key=self._selected_period_key or None,
                view_key=self._selected_view_key or None,
            )
            self._set_overview(
                serialize_dashboard_overview_view_model(workspace_state.overview)
            )
            self._set_project_options(
                serialize_selector_options(workspace_state.project_options)
            )
            self._set_selected_project_id(workspace_state.selected_project_id)
            self._set_baseline_options(
                serialize_selector_options(workspace_state.baseline_options)
            )
            self._set_selected_baseline_id(workspace_state.selected_baseline_id)
            self._set_period_options(
                serialize_selector_options(workspace_state.period_options)
            )
            self._set_selected_period_key(workspace_state.selected_period_key)
            self._set_view_options(
                serialize_selector_options(workspace_state.view_options)
            )
            self._set_selected_view_key(workspace_state.selected_view_key)
            self._set_health_cards(
                serialize_dashboard_health_card_view_models(
                    workspace_state.health_cards
                )
            )
            serialized_tables = serialize_dashboard_operational_table_view_models(
                workspace_state.operational_tables
            )
            self._raw_operational_tables = serialized_tables
            self._set_operational_tabs(
                serialize_dashboard_operational_tab_view_models(
                    workspace_state.operational_tabs
                )
            )
            next_tab_id = self._selected_operational_tab_id
            available_tab_ids = {
                str(table.get("id", "") or "") for table in serialized_tables
            }
            if next_tab_id not in available_tab_ids:
                next_tab_id = self._default_operational_tab_id(
                    self._selected_view_key,
                    serialized_tables,
                )
            self._set_selected_operational_tab_id(next_tab_id)
            self._set_activity_feed(
                serialize_dashboard_activity_feed_view_model(
                    workspace_state.activity_feed
                )
            )
            self._set_panels(
                serialize_dashboard_panel_view_models(workspace_state.panels)
            )
            self._set_charts(
                serialize_dashboard_chart_view_models(workspace_state.charts)
            )
            self._set_sections(
                serialize_dashboard_section_view_models(workspace_state.sections)
            )
            self._set_empty_state(workspace_state.empty_state)
            self._apply_operational_table_state()
            loaded_successfully = True
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception(
                "PM dashboard refresh failed source=%s project=%r baseline=%r period=%r view=%r",
                source,
                self._selected_project_id,
                self._selected_baseline_id,
                self._selected_period_key,
                self._selected_view_key,
            )
            self._set_error_message(str(exc))
        finally:
            duration_ms = (perf_counter() - started) * 1000
            row_count = int(self._operational_table.get("rowCount", 0) or 0)
            log_method = logger.warning if duration_ms > 500 else logger.info
            log_method(
                "PM dashboard refresh complete source=%s success=%s duration_ms=%.1f project=%r baseline=%r period=%r view=%r operational_tab=%r row_count=%s",
                source,
                loaded_successfully,
                duration_ms,
                self._selected_project_id,
                self._selected_baseline_id,
                self._selected_period_key,
                self._selected_view_key,
                self._selected_operational_tab_id,
                row_count,
            )
            if mark_loaded and loaded_successfully:
                self._set_has_loaded(True)
            self._is_refreshing = False
            self._set_is_loading(False)

    def _request_domain_refresh(self) -> None:
        if not self._has_loaded:
            logger.debug("PM dashboard domain refresh ignored before initial load")
            return
        super()._request_domain_refresh()

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(
            "project",
            "project_tasks",
            "project_baseline",
            "resource",
            "project_costs",
            "register_scope",
            "portfolio_entity",
            "task_collaboration",
            scope_code="project_management",
        )
        self._subscribe_domain_change(
            "approval_request",
            scope_code="platform",
        )


__all__ = ["DashboardRefreshMixin"]
