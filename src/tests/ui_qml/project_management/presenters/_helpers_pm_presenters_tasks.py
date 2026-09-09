import json
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QSettings

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
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


class _FakeTaskService:
    def __init__(self, tasks: list[SimpleNamespace] | None = None) -> None:
        self._tasks = {
            task.id: task
            for task in (tasks or [])
        }
        self._assignments: dict[str, SimpleNamespace] = {}
        self._dependencies: dict[str, SimpleNamespace] = {}
        self._project_resource_lookup: dict[str, str] = {}

    def list_tasks_for_project(self, project_id: str) -> list[SimpleNamespace]:
        return [
            task
            for task in self._tasks.values()
            if task.project_id == project_id
        ]

    def get_task(self, task_id: str) -> SimpleNamespace | None:
        return self._tasks.get(task_id)

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._tasks[task_id]
        task.status = status
        task.version += 1

    def update_progress(
        self,
        task_id: str,
        *,
        percent_complete: float | None = None,
        actual_start: date | None = None,
        actual_end: date | None = None,
        status: TaskStatus | None = None,
        expected_version: int | None = None,
    ) -> SimpleNamespace:
        task = self._tasks[task_id]
        if percent_complete is not None:
            task.percent_complete = float(percent_complete)
        if actual_start is not None:
            task.actual_start = actual_start
        if actual_end is not None:
            task.actual_end = actual_end
        if status is not None:
            task.status = status
        task.version += 1
        return task

    def delete_task(self, task_id: str) -> None:
        del self._tasks[task_id]

    def register_project_resource(self, project_resource_id: str, resource_id: str) -> None:
        self._project_resource_lookup[project_resource_id] = resource_id

    def list_assignments_for_task(self, task_id: str) -> list[SimpleNamespace]:
        return [
            assignment
            for assignment in self._assignments.values()
            if assignment.task_id == task_id
        ]

    def assign_project_resource(
        self,
        *,
        task_id: str,
        project_resource_id: str,
        allocation_percent: float,
    ) -> SimpleNamespace:
        assignment = SimpleNamespace(
            id=f"assign-{len(self._assignments) + 1}",
            task_id=task_id,
            resource_id=self._project_resource_lookup.get(
                project_resource_id,
                project_resource_id,
            ),
            allocation_percent=allocation_percent,
            hours_logged=0.0,
            project_resource_id=project_resource_id,
        )
        self._assignments[assignment.id] = assignment
        return assignment

    def add_dependency(
        self,
        *,
        predecessor_id: str,
        successor_id: str,
        dependency_type: str,
        lag_days: int = 0,
    ) -> SimpleNamespace:
        dependency = SimpleNamespace(
            id=f"dep-{len(self._dependencies) + 1}",
            predecessor_task_id=predecessor_id,
            successor_task_id=successor_id,
            dependency_type=DependencyType(str(dependency_type)),
            lag_days=lag_days,
        )
        self._dependencies[dependency.id] = dependency
        return dependency

    def list_dependencies_for_task(self, task_id: str) -> list[SimpleNamespace]:
        return [
            dependency
            for dependency in self._dependencies.values()
            if dependency.predecessor_task_id == task_id
            or dependency.successor_task_id == task_id
        ]


class _FakeTaskOptionService:
    def __init__(self, tasks_by_project: dict[str, list[SimpleNamespace]]) -> None:
        self._tasks_by_project = tasks_by_project

    def list_tasks_for_project(self, project_id: str) -> list[SimpleNamespace]:
        return list(self._tasks_by_project.get(project_id, []))


def _build_task_record(
    *,
    task_id: str,
    project_id: str,
    name: str,
    description: str,
    status: TaskStatus,
    start_date: date | None,
    end_date: date | None,
    duration_days: int | None,
    priority: int,
    percent_complete: float,
    deadline: date | None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=task_id,
        project_id=project_id,
        name=name,
        description=description,
        status=status,
        start_date=start_date,
        end_date=end_date,
        duration_days=duration_days,
        priority=priority,
        percent_complete=percent_complete,
        actual_start=None,
        actual_end=None,
        deadline=deadline,
        version=1,
    )
