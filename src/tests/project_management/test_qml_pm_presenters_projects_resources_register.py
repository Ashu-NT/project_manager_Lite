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
from src.api.desktop.runtime import build_desktop_api_registry
from src.api.desktop.platform import ApprovalRequestDto, ApprovalStatus, DesktopApiResult
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
from src.core.platform.documents import DocumentStorageKind
from src.tests.ui_runtime_helpers import wait_until
from src.ui_qml.modules.project_management.presenters.collaboration import (
    ProjectCollaborationWorkspacePresenter,
)


class _FakeEmployeeService:
    def list_employees(self, *, active_only: bool | None = None) -> list[SimpleNamespace]:
        employees = [
            SimpleNamespace(
                id="emp-1",
                employee_code="EMP-001",
                full_name="Alex Taylor",
                title="Planner",
                department="Operations",
                site_name="Plant North",
                email="alex@example.com",
                phone="555-0100",
                is_active=True,
            ),
            SimpleNamespace(
                id="emp-2",
                employee_code="EMP-002",
                full_name="Jordan Blake",
                title="Supervisor",
                department="Maintenance",
                site_name="Plant South",
                email="jordan@example.com",
                phone="555-0101",
                is_active=False,
            ),
        ]
        if active_only is None:
            return employees
        return [
            employee
            for employee in employees
            if bool(employee.is_active) == bool(active_only)
        ]


class _FakeResourceService:
    def __init__(self, resources: list[SimpleNamespace] | None = None) -> None:
        self._resources = {
            resource.id: resource
            for resource in (resources or [])
        }

    def list_resources(self) -> list[SimpleNamespace]:
        return list(self._resources.values())


class _FakeRegisterService:
    def __init__(self, entries: list[SimpleNamespace] | None = None) -> None:
        self._entries = {
            entry.id: entry
            for entry in (entries or [])
        }

    def list_entries(
        self,
        *,
        project_id: str | None = None,
        entry_type: RegisterEntryType | None = None,
        status: RegisterEntryStatus | None = None,
        severity: RegisterEntrySeverity | None = None,
    ) -> list[SimpleNamespace]:
        return [
            entry
            for entry in self._entries.values()
            if (project_id is None or entry.project_id == project_id)
            and (entry_type is None or entry.entry_type == entry_type)
            and (status is None or entry.status == status)
            and (severity is None or entry.severity == severity)
        ]


def _build_register_record(
    *,
    entry_id: str,
    project_id: str,
    entry_type: RegisterEntryType,
    title: str,
    description: str,
    severity: RegisterEntrySeverity,
    status: RegisterEntryStatus,
    owner_name: str | None,
    due_date: date | None,
    impact_summary: str,
    response_plan: str,
    version: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=entry_id,
        project_id=project_id,
        entry_type=entry_type,
        title=title,
        description=description,
        severity=severity,
        status=status,
        owner_name=owner_name,
        due_date=due_date,
        impact_summary=impact_summary,
        response_plan=response_plan,
        version=version,
    )


def test_project_management_workspace_catalog_exposes_typed_projects_controller() -> None:
    projects_api = build_project_management_projects_desktop_api(
        project_service=SimpleNamespace(
            list_projects=lambda: [
                SimpleNamespace(
                    id="proj-1",
                    name="Plant Upgrade",
                    description="Replace switchgear and commission the new line.",
                    status=ProjectStatus.ACTIVE,
                    start_date=date(2026, 5, 1),
                    end_date=date(2026, 8, 15),
                    client_name="Contoso Manufacturing",
                    client_contact="alex@contoso.example",
                    planned_budget=250000.0,
                    currency="EUR",
                    version=4,
                ),
                SimpleNamespace(
                    id="proj-2",
                    name="Warehouse Retrofit",
                    description="Upgrade lighting and controls.",
                    status=ProjectStatus.ON_HOLD,
                    start_date=None,
                    end_date=None,
                    client_name="Northwind Logistics",
                    client_contact="jamie@northwind.example",
                    planned_budget=None,
                    currency=None,
                    version=2,
                ),
            ]
        )
    )
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(project_management_projects=projects_api)
    )

    controller = catalog.projectsWorkspace

    assert controller.workspace["routeId"] == "project_management.projects"
    assert controller.overview["title"] == "Projects"
    assert controller.overview["metrics"][0]["value"] == "2"
    assert controller.projects["items"][0]["title"] == "Plant Upgrade"
    assert controller.selectedProject["title"] == "Plant Upgrade"

    controller.setStatusFilter("ON_HOLD")

    assert controller.selectedStatusFilter == "ON_HOLD"
    assert controller.projects["items"][0]["title"] == "Warehouse Retrofit"

    controller.setSearchText("plant")

    assert controller.projects["items"] == []
    assert controller.emptyState == "No projects match the current filters."


