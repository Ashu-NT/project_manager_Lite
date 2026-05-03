from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_dashboard_chart_view_models,
    ProjectManagementWorkspaceControllerBase,
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


class ProjectManagementDashboardWorkspaceController(
    ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()
    projectOptionsChanged = Signal()
    selectedProjectIdChanged = Signal()
    baselineOptionsChanged = Signal()
    selectedBaselineIdChanged = Signal()
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
        self._panels: list[dict[str, object]] = []
        self._charts: list[dict[str, object]] = []
        self._sections: list[dict[str, object]] = []
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

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(
            "project",
            "project_tasks",
            "project_baseline",
            "resource",
            "project_costs",
            "register_scope",
            "portfolio_entity",
            scope_code="project_management",
        )

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
