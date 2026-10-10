import ast
from pathlib import Path

from src.core.modules.project_management.application.collaboration import (
    CollaborationService,
)
from src.core.modules.project_management.application.dashboard import DashboardService
from src.core.modules.project_management.application.financials import FinanceService
from src.core.modules.project_management.application.portfolio import PortfolioService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.reporting import (
    ReportingService,
)
from src.core.modules.project_management.application.resources import (
    ProjectResourceService,
    ResourceService,
)
from src.core.modules.project_management.application.risk import RegisterService
from src.core.modules.project_management.application.scheduling import (
    CalendarProtocol,
    SchedulingEngine,
)
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.timesheets import TimesheetService
from src.core.modules.project_management.infrastructure.importers import (
    DataImportService,
)
from src.core.platform.access import AccessControlService
from src.core.platform.application.approval.approval_service import ApprovalService
from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.master_data.data_exchange import (
    MasterDataExchangeService,
)
from src.core.platform.application.master_data.department.department_service import (
    DepartmentService,
)
from src.core.platform.application.master_data.documents.document_service import (
    DocumentService,
)
from src.core.platform.application.master_data.employee.employee_service import (
    EmployeeService,
)
from src.core.platform.application.master_data.org.organization_service import (
    OrganizationService,
)
from src.core.platform.application.master_data.party.party_service import PartyService
from src.core.platform.application.master_data.site.site_service import SiteService
from src.core.platform.application.platform_runtime import (
    PlatformRuntimeApplicationService,
)
from src.core.platform.application.security.auth import AuthService
from src.core.platform.application.tenant.modules import ModuleCatalogService
from src.core.platform.application.time_management.time import TimeService
from src.core.platform.common.service_base import ServiceBase as LegacyServiceBase
from src.infra.composition.app_container import ServiceGraph, build_service_graph
from src.tests.path_rewrites import REPO_ROOT


def test_service_graph_builder_wires_all_services(session):
    graph = build_service_graph(session)

    assert isinstance(graph, ServiceGraph)
    assert isinstance(graph.platform_runtime_application_service, PlatformRuntimeApplicationService)
    assert isinstance(graph.module_catalog_service, ModuleCatalogService)
    assert isinstance(graph.time_service, TimeService)
    assert isinstance(graph.approval_service, ApprovalService)
    assert isinstance(graph.auth_service, AuthService)
    assert isinstance(graph.organization_service, OrganizationService)
    assert isinstance(graph.document_service, DocumentService)
    assert isinstance(graph.party_service, PartyService)
    assert isinstance(graph.department_service, DepartmentService)
    assert isinstance(graph.site_service, SiteService)
    assert isinstance(graph.employee_service, EmployeeService)
    assert isinstance(graph.master_data_exchange_service, MasterDataExchangeService)
    assert isinstance(graph.access_service, AccessControlService)
    assert isinstance(graph.enterprise_audit_service, EnterpriseAuditService)
    assert isinstance(graph.collaboration_service, CollaborationService)
    assert isinstance(graph.project_service, ProjectService)
    assert isinstance(graph.task_service, TaskService)
    assert isinstance(graph.timesheet_service, TimesheetService)
    assert isinstance(graph.resource_service, ResourceService)
    assert isinstance(graph.finance_service, FinanceService)
    # work_calendar_engine is now GlobalCalendarShim (enterprise-backed)
    assert hasattr(graph, "work_calendar_engine") and graph.work_calendar_engine is not None
    assert isinstance(graph.work_calendar_engine, CalendarProtocol)
    assert isinstance(graph.scheduling_engine, SchedulingEngine)
    assert isinstance(graph.reporting_service, ReportingService)
    assert isinstance(graph.baseline_service, BaselineService)
    assert isinstance(graph.dashboard_service, DashboardService)
    assert isinstance(graph.portfolio_service, PortfolioService)
    assert isinstance(graph.register_service, RegisterService)
    assert isinstance(graph.project_resource_service, ProjectResourceService)
    assert isinstance(graph.data_import_service, DataImportService)

    as_dict = graph.as_dict()
    assert as_dict["approval_service"] is graph.approval_service
    assert as_dict["auth_service"] is graph.auth_service
    assert as_dict["platform_runtime_application_service"] is graph.platform_runtime_application_service
    assert as_dict["organization_service"] is graph.organization_service
    assert as_dict["document_service"] is graph.document_service
    assert as_dict["party_service"] is graph.party_service
    assert as_dict["department_service"] is graph.department_service
    assert as_dict["site_service"] is graph.site_service
    assert as_dict["employee_service"] is graph.employee_service
    assert as_dict["master_data_exchange_service"] is graph.master_data_exchange_service
    assert as_dict["module_catalog_service"] is graph.module_catalog_service
    assert as_dict["time_service"] is graph.time_service
    assert as_dict["access_service"] is graph.access_service
    assert as_dict["enterprise_audit_service"] is graph.enterprise_audit_service
    assert as_dict["collaboration_service"] is graph.collaboration_service
    assert as_dict["dashboard_service"] is graph.dashboard_service
    assert as_dict["finance_service"] is graph.finance_service
    assert as_dict["portfolio_service"] is graph.portfolio_service
    assert as_dict["register_service"] is graph.register_service
    assert as_dict["project_resource_service"] is graph.project_resource_service
    assert as_dict["timesheet_service"] is graph.timesheet_service
    assert as_dict["session"] is session
    assert graph.time_service is graph.timesheet_service


