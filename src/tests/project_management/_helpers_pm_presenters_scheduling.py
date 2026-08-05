import json
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QSettings

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementTaskViewStore,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectDashboardPresenter,
    ProjectFinancialsWorkspacePresenter,
    build_project_management_workspace_presenters,
)
from src.ui_qml.modules.project_management.routes import build_project_management_routes
from src.core.modules.project_management.api.desktop import (
    build_project_management_collaboration_desktop_api,
    build_project_management_dashboard_desktop_api,
    build_project_management_financials_desktop_api,
    build_project_management_projects_desktop_api,
    build_project_management_register_desktop_api,
    build_project_management_resources_desktop_api,
    build_project_management_scheduling_desktop_api,
    build_project_management_tasks_desktop_api,
)
from src.application.runtime import build_desktop_api_registry
from src.core.platform.api.desktop.approval.models.approval import ApprovalRequestDto
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.domain.approval import ApprovalStatus
from src.core.modules.project_management.domain.enums import (
    CostType,
    DependencyType,
    ProjectStatus,
    TaskStatus,
    WorkerType,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.platform.domain.master_data.documents import DocumentStorageKind
from src.tests.ui_runtime_helpers import wait_until
from src.ui_qml.modules.project_management.presenters.collaboration import (
    ProjectCollaborationWorkspacePresenter,
)


class _FakeSchedulingEngine:
    def __init__(self, schedules: dict[str, list[SimpleNamespace]]) -> None:
        self._schedules = schedules

    def recalculate_project_schedule(
        self,
        project_id: str,
        *,
        persist: bool = True,
    ) -> dict[str, SimpleNamespace]:
        return {
            item.task.id: item
            for item in self._schedules.get(project_id, [])
        }


class _FakeWorkCalendarService:
    def get_calendar(self) -> SimpleNamespace:
        return SimpleNamespace(
            working_days={0, 1, 2, 3, 4},
            hours_per_day=8.0,
        )

    def list_holidays(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                id="holiday-1",
                date=date(2026, 5, 1),
                name="Labor Day",
            )
        ]


class _FakeWorkCalendarEngine:
    def add_working_days(self, start_date: date, working_days: int) -> date:
        return date.fromordinal(start_date.toordinal() + working_days)

    def is_working_day(self, target_date: date) -> bool:
        return target_date.weekday() < 5


class _FakeBaselineService:
    def __init__(self, baselines_by_project: dict[str, list[SimpleNamespace]]) -> None:
        self._baselines_by_project = baselines_by_project

    def list_baselines(self, project_id: str) -> list[SimpleNamespace]:
        return list(self._baselines_by_project.get(project_id, []))


class _FakeReportingService:
    def __init__(self, rows_by_key: dict[tuple[str, str, str, bool], list[SimpleNamespace]]) -> None:
        self._rows_by_key = rows_by_key

    def compare_baselines(
        self,
        *,
        project_id: str,
        baseline_a_id: str,
        baseline_b_id: str,
        include_unchanged: bool = False,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            rows=list(
                self._rows_by_key.get(
                    (project_id, baseline_a_id, baseline_b_id, include_unchanged),
                    [],
                )
            )
        )


def _build_schedule_record(
    *,
    task_id: str,
    project_id: str,
    name: str,
    status: TaskStatus,
    start_date: date | None,
    finish_date: date | None,
    latest_start: date | None,
    latest_finish: date | None,
    total_float_days: int | None,
    is_critical: bool,
    deadline: date | None,
    late_by_days: int | None,
    percent_complete: float,
) -> SimpleNamespace:
    return SimpleNamespace(
        task=SimpleNamespace(
            id=task_id,
            project_id=project_id,
            name=name,
            status=status,
            percent_complete=percent_complete,
        ),
        earliest_start=start_date,
        earliest_finish=finish_date,
        latest_start=latest_start,
        latest_finish=latest_finish,
        total_float_days=total_float_days,
        is_critical=is_critical,
        deadline=deadline,
        late_by_days=late_by_days,
    )
