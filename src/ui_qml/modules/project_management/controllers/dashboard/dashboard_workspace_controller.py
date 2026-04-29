from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    serialize_dashboard_overview_view_model,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectDashboardPresenter,
    ProjectManagementWorkspacePresenter,
)


class ProjectManagementDashboardWorkspaceController(
    ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()

    def __init__(
        self,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        dashboard_presenter: ProjectDashboardPresenter | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter(
            "project_management.dashboard"
        )
        self._dashboard_presenter = dashboard_presenter or ProjectDashboardPresenter()
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

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
            self._set_overview(
                serialize_dashboard_overview_view_model(
                    self._dashboard_presenter.build_empty_overview()
                )
            )
            self._set_empty_state("Select a project to see schedule and cost health.")
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()


__all__ = ["ProjectManagementDashboardWorkspaceController"]
