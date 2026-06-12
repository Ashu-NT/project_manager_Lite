from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.dashboard.dashboard_types import (
    DashboardMap,
    DashboardObjectList,
    DashboardOptionList,
)


class DashboardStateMixin:
    def _set_overview(self, overview: DashboardMap) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_has_loaded(self, value: bool) -> None:
        if value == self._has_loaded:
            return
        self._has_loaded = value
        self.hasLoadedChanged.emit()

    def _set_project_options(self, project_options: DashboardOptionList) -> None:
        if project_options == self._project_options:
            return
        self._project_options = project_options
        self.projectOptionsChanged.emit()

    def _set_selected_project_id(self, selected_project_id: str) -> None:
        if selected_project_id == self._selected_project_id:
            return
        self._selected_project_id = selected_project_id
        self.selectedProjectIdChanged.emit()

    def _set_baseline_options(self, baseline_options: DashboardOptionList) -> None:
        if baseline_options == self._baseline_options:
            return
        self._baseline_options = baseline_options
        self.baselineOptionsChanged.emit()

    def _set_selected_baseline_id(self, selected_baseline_id: str) -> None:
        if selected_baseline_id == self._selected_baseline_id:
            return
        self._selected_baseline_id = selected_baseline_id
        self.selectedBaselineIdChanged.emit()

    def _set_period_options(self, period_options: DashboardOptionList) -> None:
        if period_options == self._period_options:
            return
        self._period_options = period_options
        self.periodOptionsChanged.emit()

    def _set_selected_period_key(self, selected_period_key: str) -> None:
        if selected_period_key == self._selected_period_key:
            return
        self._selected_period_key = selected_period_key
        self.selectedPeriodKeyChanged.emit()

    def _set_view_options(self, view_options: DashboardOptionList) -> None:
        if view_options == self._view_options:
            return
        self._view_options = view_options
        self.viewOptionsChanged.emit()

    def _set_selected_view_key(self, selected_view_key: str) -> None:
        if selected_view_key == self._selected_view_key:
            return
        self._selected_view_key = selected_view_key
        self.selectedViewKeyChanged.emit()

    def _set_health_cards(self, health_cards: DashboardObjectList) -> None:
        if health_cards == self._health_cards:
            return
        self._health_cards = health_cards
        self.healthCardsChanged.emit()

    def _set_operational_tabs(self, operational_tabs: DashboardObjectList) -> None:
        if operational_tabs == self._operational_tabs:
            return
        self._operational_tabs = operational_tabs
        self.operationalTabsChanged.emit()

    def _set_selected_operational_tab_id(self, selected_operational_tab_id: str) -> None:
        if selected_operational_tab_id == self._selected_operational_tab_id:
            return
        self._selected_operational_tab_id = selected_operational_tab_id
        self.selectedOperationalTabIdChanged.emit()

    def _set_operational_table(self, operational_table: DashboardMap) -> None:
        if operational_table == self._operational_table:
            return
        self._operational_table = operational_table
        self._operational_table_model.set_rows(operational_table.get("rows", []))
        self.operationalTableChanged.emit()

    def _set_operational_search_text(self, operational_search_text: str) -> None:
        if operational_search_text == self._operational_search_text:
            return
        self._operational_search_text = operational_search_text
        self.operationalSearchTextChanged.emit()

    def _set_operational_page(self, operational_page: int) -> None:
        if operational_page == self._operational_page:
            return
        self._operational_page = operational_page
        self.operationalPageChanged.emit()

    def _set_operational_page_size(self, operational_page_size: int) -> None:
        if operational_page_size == self._operational_page_size:
            return
        self._operational_page_size = operational_page_size
        self.operationalPageSizeChanged.emit()

    def _set_operational_total_count(self, operational_total_count: int) -> None:
        if operational_total_count == self._operational_total_count:
            return
        self._operational_total_count = operational_total_count
        self.operationalTotalCountChanged.emit()

    def _set_selected_operational_row_id(self, selected_operational_row_id: str) -> None:
        if selected_operational_row_id == self._selected_operational_row_id:
            return
        self._selected_operational_row_id = selected_operational_row_id
        self.selectedOperationalRowIdChanged.emit()

    def _set_activity_feed(self, activity_feed: DashboardMap) -> None:
        if activity_feed == self._activity_feed:
            return
        self._activity_feed = activity_feed
        self.activityFeedChanged.emit()

    def _set_panels(self, panels: DashboardObjectList) -> None:
        if panels == self._panels:
            return
        self._panels = panels
        self.panelsChanged.emit()

    def _set_charts(self, charts: DashboardObjectList) -> None:
        if charts == self._charts:
            return
        self._charts = charts
        self.chartsChanged.emit()

    def _set_sections(self, sections: DashboardObjectList) -> None:
        if sections == self._sections:
            return
        self._sections = sections
        self.sectionsChanged.emit()


__all__ = ["DashboardStateMixin"]
