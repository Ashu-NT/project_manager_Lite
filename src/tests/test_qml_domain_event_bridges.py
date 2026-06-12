from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.core.shared.events.domain_events import DomainChangeEvent, domain_events
from src.ui_qml.modules.maintenance.context import MaintenanceWorkspaceCatalog
from src.ui_qml.modules.project_management.context import (
    ProjectManagementWorkspaceCatalog,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


def test_pm_tasks_workspace_queues_domain_refresh_while_busy(monkeypatch) -> None:
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.tasksWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    controller._set_is_busy(True)
    domain_events.tasks_changed.emit("proj-1")
    domain_events.collaboration_changed.emit("task-1")
    domain_events.timesheet_periods_changed.emit("period-1")

    assert refresh_calls == []

    controller._set_is_busy(False)

    assert refresh_calls == ["refresh"]


def test_pm_resources_workspace_refreshes_on_resource_and_employee_events(monkeypatch) -> None:
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.resourcesWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.resources_changed.emit("res-1")
    domain_events.employees_changed.emit("emp-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_pm_collaboration_workspace_refreshes_on_collaboration_workflow_events(monkeypatch) -> None:
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.collaborationWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.collaboration_changed.emit("task-1")
    domain_events.approvals_changed.emit("approval-1")
    domain_events.timesheet_periods_changed.emit("period-1")

    assert refresh_calls == ["refresh", "refresh", "refresh"]


def test_pm_portfolio_workspace_refreshes_on_portfolio_workflow_events(
    monkeypatch, qapp
) -> None:
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.portfolioWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.domain_changed.emit(
        DomainChangeEvent(
            category="module",
            scope_code="project_management",
            entity_type="portfolio_entity",
            entity_id="portfolio-1",
            source_event="manual_test",
        )
    )
    domain_events.domain_changed.emit(
        DomainChangeEvent(
            category="module",
            scope_code="project_management",
            entity_type="project",
            entity_id="proj-1",
            source_event="manual_test",
        )
    )
    QApplication.processEvents()

    assert refresh_calls == ["refresh"]


def test_pm_timesheets_workspace_refreshes_on_timesheet_workflow_events(monkeypatch) -> None:
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.timesheetsWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.timesheet_periods_changed.emit("period-1")
    domain_events.resources_changed.emit("res-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_platform_control_workspace_refreshes_on_control_events(monkeypatch) -> None:
    catalog = PlatformWorkspaceCatalog()
    controller = catalog.controlWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.approvals_changed.emit("approval-1")
    domain_events.costs_changed.emit("proj-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_platform_settings_workspace_refreshes_on_runtime_events(monkeypatch) -> None:
    catalog = PlatformWorkspaceCatalog()
    controller = catalog.settingsWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.modules_changed.emit("project_management")
    domain_events.organizations_changed.emit("org-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_platform_admin_access_workspace_refreshes_on_access_events(monkeypatch) -> None:
    catalog = PlatformWorkspaceCatalog()
    controller = catalog.adminAccessWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.auth_changed.emit("user-1")
    domain_events.access_changed.emit("project-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_platform_admin_workspace_refreshes_on_master_data_events(monkeypatch) -> None:
    catalog = PlatformWorkspaceCatalog()
    controller = catalog.adminWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.organizations_changed.emit("org-1")
    domain_events.documents_changed.emit("doc-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_maintenance_dashboard_workspace_refreshes_on_maintenance_and_site_events(
    monkeypatch,
) -> None:
    catalog = MaintenanceWorkspaceCatalog()
    controller = catalog.dashboardWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.domain_changed.emit(
        DomainChangeEvent(
            category="module",
            scope_code="maintenance_management",
            entity_type="maintenance_work_order",
            entity_id="wo-1",
            source_event="manual_test",
        )
    )
    domain_events.sites_changed.emit("site-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_maintenance_assets_workspace_refreshes_on_maintenance_and_site_events(
    monkeypatch,
) -> None:
    catalog = MaintenanceWorkspaceCatalog()
    controller = catalog.assetsWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.domain_changed.emit(
        DomainChangeEvent(
            category="module",
            scope_code="maintenance_management",
            entity_type="maintenance_asset",
            entity_id="asset-1",
            source_event="manual_test",
        )
    )
    domain_events.sites_changed.emit("site-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_maintenance_reliability_workspace_queues_domain_refresh_while_busy(
    monkeypatch,
) -> None:
    catalog = MaintenanceWorkspaceCatalog()
    controller = catalog.reliabilityWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    controller._set_is_busy(True)
    domain_events.domain_changed.emit(
        DomainChangeEvent(
            category="module",
            scope_code="maintenance_management",
            entity_type="maintenance_failure_pattern",
            entity_id="rel-1",
            source_event="manual_test",
        )
    )

    assert refresh_calls == []

    controller._set_is_busy(False)

    assert refresh_calls == ["refresh"]


def test_maintenance_planner_workspace_refreshes_on_maintenance_and_site_events(
    monkeypatch,
) -> None:
    catalog = MaintenanceWorkspaceCatalog()
    controller = catalog.plannerWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.domain_changed.emit(
        DomainChangeEvent(
            category="module",
            scope_code="maintenance_management",
            entity_type="maintenance_work_request",
            entity_id="wr-1",
            source_event="manual_test",
        )
    )
    domain_events.sites_changed.emit("site-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_maintenance_work_requests_workspace_refreshes_on_maintenance_and_site_events(
    monkeypatch,
) -> None:
    catalog = MaintenanceWorkspaceCatalog()
    controller = catalog.workRequestsWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.domain_changed.emit(
        DomainChangeEvent(
            category="module",
            scope_code="maintenance_management",
            entity_type="maintenance_work_request",
            entity_id="wr-1",
            source_event="manual_test",
        )
    )
    domain_events.sites_changed.emit("site-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_maintenance_work_orders_workspace_refreshes_on_maintenance_and_site_events(
    monkeypatch,
) -> None:
    catalog = MaintenanceWorkspaceCatalog()
    controller = catalog.workOrdersWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.domain_changed.emit(
        DomainChangeEvent(
            category="module",
            scope_code="maintenance_management",
            entity_type="maintenance_work_order",
            entity_id="wo-1",
            source_event="manual_test",
        )
    )
    domain_events.sites_changed.emit("site-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_maintenance_preventive_workspace_refreshes_on_maintenance_and_site_events(
    monkeypatch,
) -> None:
    catalog = MaintenanceWorkspaceCatalog()
    controller = catalog.preventiveWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.domain_changed.emit(
        DomainChangeEvent(
            category="module",
            scope_code="maintenance_management",
            entity_type="maintenance_preventive_plan",
            entity_id="plan-1",
            source_event="manual_test",
        )
    )
    domain_events.sites_changed.emit("site-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_implemented_qml_workspace_controllers_bind_domain_event_hooks() -> None:
    root = Path(__file__).resolve().parents[2]
    controller_expectations = {
        "src/ui_qml/modules/project_management/controllers/dashboard/dashboard_workspace_controller.py": (
            "self._bind_domain_events()",
        ),
        "src/ui_qml/modules/project_management/controllers/dashboard/dashboard_refresh_mixin.py": (
            '_subscribe_domain_change(',
            'scope_code="project_management"',
            '"approval_request"',
        ),
        "src/ui_qml/modules/project_management/controllers/projects/projects_workspace_controller.py": (
            "bind_project_domain_events(self)",
        ),
        "src/ui_qml/modules/project_management/controllers/projects/project_domain_event_binder.py": (
            '_subscribe_domain_change(',
        ),
        "src/ui_qml/modules/project_management/controllers/collaboration/collaboration_workspace_controller.py": (
            "bind_collaboration_domain_events(self)",
        ),
        "src/ui_qml/modules/project_management/controllers/collaboration/domain_event_binder.py": (
            "domain_events.approvals_changed",
        ),
        "src/ui_qml/modules/project_management/controllers/portfolio/portfolio_workspace_controller.py": (
            "bind_portfolio_domain_events(self)",
        ),
        "src/ui_qml/modules/project_management/controllers/portfolio/domain_event_binder.py": (
            '_subscribe_domain_change(',
        ),
        "src/ui_qml/modules/project_management/controllers/tasks/tasks_workspace_controller.py": (
            "bind_task_domain_events(self)",
        ),
        "src/ui_qml/modules/project_management/controllers/tasks/task_domain_event_binder.py": (
            "timesheet_period",
            "task_collaboration",
        ),
        "src/ui_qml/modules/project_management/controllers/resources/resources_workspace_controller.py": (
            "bind_resource_domain_events(self)",
        ),
        "src/ui_qml/modules/project_management/controllers/resources/resource_domain_event_binder.py": (
            "domain_events.employees_changed",
        ),
        "src/ui_qml/modules/project_management/controllers/scheduling/scheduling_workspace_controller.py": (
            "bind_scheduling_domain_events(self)",
        ),
        "src/ui_qml/modules/project_management/controllers/scheduling/domain_event_binder.py": (
            '_subscribe_domain_change(',
        ),
        "src/ui_qml/modules/project_management/controllers/financials/financials_workspace_controller.py": (
            "self._bind_domain_events()",
        ),
        "src/ui_qml/modules/project_management/controllers/financials/financials_refresh_mixin.py": (
            '_subscribe_domain_change(',
            'scope_code="project_management"',
        ),
        "src/ui_qml/modules/project_management/controllers/register/register_workspace_controller.py": (
            "bind_register_domain_events(self)",
        ),
        "src/ui_qml/modules/project_management/controllers/register/register_domain_event_binder.py": (
            '_subscribe_domain_change(',
        ),
        "src/ui_qml/modules/project_management/controllers/timesheets/timesheets_workspace_controller.py": (
            "bind_timesheets_domain_events(self)",
        ),
        "src/ui_qml/modules/project_management/controllers/timesheets/domain_event_binder.py": (
            '_subscribe_domain_change(',
        ),
        "src/ui_qml/platform/controllers/control/control_workspace_controller.py": (
            "self._bind_domain_events()",
            "domain_events.approvals_changed",
        ),
        "src/ui_qml/platform/controllers/settings/settings_workspace_controller.py": (
            "self._bind_domain_events()",
            "domain_events.modules_changed",
        ),
        "src/ui_qml/platform/controllers/admin/access_workspace_controller.py": (
            "self._bind_domain_events()",
            "domain_events.access_changed",
        ),
        "src/ui_qml/platform/controllers/admin/admin_console_controller.py": (
            "self._bind_domain_events()",
        ),
        "src/ui_qml/platform/controllers/admin/admin_domain_event_binder.py": (
            "domain_events.organizations_changed",
        ),
        "src/ui_qml/modules/maintenance/controllers/dashboard/dashboard_workspace_controller.py": (
            "self._bind_domain_events()",
            'scope_code="maintenance_management"',
        ),
        "src/ui_qml/modules/maintenance/controllers/assets/assets_workspace_controller.py": (
            "self._bind_domain_events()",
            'scope_code="maintenance_management"',
        ),
        "src/ui_qml/modules/maintenance/controllers/planner/planner_workspace_controller.py": (
            "self._bind_domain_events()",
            'scope_code="maintenance_management"',
        ),
        "src/ui_qml/modules/maintenance/controllers/work_requests/work_requests_workspace_controller.py": (
            "self._bind_domain_events()",
            'scope_code="maintenance_management"',
        ),
        "src/ui_qml/modules/maintenance/controllers/work_orders/work_orders_workspace_controller.py": (
            "self._bind_domain_events()",
            'scope_code="maintenance_management"',
        ),
        "src/ui_qml/modules/maintenance/controllers/preventive/preventive_workspace_controller.py": (
            "self._bind_domain_events()",
            'scope_code="maintenance_management"',
        ),
        "src/ui_qml/modules/maintenance/controllers/reliability/reliability_workspace_controller.py": (
            "self._bind_domain_events()",
            'scope_code="maintenance_management"',
        ),
    }

    for relative_path, expected_fragments in controller_expectations.items():
        text = (root / relative_path).read_text(encoding="utf-8", errors="ignore")
        for fragment in expected_fragments:
            assert fragment in text

