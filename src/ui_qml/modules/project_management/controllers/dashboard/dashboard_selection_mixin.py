from __future__ import annotations

import logging

from src.ui_qml.modules.project_management.controllers.dashboard.dashboard_types import (
    DASHBOARD_CONTROLLER_LOGGER_NAME,
)


logger = logging.getLogger(DASHBOARD_CONTROLLER_LOGGER_NAME)


class DashboardSelectionMixin:
    def _select_project_from_qml(self, project_id: str) -> None:
        normalized_id = (project_id or "").strip()
        self._log_selector_call("selectProject", normalized_id)
        if self._is_refreshing:
            logger.debug("PM dashboard selectProject ignored during refresh")
            return
        if normalized_id == self._selected_project_id:
            return
        self._set_selected_project_id(normalized_id)
        self._set_selected_baseline_id("")
        if not self._has_loaded:
            self.load()
            return
        self._refresh_dashboard(source="selectProject")

    def _select_baseline_from_qml(self, baseline_id: str) -> None:
        normalized_id = (baseline_id or "").strip()
        self._log_selector_call("selectBaseline", normalized_id)
        if self._is_refreshing:
            logger.debug("PM dashboard selectBaseline ignored during refresh")
            return
        if normalized_id == self._selected_baseline_id:
            return
        self._set_selected_baseline_id(normalized_id)
        if not self._has_loaded:
            self.load()
            return
        self._refresh_dashboard(source="selectBaseline")

    def _select_period_from_qml(self, period_key: str) -> None:
        normalized_key = (period_key or "").strip()
        self._log_selector_call("selectPeriod", normalized_key)
        if self._is_refreshing:
            logger.debug("PM dashboard selectPeriod ignored during refresh")
            return
        if normalized_key == self._selected_period_key:
            return
        self._set_selected_period_key(normalized_key)
        if not self._has_loaded:
            self.load()
            return
        self._refresh_dashboard(source="selectPeriod")

    def _select_view_from_qml(self, view_key: str) -> None:
        normalized_key = (view_key or "").strip()
        self._log_selector_call("selectView", normalized_key)
        if self._is_refreshing:
            logger.debug("PM dashboard selectView ignored during refresh")
            return
        if normalized_key == self._selected_view_key:
            return
        self._set_selected_view_key(normalized_key)
        self._set_selected_operational_tab_id("")
        if not self._has_loaded:
            self.load()
            return
        self._refresh_dashboard(source="selectView")

    def _select_operational_tab_from_qml(self, tab_id: str) -> None:
        normalized_id = (tab_id or "").strip()
        self._log_selector_call("selectOperationalTab", normalized_id)
        if normalized_id == self._selected_operational_tab_id:
            return
        self._set_selected_operational_tab_id(normalized_id)
        self._set_operational_page(1)
        self._set_selected_operational_row_id("")
        self._apply_operational_table_state()

    def _log_selector_call(self, selector_name: str, selected_value: str) -> None:
        next_count = self._selector_debug_counts.get(selector_name, 0) + 1
        self._selector_debug_counts[selector_name] = next_count
        logger.debug(
            "PM dashboard %s #%s value=%r loaded=%s refreshing=%s",
            selector_name,
            next_count,
            selected_value,
            self._has_loaded,
            self._is_refreshing,
        )


__all__ = ["DashboardSelectionMixin"]
