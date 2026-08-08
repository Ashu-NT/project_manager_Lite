from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop.projects.builders.resource_builder import (
    list_resources_for_context,
)
from src.core.modules.project_management.api.desktop.scheduling.api import (
    ProjectManagementSchedulingDesktopApi,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.change_impact_builder import (
    build_change_impact,
    compute_schedule_impact,
)
from src.core.modules.project_management.api.desktop.tasks.api import (
    ProjectManagementTasksDesktopApi,
)
from src.core.modules.project_management.api.desktop.tasks.services.access_resolution_service import (
    project_rows_for_task_scope,
)
from src.core.platform.common.exceptions import BusinessRuleError


class _ImpactService:
    def __init__(self) -> None:
        self.has_baseline_values: list[bool] = []

    def analyse(self, **kwargs):
        has_baseline = bool(kwargs["has_approved_baseline"])
        self.has_baseline_values.append(has_baseline)
        return SimpleNamespace(
            max_project_finish_shift_days=1,
            requires_approval=has_baseline,
            affected_tasks=(),
            newly_critical_task_ids=(),
            no_longer_critical_task_ids=(),
        )


def test_da0_characterizes_schedule_impact_baseline_divergence() -> None:
    impact_service = _ImpactService()
    baseline_service = SimpleNamespace(
        get_approved_baseline=lambda _project_id: object(),
    )
    task_service = SimpleNamespace(
        get_task=lambda _task_id: SimpleNamespace(start_date=date(2026, 8, 1)),
    )

    scheduling_result = build_change_impact(
        "project-1",
        "task-1",
        change_impact_service=impact_service,
        baseline_service=baseline_service,
    )
    task_result = compute_schedule_impact(
        "task-1",
        "project-1",
        task_service=task_service,
        schedule_change_impact_service=impact_service,
    )

    assert impact_service.has_baseline_values == [True, False]
    assert scheduling_result is not None and scheduling_result.requires_approval is True
    assert task_result.requires_approval is False


class _ScopedResourceService:
    def __init__(self) -> None:
        self.context_calls: list[str] = []
        self._resource_repo = SimpleNamespace(
            list=lambda: [SimpleNamespace(id="resource-active-org")],
        )
        self._tenant_context_service = SimpleNamespace(
            require_active_organization_id=self._require_active_organization_id,
        )

    def list_resources(self):
        raise BusinessRuleError("Permission denied: project.read", code="PERMISSION_DENIED")

    def _require_active_organization_id(self, *, operation_label: str) -> str:
        self.context_calls.append(operation_label)
        return "organization-1"


def test_da0_characterizes_project_resource_scope_resolution_in_adapter() -> None:
    resource_service = _ScopedResourceService()

    rows = list_resources_for_context(
        "project-1",
        resource_service=resource_service,
        can_fallback_fn=lambda _project_id, _exc: True,
    )

    assert [row.id for row in rows] == ["resource-active-org"]
    assert resource_service.context_calls == ["list project resources"]


def test_da0_characterizes_task_list_silently_omitting_denied_project() -> None:
    api = ProjectManagementTasksDesktopApi(task_service=object())
    api._project_name_by_id = lambda: {
        "project-allowed": "Allowed",
        "project-denied": "Denied",
    }

    def _serialize(project_id: str, _project_name: str):
        if project_id == "project-denied":
            raise BusinessRuleError("Permission denied", code="PERMISSION_DENIED")
        return (SimpleNamespace(id="task-allowed"),)

    api._serialize_project_tasks = _serialize

    assert [row.id for row in api.list_all_tasks()] == ["task-allowed"]


class _TaskScopeSession:
    def project_ids_for(self, permission_code: str) -> set[str]:
        return {"project-task-read"} if permission_code == "task.read" else set()

    def has_permission(self, _permission_code: str) -> bool:
        return False


def test_da0_characterizes_hand_rolled_task_project_permission_fallback() -> None:
    project = SimpleNamespace(
        id="project-task-read",
        name="Task Scoped Project",
        organization_id="organization-1",
    )
    project_service = SimpleNamespace(
        list_projects=lambda: (_ for _ in ()).throw(
            BusinessRuleError("Permission denied: project.read", code="PERMISSION_DENIED")
        ),
        _project_repo=SimpleNamespace(get=lambda project_id: project if project_id == project.id else None),
        _tenant_context_service=SimpleNamespace(
            require_active_organization_id=lambda **_kwargs: "organization-1",
        ),
    )
    task_service = SimpleNamespace(_user_session=_TaskScopeSession())

    rows = project_rows_for_task_scope(
        project_service=project_service,
        task_service=task_service,
    )

    assert [row.id for row in rows] == ["project-task-read"]


def test_da0_characterizes_unpersisted_calendar_placeholder_success() -> None:
    api = ProjectManagementSchedulingDesktopApi()

    unchanged_snapshot = api.update_calendar(
        SimpleNamespace(calendar_id="", working_days=(0, 1, 2, 3, 4), hours_per_day=8.0)
    )
    fabricated_holiday = api.add_holiday(
        SimpleNamespace(calendar_id="", holiday_date=date(2026, 8, 8), name="Founders Day")
    )

    assert unchanged_snapshot.calendar_id == "default"
    assert fabricated_holiday.id == ""
    assert fabricated_holiday.date == date(2026, 8, 8)