def test_project_management_legacy_service_roots_are_removed():
    legacy_roots = (
        Path("core/modules/project_management"),
        Path("infra/modules/project_management"),
    )

    for root in legacy_roots:
        files = [
            path
            for path in root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        ]
        assert not files, f"Legacy project-management root still contains files: {files}"


def test_inventory_procurement_legacy_service_roots_are_removed():
    legacy_roots = (
        Path("core/modules/inventory_procurement"),
        Path("infra/modules/inventory_procurement"),
    )

    for root in legacy_roots:
        files = [
            path
            for path in root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        ]
        assert not files, f"Legacy inventory-procurement root still contains files: {files}"


def test_maintenance_product_roots_and_registry_are_absent():
    assert not (REPO_ROOT / "src" / "core" / "modules" / "maintenance").exists()
    assert not (REPO_ROOT / "src" / "ui_qml" / "modules" / "maintenance").exists()
    assert not (REPO_ROOT / "src" / "infra" / "composition" / "maintenance_registry.py").exists()


def test_legacy_service_imports_point_to_new_packages():
    assert LegacyServiceBase.__name__ == "ServiceBase"


def test_services_module_delegates_to_modular_registration_builders():
    text = (
        REPO_ROOT / "src" / "infra" / "composition" / "app_container.py"
    ).read_text(
        encoding="utf-8",
        errors="ignore",
    )

    assert any(
        isinstance(node, ast.ImportFrom)
        and node.module == "src.core.platform.infrastructure.composition.bootstrap"
        and any(alias.name == "build_platform_service_bundle" for alias in node.names)
        for node in ast.walk(ast.parse(text))
    )
    assert "build_platform_repositories" in text
    assert "build_project_management_repository_context" in text
    assert "notification_recipient_policy=pm_notification_recipient_policy" in text
    assert "platform_services = build_platform_service_bundle(" in text
    assert "from src.core.modules.project_management.infrastructure.composition.bootstrap import (" in text
    assert "build_project_management_service_bundle(" in text


def test_service_registration_package_is_split_by_platform_and_module():
    root = REPO_ROOT / "src" / "infra" / "composition"

    assert (root / "__init__.py").exists()
    assert not (root / "persistence" / "repositories.py").exists()
    assert (
        REPO_ROOT / "src/core/platform/infrastructure/composition/dependencies/repositories.py"
    ).exists()
    assert (
        REPO_ROOT
        / "src/core/modules/project_management/infrastructure/composition/dependencies/repositories.py"
    ).exists()
    assert (
        REPO_ROOT / "src/core/platform/infrastructure/composition/bootstrap.py"
    ).exists()
    assert not (root / "modules" / "platform_registry.py").exists()
    assert (
        REPO_ROOT
        / "src/core/modules/project_management/infrastructure/composition/bootstrap.py"
    ).exists()
    assert not (root / "modules" / "project_registry.py").exists()


def test_platform_composition_has_no_module_imports():
    root = REPO_ROOT / "src/core/platform/infrastructure/composition"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("src.core.modules."), path
            elif isinstance(node, ast.Import):
                assert all(
                    not alias.name.startswith("src.core.modules.")
                    for alias in node.names
                ), path


def test_application_root_uses_only_pm_composition_bootstrap():
    source = (REPO_ROOT / "src/infra/composition/app_container.py").read_text(encoding="utf-8")
    pm_composition_imports = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
        and node.module
        and node.module.startswith(
            "src.core.modules.project_management.infrastructure.composition"
        )
    }
    assert pm_composition_imports == {
        "src.core.modules.project_management.infrastructure.composition.bootstrap"
    }


def test_application_root_uses_only_platform_composition_bootstrap():
    source = (REPO_ROOT / "src/infra/composition/app_container.py").read_text(encoding="utf-8")
    platform_composition_imports = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
        and node.module
        and node.module.startswith("src.core.platform.infrastructure.composition")
    }
    assert platform_composition_imports == {
        "src.core.platform.infrastructure.composition.bootstrap"
    }


def test_platform_composition_groups_extracted_wiring_by_capability():
    composition = REPO_ROOT / "src/core/platform/infrastructure/composition"
    for path in (
        "dependencies/master_data/employee.py",
        "dependencies/master_data/catalog.py",
        "dependencies/security/auth.py",
        "dependencies/tenancy/context.py",
        "dependencies/tenancy/modules.py",
        "dependencies/tenancy/membership.py",
        "dependencies/master_data/organization.py",
        "dependencies/security/governance.py",
        "dependencies/security/administration.py",
        "dependencies/history/services.py",
        "dependencies/finance/period.py",
        "dependencies/tenancy/admin.py",
        "dependencies/master_data/exchange.py",
        "dependencies/notifications/delivery.py",
        "dependencies/approvals/approval.py",
        "dependencies/time/calendar.py",
        "registrations/security/scope_resolvers.py",
        "registrations/tenancy/local_defaults.py",
        "events/master_data/view_invalidation.py",
        "events/security/view_invalidation.py",
        "events/tenancy/view_invalidation.py",
        "events/notifications/approval_notifications.py",
        "events/approvals/view_invalidation.py",
    ):
        assert (composition / path).is_file(), path
    for stale in ("master_data", "security", "tenancy", "notifications", "approvals"):
        assert not (composition / "events" / f"{stale}.py").exists()

