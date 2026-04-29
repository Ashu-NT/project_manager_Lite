from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementDashboardDesktopApi,
    build_project_management_dashboard_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardMetricViewModel,
    ProjectDashboardOverviewViewModel,
    ProjectDashboardSectionItemViewModel,
    ProjectDashboardSectionViewModel,
    ProjectDashboardSelectorOptionViewModel,
    ProjectDashboardWorkspaceViewModel,
)


class ProjectDashboardWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementDashboardDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_dashboard_desktop_api()

    def build_workspace_state(
        self,
        *,
        project_id: str | None = None,
        baseline_id: str | None = None,
    ) -> ProjectDashboardWorkspaceViewModel:
        snapshot = self._desktop_api.build_snapshot(
            project_id=project_id,
            baseline_id=baseline_id,
        )
        return ProjectDashboardWorkspaceViewModel(
            overview=self._to_overview_view_model(snapshot.overview),
            project_options=tuple(
                ProjectDashboardSelectorOptionViewModel(
                    value=option.value,
                    label=option.label,
                )
                for option in snapshot.project_options
            ),
            selected_project_id=snapshot.selected_project_id,
            baseline_options=tuple(
                ProjectDashboardSelectorOptionViewModel(
                    value=option.value,
                    label=option.label,
                )
                for option in snapshot.baseline_options
            ),
            selected_baseline_id=snapshot.selected_baseline_id,
            sections=tuple(
                ProjectDashboardSectionViewModel(
                    title=section.title,
                    subtitle=section.subtitle,
                    empty_state=section.empty_state,
                    items=tuple(
                        ProjectDashboardSectionItemViewModel(
                            id=item.id,
                            title=item.title,
                            status_label=item.status_label,
                            subtitle=item.subtitle,
                            supporting_text=item.supporting_text,
                            meta_text=item.meta_text,
                            state=dict(item.state),
                        )
                        for item in section.items
                    ),
                )
                for section in snapshot.sections
            ),
            empty_state=snapshot.empty_state,
        )

    @staticmethod
    def _to_overview_view_model(descriptor) -> ProjectDashboardOverviewViewModel:
        return ProjectDashboardOverviewViewModel(
            title=descriptor.title,
            subtitle=descriptor.subtitle,
            metrics=tuple(
                ProjectDashboardMetricViewModel(
                    label=metric.label,
                    value=metric.value,
                    supporting_text=metric.supporting_text,
                )
                for metric in descriptor.metrics
            ),
        )


__all__ = ["ProjectDashboardWorkspacePresenter"]
