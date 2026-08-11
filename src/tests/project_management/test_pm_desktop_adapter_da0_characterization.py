from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop.projects.builders.resource_builder import (
    list_resources_for_context,
)
from src.core.modules.project_management.api.desktop.projects.serializers.resource_serializer import (
    serialize_project_resource,
)
from src.core.modules.project_management.api.desktop.resources.api import (
    ProjectManagementResourcesDesktopApi,
)
from src.core.modules.project_management.api.desktop.resources.builders.assignment_builder import (
    build_resource_assignments,
)
from src.core.modules.project_management.api.desktop.resources.commands.resource_commands import (
    ResourceUpdateCommand,
)
from src.core.modules.project_management.api.desktop.scheduling.api import (
    ProjectManagementSchedulingDesktopApi,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.change_impact_builder import (
    build_change_impact,
)
from src.core.modules.project_management.api.desktop.tasks.api import (
    ProjectManagementTasksDesktopApi,
)
from src.core.modules.project_management.api.desktop.tasks.builders.assignment_preview_builder import (
    build_assignment_preview,
)
from src.core.modules.project_management.api.desktop.tasks.builders.resource_options_builder import (
    build_project_resource_options,
)
from src.core.modules.project_management.api.desktop.tasks.services.access_resolution_service import (
    project_rows_for_task_scope,
)
from src.core.modules.project_management.api.desktop.dashboard.builders.chart_builder import (
    _build_resource_chart,
)
from src.core.modules.project_management.api.desktop.dashboard.builders.operational_table_builder import (
    _build_high_risks_table,
    _build_resource_overloads_table,
)
from src.core.modules.project_management.api.desktop.dashboard.builders.overview_builder import (
    overloaded_resource_count,
)
from src.core.modules.project_management.api.desktop.dashboard.builders.panel_builder import (
    _build_resource_overload_panel,
)
from src.core.modules.project_management.api.desktop.register.builders.entry_list_builder import (
    build_entry_list,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.modules.project_management.infrastructure.reporting.models.report_models import (
    ResourceLoadRow,
)
from src.core.platform.domain.security.auth.session import UserSessionPrincipal


class _ImpactService:
    def __init__(self) -> None:
        self.has_baseline_values: list[bool] = []

    def analyse(self, **kwargs):
        self.has_baseline_values.append(True)
        return SimpleNamespace(
            max_project_finish_shift_days=1,
            requires_approval=True,
            affected_tasks=(),
            newly_critical_task_ids=(),
            no_longer_critical_task_ids=(),
        )

    def analyse_delay(self, **kwargs):
        return self.analyse(**kwargs)


def test_da5_schedule_impact_entry_points_share_baseline_decision() -> None:
    impact_service = _ImpactService()
    task_service = SimpleNamespace(
        get_task=lambda _task_id: SimpleNamespace(start_date=date(2026, 8, 1)),
    )

    scheduling_result = build_change_impact(
        "project-1",
        "task-1",
        change_impact_service=impact_service,
    )
    task_result = ProjectManagementTasksDesktopApi(
        task_service=task_service,
        schedule_change_impact_service=impact_service,
    ).get_schedule_impact("task-1", "project-1")

    assert impact_service.has_baseline_values == [True, True]
    assert scheduling_result is not None and scheduling_result.requires_approval is True
    assert task_result.requires_approval is True


class _ScopedResourceService:
    def __init__(self) -> None:
        self.context_calls: list[str] = []
        self.resources = [SimpleNamespace(id="resource-active-org")]

    def list_for_project_workspace(
        self,
        project_id: str,
        *,
        resource_ids: tuple[str, ...] = (),
    ):
        self.context_calls.append(project_id)
        if not resource_ids:
            return self.resources
        selected = set(resource_ids)
        return [resource for resource in self.resources if resource.id in selected]


def test_da1_project_resource_scope_resolution_uses_public_application_query() -> None:
    resource_service = _ScopedResourceService()

    rows = list_resources_for_context(
        "project-1",
        resource_service=resource_service,
    )

    assert [row.id for row in rows] == ["resource-active-org"]
    assert resource_service.context_calls == ["project-1"]


def test_da1_project_manager_queries_project_resources_without_resource_read(services) -> None:
    project = services["project_service"].create_project("DA1 Scoped Project")
    resource = services["resource_service"].create_resource(
        name="Scoped Planner",
        role="Planner",
    )
    membership = services["project_resource_service"].add_to_project(
        project_id=project.id,
        resource_id=resource.id,
    )
    principal = services["user_session"].principal
    services["user_session"].set_principal(
        UserSessionPrincipal(
            user_id=principal.user_id,
            username="scoped-project-manager",
            display_name="Scoped Project Manager",
            role_names=frozenset(),
            permissions=frozenset({"project.manage"}),
            scoped_access={
                "project": {project.id: frozenset({"project.manage"})},
            },
            active_tenant_id=principal.active_tenant_id,
            active_organization_id=principal.active_organization_id,
        )
    )

    resources = services["resource_service"].list_for_project_workspace(project.id)
    memberships = services["project_resource_service"].list_for_project_workspace(project.id)

    assert [row.id for row in resources] == [resource.id]
    assert [row.id for row in memberships] == [membership.id]


def test_da1_task_reader_queries_only_its_scoped_project_resources(services) -> None:
    project = services["project_service"].create_project("DA1 Task Project")
    services["project_service"].create_project("DA1 Hidden Project")
    resource = services["resource_service"].create_resource(
        name="Task Planner",
        role="Planner",
    )
    membership = services["project_resource_service"].add_to_project(
        project_id=project.id,
        resource_id=resource.id,
    )
    principal = services["user_session"].principal
    services["user_session"].set_principal(
        UserSessionPrincipal(
            user_id=principal.user_id,
            username="scoped-task-reader",
            display_name="Scoped Task Reader",
            role_names=frozenset(),
            permissions=frozenset({"task.read"}),
            scoped_access={
                "project": {project.id: frozenset({"task.read"})},
            },
            active_tenant_id=principal.active_tenant_id,
            active_organization_id=principal.active_organization_id,
        )
    )

    projects = services["project_service"].list_for_task_workspace()
    memberships = services["project_resource_service"].list_for_task_workspace(project.id)
    resources = services["resource_service"].list_for_task_workspace(
        resource_ids=(resource.id,),
    )

    assert [row.id for row in projects] == [project.id]
    assert [row.id for row in memberships] == [membership.id]
    assert [row.id for row in resources] == [resource.id]


def test_da1_task_project_scope_resolution_uses_public_application_query() -> None:
    project = SimpleNamespace(
        id="project-task-read",
        name="Task Scoped Project",
        organization_id="organization-1",
    )
    project_service = SimpleNamespace(list_for_task_workspace=lambda: [project])

    rows = project_rows_for_task_scope(
        project_service=project_service,
    )

    assert [row.id for row in rows] == ["project-task-read"]


class _CapturingResourceService:
    def __init__(self) -> None:
        self.resource = SimpleNamespace(
            id="resource-1",
            name="Planner",
            code="RES-1",
            role="Planner",
            hourly_rate=100.0,
            is_active=True,
            cost_type="LABOR",
            currency_code="EUR",
            capacity_percent=100.0,
            address="",
            contact="",
            worker_type="EXTERNAL",
            employee_id=None,
            version=1,
        )
        self.update_kwargs = {}

    def get_resource(self, _resource_id: str):
        return self.resource

    def update_resource(self, _resource_id: str, **kwargs):
        self.update_kwargs = kwargs
        self.resource.hourly_rate = kwargs.get("hourly_rate") or self.resource.hourly_rate
        self.resource.currency_code = kwargs.get("currency_code") or self.resource.currency_code
        return self.resource


def test_da3_desktop_forwards_rate_fields_without_policy_decision() -> None:
    service = _CapturingResourceService()
    api = ProjectManagementResourcesDesktopApi(resource_service=service)

    api.update_resource(
        ResourceUpdateCommand(
            resource_id="resource-1",
            name="Planner",
            role="Planner",
            hourly_rate=Decimal("120"),
            currency_code="USD",
            expected_version=1,
        )
    )

    assert service.update_kwargs["hourly_rate"] == Decimal("120")
    assert service.update_kwargs["currency_code"] == "USD"
    assert "effective_on" not in service.update_kwargs


def test_da1_resource_assignments_use_public_task_service_query() -> None:
    task_service = SimpleNamespace(
        list_assignments_for_resource=lambda _resource_id: (
            SimpleNamespace(
                id="assignment-1",
                task_id="task-1",
                allocation_percent=75.0,
                hours_logged=3.5,
            ),
        ),
        list_tasks_for_resource=lambda _resource_id: (
            SimpleNamespace(id="task-1", name="Planning", project_id="project-1"),
        ),
    )

    rows = build_resource_assignments(
        "resource-1",
        task_service=task_service,
        project_service=SimpleNamespace(
            get_project=lambda _project_id: SimpleNamespace(name="Project One")
        ),
    )

    assert len(rows) == 1
    assert rows[0].id == "assignment-1"
    assert rows[0].task_name == "Planning"
    assert rows[0].project_name == "Project One"
    assert rows[0].allocation_label == "75%"


def test_da1_task_service_lists_authorized_resource_assignments(services) -> None:
    project = services["project_service"].create_project("DA1 Resource Assignment")
    resource = services["resource_service"].create_resource(
        name="DA1 Planner",
        role="Planner",
    )
    task = services["task_service"].create_task(
        project.id,
        "DA1 Planning Task",
        start_date=date(2026, 8, 10),
        duration_days=2,
    )
    assignment = services["task_service"].assign_resource(
        task.id,
        resource.id,
        allocation_percent=60.0,
    )

    rows = services["task_service"].list_assignments_for_resource(resource.id)

    assert [row.id for row in rows] == [assignment.id]


def test_da0_characterizes_duplicate_project_resource_rate_precedence() -> None:
    project_resource = SimpleNamespace(
        id="project-resource-1",
        project_id="project-1",
        resource_id="resource-1",
        hourly_rate=Decimal("125"),
        currency_code="GBP",
        planned_hours=Decimal("40"),
        is_active=True,
    )
    resource = SimpleNamespace(
        id="resource-1",
        name="Planner",
        role="Lead",
        worker_type="EXTERNAL",
        hourly_rate=Decimal("90"),
        currency_code="EUR",
        is_active=True,
    )

    project_row = serialize_project_resource(project_resource, resource_by_id=resource)
    task_options = build_project_resource_options(
        "project-1",
        project_resource_service=SimpleNamespace(
            list_for_task_workspace=lambda _project_id: (project_resource,)
        ),
        resource_service=SimpleNamespace(
            list_for_task_workspace=lambda **_kwargs: (resource,)
        ),
    )

    assert project_row.hourly_rate == 125.0
    assert project_row.currency_code == "GBP"
    assert task_options[0].label == "Planner (125.00 GBP/hr)"


def test_da0_characterizes_assignment_preview_formula_and_per_conflict_lookup() -> None:
    target = SimpleNamespace(
        id="task-1",
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 12),
    )
    conflict_tasks = {
        "task-2": SimpleNamespace(id="task-2", project_name="Project Two"),
        "task-3": SimpleNamespace(id="task-3", project_name="Project Three"),
    }
    task_calls: list[str] = []

    def _get_task(task_id: str):
        task_calls.append(task_id)
        return target if task_id == target.id else conflict_tasks.get(task_id)

    window = SimpleNamespace(
        peak_load_percent=160.0,
        capacity_percent=100.0,
        daily_loads=(
            SimpleNamespace(overloaded=True, contributing_tasks=("task-1", "task-2")),
            SimpleNamespace(overloaded=True, contributing_tasks=("task-3",)),
        ),
    )

    preview = build_assignment_preview(
        "task-1",
        "project-resource-1",
        task_service=SimpleNamespace(get_task=_get_task),
        project_resource_service=SimpleNamespace(
            get=lambda _project_resource_id: SimpleNamespace(resource_id="resource-1")
        ),
        assignment_skill_validator=None,
        resource_availability_service=SimpleNamespace(
            is_resource_available=lambda *_args: (False, window)
        ),
    )

    assert preview.overallocation_pct == 60.0
    assert set(preview.conflict_projects) == {"Project Two", "Project Three"}
    assert set(task_calls) == {"task-1", "task-2", "task-3"}


def test_da0_characterizes_shared_overload_boundary_across_desktop_views() -> None:
    at_capacity = ResourceLoadRow(
        resource_id="resource-100",
        resource_name="At capacity",
        utilization_percent=100.0,
        total_allocation_percent=100.0,
        capacity_percent=100.0,
        tasks_count=1,
    )
    overloaded = ResourceLoadRow(
        resource_id="resource-101",
        resource_name="Overloaded",
        utilization_percent=100.1,
        total_allocation_percent=100.1,
        capacity_percent=100.0,
        tasks_count=2,
    )
    dashboard_data = SimpleNamespace(resource_load=(at_capacity, overloaded))

    chart = _build_resource_chart(dashboard_data=dashboard_data, portfolio_mode=False)
    panel = _build_resource_overload_panel(dashboard_data=dashboard_data, portfolio_mode=False)
    table = _build_resource_overloads_table(dashboard_data)

    assert at_capacity.utilization_status_label == "Hot"
    assert overloaded.utilization_status_label == "Overloaded"
    assert overloaded_resource_count((at_capacity, overloaded)) == 1
    assert [point.tone for point in chart.points] == ["accent", "danger"]
    assert [row.tone for row in panel.rows] == ["danger", "warning"]
    assert [row.values["statusLabel"] for row in table.rows] == ["Balanced", "Overloaded"]


def test_da0_characterizes_dashboard_and_register_high_risk_parity() -> None:
    entries = (
        SimpleNamespace(
            id="critical-open",
            project_id="project-1",
            entry_type=RegisterEntryType.RISK,
            title="Critical open",
            severity=RegisterEntrySeverity.CRITICAL,
            status=RegisterEntryStatus.OPEN,
            owner_name=None,
            due_date=date(2026, 8, 20),
            response_plan="Escalate",
            impact_summary="",
            description="",
        ),
        SimpleNamespace(
            id="high-progress",
            project_id="project-1",
            entry_type=RegisterEntryType.RISK,
            title="High in progress",
            severity=RegisterEntrySeverity.HIGH,
            status=RegisterEntryStatus.IN_PROGRESS,
            owner_name=None,
            due_date=date(2026, 8, 15),
            response_plan="Mitigate",
            impact_summary="",
            description="",
        ),
        SimpleNamespace(
            id="high-closed",
            project_id="project-1",
            entry_type=RegisterEntryType.RISK,
            title="High closed",
            severity=RegisterEntrySeverity.HIGH,
            status=RegisterEntryStatus.CLOSED,
            owner_name=None,
            due_date=date(2026, 8, 1),
            response_plan="",
            impact_summary="",
            description="",
        ),
    )
    service = SimpleNamespace(list_entries=lambda **_kwargs: entries)

    register_rows = build_entry_list(register_service=service, project_id="project-1")
    active_high_risk_ids = [
        row.id
        for row in register_rows
        if row.severity in (RegisterEntrySeverity.HIGH, RegisterEntrySeverity.CRITICAL)
        and row.status in (RegisterEntryStatus.OPEN, RegisterEntryStatus.IN_PROGRESS)
    ]
    dashboard_table = _build_high_risks_table(
        SimpleNamespace(
            kpi=SimpleNamespace(project_id="project-1"),
            high_risks=tuple(
                row for row in register_rows if row.id in active_high_risk_ids
            ),
        )
    )
    assert [row.id for row in dashboard_table.rows] == active_high_risk_ids
