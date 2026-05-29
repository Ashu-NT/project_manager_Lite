from __future__ import annotations

from math import ceil

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.shared.models.data_table_model import DynamicTableModel
from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    serialize_dashboard_activity_feed_view_model,
    serialize_dashboard_chart_view_models,
    serialize_dashboard_health_card_view_models,
    serialize_dashboard_operational_tab_view_models,
    serialize_dashboard_operational_table_view_models,
    serialize_dashboard_overview_view_model,
    serialize_dashboard_panel_view_models,
    serialize_dashboard_section_view_models,
    serialize_selector_options,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectDashboardWorkspacePresenter,
    ProjectManagementWorkspacePresenter,
)

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
class ProjectManagementDashboardWorkspaceController(
    ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()
    projectOptionsChanged = Signal()
    selectedProjectIdChanged = Signal()
    baselineOptionsChanged = Signal()
    selectedBaselineIdChanged = Signal()
    periodOptionsChanged = Signal()
    selectedPeriodKeyChanged = Signal()
    viewOptionsChanged = Signal()
    selectedViewKeyChanged = Signal()
    healthCardsChanged = Signal()
    operationalTabsChanged = Signal()
    selectedOperationalTabIdChanged = Signal()
    operationalTableChanged = Signal()
    operationalSearchTextChanged = Signal()
    operationalPageChanged = Signal()
    operationalPageSizeChanged = Signal()
    operationalTotalCountChanged = Signal()
    selectedOperationalRowIdChanged = Signal()
    activityFeedChanged = Signal()
    panelsChanged = Signal()
    chartsChanged = Signal()
    sectionsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        dashboard_workspace_presenter: ProjectDashboardWorkspacePresenter | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter(
            "project_management.dashboard"
        )
        self._dashboard_workspace_presenter = (
            dashboard_workspace_presenter or ProjectDashboardWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._project_options: list[dict[str, str]] = []
        self._selected_project_id = ""
        self._baseline_options: list[dict[str, str]] = []
        self._selected_baseline_id = ""
        self._period_options: list[dict[str, str]] = []
        self._selected_period_key = ""
        self._view_options: list[dict[str, str]] = []
        self._selected_view_key = ""
        self._health_cards: list[dict[str, object]] = []
        self._operational_tabs: list[dict[str, object]] = []
        self._selected_operational_tab_id = ""
        self._operational_table_model = DynamicTableModel(self)
        self._operational_table: dict[str, object] = self._empty_operational_table()
        self._operational_search_text = ""
        self._operational_page = 1
        self._operational_page_size = 25
        self._operational_total_count = 0
        self._selected_operational_row_id = ""
        self._activity_feed: dict[str, object] = {
            "title": "Recent Activity",
            "subtitle": "",
            "emptyState": "No recent activity is available yet.",
            "items": [],
        }
        self._panels: list[dict[str, object]] = []
        self._charts: list[dict[str, object]] = []
        self._sections: list[dict[str, object]] = []
        self._raw_operational_tables: list[dict[str, object]] = []
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=projectOptionsChanged)
    def projectOptions(self) -> list[dict[str, str]]:
        return self._project_options

    @Property(str, notify=selectedProjectIdChanged)
    def selectedProjectId(self) -> str:
        return self._selected_project_id

    @Property("QVariantList", notify=baselineOptionsChanged)
    def baselineOptions(self) -> list[dict[str, str]]:
        return self._baseline_options

    @Property(str, notify=selectedBaselineIdChanged)
    def selectedBaselineId(self) -> str:
        return self._selected_baseline_id

    @Property("QVariantList", notify=periodOptionsChanged)
    def periodOptions(self) -> list[dict[str, str]]:
        return self._period_options

    @Property(str, notify=selectedPeriodKeyChanged)
    def selectedPeriodKey(self) -> str:
        return self._selected_period_key

    @Property("QVariantList", notify=viewOptionsChanged)
    def viewOptions(self) -> list[dict[str, str]]:
        return self._view_options

    @Property(str, notify=selectedViewKeyChanged)
    def selectedViewKey(self) -> str:
        return self._selected_view_key

    @Property("QVariantList", notify=healthCardsChanged)
    def healthCards(self) -> list[dict[str, object]]:
        return self._health_cards

    @Property("QVariantList", notify=operationalTabsChanged)
    def operationalTabs(self) -> list[dict[str, object]]:
        return self._operational_tabs

    @Property(str, notify=selectedOperationalTabIdChanged)
    def selectedOperationalTabId(self) -> str:
        return self._selected_operational_tab_id

    @Property("QVariantMap", notify=operationalTableChanged)
    def operationalTable(self) -> dict[str, object]:
        return self._operational_table

    @Property(QObject, constant=True)
    def operationalTableModel(self) -> DynamicTableModel:
        return self._operational_table_model

    @Property(str, notify=operationalSearchTextChanged)
    def operationalSearchText(self) -> str:
        return self._operational_search_text

    @Property(int, notify=operationalPageChanged)
    def operationalPage(self) -> int:
        return self._operational_page

    @Property(int, notify=operationalPageSizeChanged)
    def operationalPageSize(self) -> int:
        return self._operational_page_size

    @Property(int, notify=operationalTotalCountChanged)
    def operationalTotalCount(self) -> int:
        return self._operational_total_count

    @Property(str, notify=selectedOperationalRowIdChanged)
    def selectedOperationalRowId(self) -> str:
        return self._selected_operational_row_id

    @Property("QVariantMap", notify=activityFeedChanged)
    def activityFeed(self) -> dict[str, object]:
        return self._activity_feed

    @Property("QVariantList", notify=panelsChanged)
    def panels(self) -> list[dict[str, object]]:
        return self._panels

    @Property("QVariantList", notify=chartsChanged)
    def charts(self) -> list[dict[str, object]]:
        return self._charts

    @Property("QVariantList", notify=sectionsChanged)
    def sections(self) -> list[dict[str, object]]:
        return self._sections

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(
                    self._workspace_presenter.build_view_model()
                )
            )
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
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(str)
    def selectProject(self, project_id: str) -> None:
        normalized_id = (project_id or "").strip()
        if normalized_id == self._selected_project_id:
            return
        self._set_selected_project_id(normalized_id)
        self._set_selected_baseline_id("")
        self.refresh()

    @Slot(str)
    def selectBaseline(self, baseline_id: str) -> None:
        normalized_id = (baseline_id or "").strip()
        if normalized_id == self._selected_baseline_id:
            return
        self._set_selected_baseline_id(normalized_id)
        self.refresh()

    @Slot(str)
    def selectPeriod(self, period_key: str) -> None:
        normalized_key = (period_key or "").strip()
        if normalized_key == self._selected_period_key:
            return
        self._set_selected_period_key(normalized_key)
        self.refresh()

    @Slot(str)
    def selectView(self, view_key: str) -> None:
        normalized_key = (view_key or "").strip()
        if normalized_key == self._selected_view_key:
            return
        self._set_selected_view_key(normalized_key)
        self._set_selected_operational_tab_id("")
        self.refresh()

    @Slot(str)
    def selectOperationalTab(self, tab_id: str) -> None:
        normalized_id = (tab_id or "").strip()
        if normalized_id == self._selected_operational_tab_id:
            return
        self._set_selected_operational_tab_id(normalized_id)
        self._set_operational_page(1)
        self._set_selected_operational_row_id("")
        self._apply_operational_table_state()

    @Slot(str)
    def setOperationalSearchText(self, search_text: str) -> None:
        normalized_text = (search_text or "").strip()
        if normalized_text == self._operational_search_text:
            return
        self._set_operational_search_text(normalized_text)
        self._set_operational_page(1)
        self._apply_operational_table_state()

    @Slot(int)
    def setOperationalPage(self, page: int) -> None:
        requested_page = max(1, int(page))
        if requested_page == self._operational_page:
            return
        self._set_operational_page(requested_page)
        self._apply_operational_table_state()

    @Slot(int)
    def setOperationalPageSize(self, page_size: int) -> None:
        requested_page_size = max(1, int(page_size))
        if requested_page_size == self._operational_page_size:
            return
        self._set_operational_page_size(requested_page_size)
        self._set_operational_page(1)
        self._apply_operational_table_state()

    @Slot(str)
    def selectOperationalRow(self, row_id: str) -> None:
        self._set_selected_operational_row_id((row_id or "").strip())

    @Slot(result="QVariantMap")
    def exportDashboard(self) -> dict[str, object]:
        message = "Export is not available here. Open the Reports section to generate dashboard summaries and project health exports."
        self._set_error_message("")
        self._set_feedback_message(message)
        return {"ok": True, "message": message}

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

    def _default_operational_tab_id(
        self,
        selected_view_key: str,
        tables: list[dict[str, object]],
    ) -> str:
        available_ids = [
            str(table.get("id", "") or "")
            for table in tables
            if str(table.get("id", "") or "")
        ]
        preferred_by_view = {
            "executive": "delayed_tasks",
            "pmo": "pending_approvals",
            "project_manager": "delayed_tasks",
            "resource_manager": "resource_overloads",
            "financial": "budget_variances",
        }
        preferred = preferred_by_view.get(selected_view_key, "")
        if preferred in available_ids:
            return preferred
        return available_ids[0] if available_ids else ""

    def _current_operational_table_source(self) -> dict[str, object]:
        selected_id = self._selected_operational_tab_id
        for table in self._raw_operational_tables:
            if str(table.get("id", "") or "") == selected_id:
                return table
        return self._raw_operational_tables[0] if self._raw_operational_tables else self._empty_operational_table()

    def _apply_operational_table_state(self) -> None:
        table = self._current_operational_table_source()
        all_rows = list(table.get("rows", []) or [])
        filtered_rows = self._filter_operational_rows(
            rows=all_rows,
            search_text=self._operational_search_text,
        )
        total_count = len(filtered_rows)
        self._set_operational_total_count(total_count)
        page_size = max(1, self._operational_page_size)
        total_pages = max(1, ceil(total_count / page_size)) if total_count else 1
        if self._operational_page > total_pages:
            self._set_operational_page(total_pages)
        page = max(1, self._operational_page)
        start_index = (page - 1) * page_size
        page_rows = filtered_rows[start_index : start_index + page_size]
        visible_row_ids = {str(row.get("id", "") or "") for row in page_rows}
        if self._selected_operational_row_id and self._selected_operational_row_id not in visible_row_ids:
            self._set_selected_operational_row_id("")
        self._set_operational_table(
            {
                "id": table.get("id", ""),
                "title": table.get("title", ""),
                "subtitle": table.get("subtitle", ""),
                "emptyState": table.get("emptyState", ""),
                "columns": list(table.get("columns", []) or []),
                "rows": page_rows,
            }
        )

    @staticmethod
    def _filter_operational_rows(
        *,
        rows: list[dict[str, object]],
        search_text: str,
    ) -> list[dict[str, object]]:
        normalized = search_text.strip().lower()
        if not normalized:
            return rows
        filtered: list[dict[str, object]] = []
        for row in rows:
            haystacks = [
                str(value or "").lower()
                for key, value in row.items()
                if key not in {"state", "routeId"}
            ]
            if any(normalized in haystack for haystack in haystacks):
                filtered.append(row)
        return filtered

    @staticmethod
    def _empty_operational_table() -> dict[str, object]:
        return {
            "id": "",
            "title": "",
            "subtitle": "",
            "emptyState": "No dashboard rows are available yet.",
            "columns": [],
            "rows": [],
        }

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_project_options(self, project_options: list[dict[str, str]]) -> None:
        if project_options == self._project_options:
            return
        self._project_options = project_options
        self.projectOptionsChanged.emit()

    def _set_selected_project_id(self, selected_project_id: str) -> None:
        if selected_project_id == self._selected_project_id:
            return
        self._selected_project_id = selected_project_id
        self.selectedProjectIdChanged.emit()

    def _set_baseline_options(self, baseline_options: list[dict[str, str]]) -> None:
        if baseline_options == self._baseline_options:
            return
        self._baseline_options = baseline_options
        self.baselineOptionsChanged.emit()

    def _set_selected_baseline_id(self, selected_baseline_id: str) -> None:
        if selected_baseline_id == self._selected_baseline_id:
            return
        self._selected_baseline_id = selected_baseline_id
        self.selectedBaselineIdChanged.emit()

    def _set_period_options(self, period_options: list[dict[str, str]]) -> None:
        if period_options == self._period_options:
            return
        self._period_options = period_options
        self.periodOptionsChanged.emit()

    def _set_selected_period_key(self, selected_period_key: str) -> None:
        if selected_period_key == self._selected_period_key:
            return
        self._selected_period_key = selected_period_key
        self.selectedPeriodKeyChanged.emit()

    def _set_view_options(self, view_options: list[dict[str, str]]) -> None:
        if view_options == self._view_options:
            return
        self._view_options = view_options
        self.viewOptionsChanged.emit()

    def _set_selected_view_key(self, selected_view_key: str) -> None:
        if selected_view_key == self._selected_view_key:
            return
        self._selected_view_key = selected_view_key
        self.selectedViewKeyChanged.emit()

    def _set_health_cards(self, health_cards: list[dict[str, object]]) -> None:
        if health_cards == self._health_cards:
            return
        self._health_cards = health_cards
        self.healthCardsChanged.emit()

    def _set_operational_tabs(self, operational_tabs: list[dict[str, object]]) -> None:
        if operational_tabs == self._operational_tabs:
            return
        self._operational_tabs = operational_tabs
        self.operationalTabsChanged.emit()

    def _set_selected_operational_tab_id(self, selected_operational_tab_id: str) -> None:
        if selected_operational_tab_id == self._selected_operational_tab_id:
            return
        self._selected_operational_tab_id = selected_operational_tab_id
        self.selectedOperationalTabIdChanged.emit()

    def _set_operational_table(self, operational_table: dict[str, object]) -> None:
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

    def _set_activity_feed(self, activity_feed: dict[str, object]) -> None:
        if activity_feed == self._activity_feed:
            return
        self._activity_feed = activity_feed
        self.activityFeedChanged.emit()

    def _set_panels(self, panels: list[dict[str, object]]) -> None:
        if panels == self._panels:
            return
        self._panels = panels
        self.panelsChanged.emit()

    def _set_charts(self, charts: list[dict[str, object]]) -> None:
        if charts == self._charts:
            return
        self._charts = charts
        self.chartsChanged.emit()

    def _set_sections(self, sections: list[dict[str, object]]) -> None:
        if sections == self._sections:
            return
        self._sections = sections
        self.sectionsChanged.emit()


__all__ = ["ProjectManagementDashboardWorkspaceController"]
