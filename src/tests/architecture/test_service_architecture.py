import ast
from pathlib import Path

from src.core.modules.project_management.application.collaboration.commands import (
    CollaborationCommentCommandHandler,
)
from src.core.modules.project_management.application.collaboration.queries import (
    CollaborationInboxQueryHandler,
)
from src.core.modules.project_management.application.dashboard import (
    PortfolioDashboardQueryHandler,
    ProjectDashboardQueryHandler,
)
from src.core.modules.project_management.application.financials import (
    FinanceSnapshotQueryHandler,
)
from src.core.modules.project_management.application.portfolio.commands import (
    PortfolioIntakeCommandHandler,
)
from src.core.modules.project_management.application.portfolio.queries import (
    PortfolioExecutiveQueryHandler,
)
from src.core.modules.project_management.application.projects import ProjectQueryHandler
from src.core.modules.project_management.application.reporting import (
    EarnedValueReportBuilder,
    ProjectKpiReportBuilder,
)
from src.core.modules.project_management.application.resources import (
    ProjectResourceQueryHandler,
    ResourceMasterCommandHandler,
    ResourceQueryHandler,
)
from src.core.modules.project_management.application.risk import RegisterQueryHandler
from src.core.modules.project_management.application.scheduling import (
    CalendarProtocol,
    SchedulingEngine,
)
from src.core.modules.project_management.application.scheduling.baselines.queries.catalog import (
    BaselineQueryHandler,
)
from src.core.modules.project_management.application.tasks import TaskLookupQueryHandler
from src.core.modules.project_management.application.timesheets import (
    TimesheetReviewQueryHandler,
    TimesheetWorkspaceCommandHandler,
    TimesheetWorkspaceQueryHandler,
)
from src.core.modules.project_management.infrastructure.importers import (
    DataImportService,
)
from src.core.platform.access import AccessControlService
from src.core.platform.application.approval import (
    ApprovalCommandHandler,
    ApprovalQueryHandler,
)
from src.core.platform.application.data_operations.exporting import ExportRuntime
from src.core.platform.application.data_operations.importing import CsvImportRuntime
from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.master_data.department import (
    DepartmentCommandHandler,
    DepartmentQueryHandler,
)
from src.core.platform.application.master_data.documents import (
    DocumentAttachmentCommandHandler,
    DocumentAttachmentQueryHandler,
    DocumentCommandHandler,
    DocumentQueryHandler,
    DocumentStructureCommandHandler,
)
from src.core.platform.application.master_data.employee import (
    EmployeeCommandHandler,
    EmployeeQueryHandler,
)
from src.core.platform.application.master_data.org import (
    OrganizationCommandHandler,
    OrganizationLifecycleCommandHandler,
    OrganizationQueryHandler,
)
from src.core.platform.application.master_data.party import (
    PartyCommandHandler,
    PartyQueryHandler,
)
from src.core.platform.application.master_data.site import (
    SiteCommandHandler,
    SiteQueryHandler,
)
from src.core.platform.application.platform_runtime import (
    PlatformRuntimeQueryHandler,
)
from src.core.platform.application.security.auth import AuthenticationHandler
from src.core.platform.application.security.authorization.roles.commands import (
    RoleAssignmentHandler,
)
from src.core.platform.application.tenant.modules import (
    ModuleCatalogQueryHandler,
    ModuleEntitlementCommandHandler,
)
from src.core.platform.application.time_management.time import (
    TimeEntryCommandHandler,
    TimeEntryQueryHandler,
)
from src.core.platform.common.service_base import ServiceBase as LegacyServiceBase
from src.infra.composition.app_container import ServiceGraph, build_service_graph
from src.tests.path_rewrites import REPO_ROOT