def test_project_management_workspace_catalog_exposes_typed_resources_controller() -> None:
    resources_api = build_project_management_resources_desktop_api(
        resource_service=_FakeResourceService(
            [
                SimpleNamespace(
                    id="res-1",
                    name="Electrical Crew",
                    role="Lead Technician",
                    hourly_rate=95.0,
                    is_active=True,
                    cost_type=CostType.LABOR,
                    currency_code="EUR",
                    version=3,
                    capacity_percent=110.0,
                    address="Site Office",
                    contact="crew@example.com",
                    worker_type=WorkerType.EXTERNAL,
                    employee_id=None,
                ),
                SimpleNamespace(
                    id="res-2",
                    name="Alex Taylor",
                    role="Planner",
                    hourly_rate=80.0,
                    is_active=False,
                    cost_type=CostType.LABOR,
                    currency_code="USD",
                    version=2,
                    capacity_percent=100.0,
                    address="",
                    contact="alex@example.com",
                    worker_type=WorkerType.EMPLOYEE,
                    employee_id="emp-1",
                ),
            ]
        ),
        employee_service=_FakeEmployeeService(),
    )
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(project_management_resources=resources_api)
    )

    controller = catalog.resourcesWorkspace

    assert controller.workspace["routeId"] == "project_management.resources"
    assert controller.overview["title"] == "Resources"
    assert controller.categoryOptions[1]["value"] == "LABOR"
    assert controller.employeeOptions[0]["context"] == "Operations | Plant North"
    assert controller.resources["items"][0]["title"] == "Electrical Crew"
    assert controller.selectedResource["title"] == "Electrical Crew"

    controller.setActiveFilter("inactive")

    assert controller.selectedActiveFilter == "inactive"
    assert [item["title"] for item in controller.resources["items"]] == ["Alex Taylor"]

    controller.setSearchText("crew")

    assert controller.resources["items"] == []
    assert controller.emptyState == "No resources match the current filters."


def test_project_management_workspace_catalog_exposes_typed_register_controller() -> None:
    register_api = build_project_management_register_desktop_api(
        project_service=SimpleNamespace(
            list_projects=lambda: [
                SimpleNamespace(id="proj-1", name="Plant Upgrade"),
                SimpleNamespace(id="proj-2", name="Warehouse Retrofit"),
            ]
        ),
        register_service=_FakeRegisterService(
            [
                _build_register_record(
                    entry_id="reg-1",
                    project_id="proj-1",
                    entry_type=RegisterEntryType.RISK,
                    title="Critical supplier dependency",
                    description="Switchgear release note is still pending.",
                    severity=RegisterEntrySeverity.CRITICAL,
                    status=RegisterEntryStatus.OPEN,
                    owner_name="Lead Planner",
                    due_date=date(2026, 5, 2),
                    impact_summary="Commissioning could slip by one week.",
                    response_plan="Escalate with vendor and approve alternates.",
                    version=2,
                ),
                _build_register_record(
                    entry_id="reg-2",
                    project_id="proj-1",
                    entry_type=RegisterEntryType.CHANGE,
                    title="Additional cable tray scope",
                    description="New field route requires material and labor change.",
                    severity=RegisterEntrySeverity.MEDIUM,
                    status=RegisterEntryStatus.IN_PROGRESS,
                    owner_name="Project Engineer",
                    due_date=date(2026, 5, 7),
                    impact_summary="Budget exposure needs approval.",
                    response_plan="Issue estimate and submit change control.",
                    version=1,
                ),
                _build_register_record(
                    entry_id="reg-3",
                    project_id="proj-2",
                    entry_type=RegisterEntryType.ISSUE,
                    title="Permit handoff blocked",
                    description="Permit package is still pending city review.",
                    severity=RegisterEntrySeverity.HIGH,
                    status=RegisterEntryStatus.IN_PROGRESS,
                    owner_name="PM",
                    due_date=date(2026, 5, 6),
                    impact_summary="Mobilization is at risk.",
                    response_plan="Daily escalation with local authority.",
                    version=1,
                ),
            ]
        ),
    )
    # Risk was consolidated into the unified Register workspace (no standalone
    # risk controller/route). The Register controller now serves risks via its
    # RISK type filter. See docs/REGISTER_RISK_CONSOLIDATION.md.
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            project_management_register=register_api,
        )
    )

    register_controller = catalog.registerWorkspace

    assert register_controller.workspace["routeId"] == "project_management.register"
    assert register_controller.typeOptions[1]["value"] == "RISK"
    assert register_controller.entries["items"][0]["title"] == "Critical supplier dependency"
    assert register_controller.selectedEntry["fields"][2]["label"] == "Impact"

    register_controller.setTypeFilter("RISK")

    assert [item["title"] for item in register_controller.entries["items"]] == [
        "Critical supplier dependency"
    ]

    register_controller.setTypeFilter("CHANGE")

    assert [item["title"] for item in register_controller.entries["items"]] == [
        "Additional cable tray scope"
    ]