def test_service_graph_builder_wires_all_services(session):
    graph = build_service_graph(session)

    assert isinstance(graph, ServiceGraph)
    assert isinstance(graph.platform.platform_runtime_query, PlatformRuntimeQueryHandler)
    assert isinstance(graph.platform.module_catalog_service, ModuleCatalogQueryHandler)
    assert isinstance(graph.platform.module_entitlement_commands, ModuleEntitlementCommandHandler)
    assert isinstance(graph.project_management.time_entry_commands, TimeEntryCommandHandler)
    assert isinstance(graph.project_management.time_entry_queries, TimeEntryQueryHandler)
    assert isinstance(graph.platform.approval_commands, ApprovalCommandHandler)
    assert isinstance(graph.platform.approval_queries, ApprovalQueryHandler)
    assert isinstance(graph.platform.auth.authentication, AuthenticationHandler)
    assert isinstance(graph.platform.role_assignment_commands, RoleAssignmentHandler)
    assert isinstance(graph.platform.organization_commands, OrganizationCommandHandler)
    assert isinstance(graph.platform.organization_lifecycle, OrganizationLifecycleCommandHandler)
    assert isinstance(graph.platform.organization_query, OrganizationQueryHandler)
    assert isinstance(graph.platform.document_commands, DocumentCommandHandler)
    assert isinstance(graph.platform.document_structure_commands, DocumentStructureCommandHandler)
    assert isinstance(graph.platform.document_query, DocumentQueryHandler)
    assert isinstance(graph.platform.document_attachment_commands, DocumentAttachmentCommandHandler)
    assert isinstance(graph.platform.document_attachment_query, DocumentAttachmentQueryHandler)
    assert isinstance(graph.platform.party_commands, PartyCommandHandler)
    assert isinstance(graph.platform.party_query, PartyQueryHandler)
    assert isinstance(graph.platform.department_commands, DepartmentCommandHandler)
    assert isinstance(graph.platform.department_query, DepartmentQueryHandler)
    assert isinstance(graph.platform.site_commands, SiteCommandHandler)
    assert isinstance(graph.platform.site_query, SiteQueryHandler)
    assert isinstance(graph.platform.employee_commands, EmployeeCommandHandler)
    assert isinstance(graph.platform.employee_query, EmployeeQueryHandler)
    assert isinstance(graph.platform.master_data_import_runtime, CsvImportRuntime)
    assert isinstance(graph.platform.master_data_export_runtime, ExportRuntime)
    assert isinstance(graph.platform.access_service, AccessControlService)
    assert isinstance(graph.platform.enterprise_audit_service, EnterpriseAuditService)
    assert isinstance(graph.project_management.collaboration_comment_commands, CollaborationCommentCommandHandler)
    assert isinstance(graph.project_management.collaboration_inbox_query, CollaborationInboxQueryHandler)
    assert isinstance(graph.project_management.project_query, ProjectQueryHandler)
    assert isinstance(graph.project_management.task_lookup_query, TaskLookupQueryHandler)
    assert isinstance(graph.project_management.timesheet_workspace_query, TimesheetWorkspaceQueryHandler)
    assert isinstance(graph.project_management.timesheet_workspace_commands, TimesheetWorkspaceCommandHandler)
    assert isinstance(graph.project_management.timesheet_review_query, TimesheetReviewQueryHandler)
    assert isinstance(graph.project_management.resource_query, ResourceQueryHandler)
    assert isinstance(graph.project_management.resource_master_commands, ResourceMasterCommandHandler)
    assert isinstance(graph.project_management.finance_snapshot_query, FinanceSnapshotQueryHandler)
    # work_calendar_engine is now GlobalCalendarShim (enterprise-backed)
    assert hasattr(graph.project_management, "work_calendar_engine") and graph.project_management.work_calendar_engine is not None
    assert isinstance(graph.project_management.work_calendar_engine, CalendarProtocol)
    assert isinstance(graph.project_management.scheduling_engine, SchedulingEngine)
    assert isinstance(graph.project_management.project_kpi_report, ProjectKpiReportBuilder)
    assert isinstance(graph.project_management.earned_value_report, EarnedValueReportBuilder)
    assert isinstance(graph.project_management.baseline_query, BaselineQueryHandler)
    assert isinstance(graph.project_management.project_dashboard_query, ProjectDashboardQueryHandler)
    assert isinstance(graph.project_management.portfolio_dashboard_query, PortfolioDashboardQueryHandler)
    assert isinstance(graph.project_management.portfolio_intake_commands, PortfolioIntakeCommandHandler)
    assert isinstance(graph.project_management.portfolio_executive_query, PortfolioExecutiveQueryHandler)
    assert isinstance(graph.project_management.register_query, RegisterQueryHandler)
    assert isinstance(graph.project_management.project_resource_query, ProjectResourceQueryHandler)
    assert isinstance(graph.project_management.data_import_service, DataImportService)

    as_dict = graph.as_dict()
    assert as_dict["approval_commands"] is graph.platform.approval_commands
    assert as_dict["approval_queries"] is graph.platform.approval_queries
    assert as_dict["authentication"] is graph.platform.auth.authentication
    assert as_dict["principal_builder"] is graph.platform.auth.principals
    assert as_dict["platform_runtime_query"] is graph.platform.platform_runtime_query
    assert as_dict["organization_query"] is graph.platform.organization_query
    assert as_dict["document_query"] is graph.platform.document_query
    assert as_dict["party_query"] is graph.platform.party_query
    assert as_dict["department_query"] is graph.platform.department_query
    assert as_dict["site_query"] is graph.platform.site_query
    assert as_dict["employee_query"] is graph.platform.employee_query
    assert as_dict["master_data_import_runtime"] is graph.platform.master_data_import_runtime
    assert as_dict["master_data_export_runtime"] is graph.platform.master_data_export_runtime
    assert as_dict["module_catalog_service"] is graph.platform.module_catalog_service
    assert as_dict["time_entry_commands"] is graph.project_management.time_entry_commands
    assert as_dict["time_entry_queries"] is graph.project_management.time_entry_queries
    assert as_dict["access_service"] is graph.platform.access_service
    assert as_dict["enterprise_audit_service"] is graph.platform.enterprise_audit_service
    assert as_dict["collaboration_comment_commands"] is graph.project_management.collaboration_comment_commands
    assert as_dict["collaboration_inbox_query"] is graph.project_management.collaboration_inbox_query
    assert as_dict["project_dashboard_query"] is graph.project_management.project_dashboard_query
    assert as_dict["portfolio_dashboard_query"] is graph.project_management.portfolio_dashboard_query
    assert as_dict["resource_query"] is graph.project_management.resource_query
    assert as_dict["earned_value_report"] is graph.project_management.earned_value_report
    assert as_dict["finance_snapshot_query"] is graph.project_management.finance_snapshot_query
    assert as_dict["portfolio_intake_commands"] is graph.project_management.portfolio_intake_commands
    assert as_dict["portfolio_executive_query"] is graph.project_management.portfolio_executive_query
    assert as_dict["register_query"] is graph.project_management.register_query
    assert as_dict["project_resource_query"] is graph.project_management.project_resource_query
    assert as_dict["timesheet_workspace_query"] is graph.project_management.timesheet_workspace_query
    assert as_dict["session"] is session
    assert graph.project_management.timesheet_workspace_commands._time_entries is graph.project_management.time_entry_commands
    assert graph.project_management.timesheet_workspace_commands._entry_queries is graph.project_management.time_entry_queries
    assert graph.project_management.timesheet_workspace_commands._period_transitions is graph.project_management.timesheet_period_transitions


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

