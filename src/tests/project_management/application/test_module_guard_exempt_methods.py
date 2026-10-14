from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop.register.api import (
    ProjectManagementRegisterDesktopApi,
)
from src.core.modules.project_management.api.desktop.resources.api import (
    ProjectManagementResourcesDesktopApi,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.dashboard import (
    PortfolioDashboardQueryHandler,
    ProjectDashboardQueryHandler,
)
from src.core.modules.project_management.application.portfolio.queries.portfolio_intake import (
    PortfolioIntakeQueryHandler,
)
from src.core.modules.project_management.application.reporting import (
    EarnedValueReportBuilder,
    ReportingAccessPolicy,
)
from src.core.modules.project_management.application.resources.queries.resource_queries import (
    ResourceQueryHandler,
)
from src.core.modules.project_management.application.risk.commands.register_lifecycle import (
    RegisterLifecycleHandler,
)
from src.core.modules.project_management.application.tasks.service import TaskService
from src.core.modules.project_management.infrastructure.importers.services.data_import_service import (
    DataImportService,
)
from src.core.platform.common.exceptions import BusinessRuleError


class _GuardedService(ProjectManagementModuleGuardMixin):
    def __init__(self, module_catalog_service) -> None:
        self._module_catalog_service = module_catalog_service

    def create_task(self) -> str:
        return "created"

    def set_approved_time_dispatcher(self, dispatcher) -> None:
        self._dispatcher = dispatcher

    def consume_last_overallocation_warning(self) -> str | None:
        return None


def _module_catalog(*, runtime_enabled: bool) -> SimpleNamespace:
    entitlement = SimpleNamespace(
        runtime_enabled=runtime_enabled, label="Project Management", lifecycle_status="inactive",
    )
    return SimpleNamespace(get_entitlement=lambda _module_code: entitlement)


def test_business_methods_are_blocked_when_the_module_is_disabled() -> None:
    service = _GuardedService(_module_catalog(runtime_enabled=False))
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        service.create_task()


def test_business_methods_are_allowed_when_the_module_is_enabled() -> None:
    service = _GuardedService(_module_catalog(runtime_enabled=True))
    assert service.create_task() == "created"


def test_register_desktop_commands_check_module_before_handler() -> None:
    api = ProjectManagementRegisterDesktopApi(
        register_lifecycle_commands=object(),  # type: ignore[arg-type]
        module_catalog_service=_module_catalog(runtime_enabled=False),
    )
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        api.create_entry(
            SimpleNamespace(project_id="project-1", entry_type="RISK", title="Risk")
        )


def test_register_handler_checks_module_before_opening_uow() -> None:
    commands = RegisterLifecycleHandler(
        project_repo=object(),  # type: ignore[arg-type]
        register_repo=object(),  # type: ignore[arg-type]
        user_session=None,
        tenant_context_service=object(),  # type: ignore[arg-type]
        uow_factory=None,
        module_catalog_service=_module_catalog(runtime_enabled=False),
    )
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        commands.create_entry("project-1", entry_type="risk", title="Risk")


def test_portfolio_intake_query_checks_module_before_repository_access() -> None:
    query = PortfolioIntakeQueryHandler(
        intake_repo=object(),  # type: ignore[arg-type]
        tenant_context_service=object(),  # type: ignore[arg-type]
        module_catalog_service=_module_catalog(runtime_enabled=False),
    )
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        query.list_intake_items_page()


@pytest.mark.parametrize(
    ("key", "method"),
    [("project_resource_query", "list_by_project"), ("project_resource_commands", "delete")],
)
def test_project_resource_handlers_check_module_before_operation(services, monkeypatch, key, method):
    handler = services[key]
    monkeypatch.setattr(handler, "_module_catalog_service", _module_catalog(runtime_enabled=False))
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        getattr(handler, method)("missing-project-resource")


def test_task_detail_query_facade_checks_module_before_handler() -> None:
    service = TaskService.__new__(TaskService)
    service._module_catalog_service = _module_catalog(runtime_enabled=False)
    service._detail_query = SimpleNamespace(get_task=lambda _task_id: pytest.fail("handler called"))
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        service.get_task("task-1")


def test_direct_project_query_checks_module_before_reading(services, monkeypatch):
    query = services["project_query"]
    monkeypatch.setattr(query, "_module_catalog_service", _module_catalog(runtime_enabled=False))
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        query.list_projects()


@pytest.mark.parametrize(
    ("key", "method", "args"),
    [
        ("project_create", "create_project", ("Denied", "")),
        ("project_update", "update_project", ("missing-project",)),
        ("project_status", "set_status", ("missing-project", "ACTIVE")),
        ("project_deletion", "delete_project", ("missing-project",)),
    ],
)
def test_direct_project_commands_check_module_before_operation(services, monkeypatch, key, method, args):
    handler = services[key]
    monkeypatch.setattr(handler, "_module_catalog_service", _module_catalog(runtime_enabled=False))
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        getattr(handler, method)(*args)


def test_dashboard_capability_consumer_keeps_module_gate() -> None:
    dashboard = ProjectDashboardQueryHandler.__new__(ProjectDashboardQueryHandler)
    dashboard._module_catalog_service = _module_catalog(runtime_enabled=False)
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        dashboard.get_dashboard_data("project-1")
    portfolio = PortfolioDashboardQueryHandler.__new__(PortfolioDashboardQueryHandler)
    portfolio._module_catalog_service = _module_catalog(runtime_enabled=False)
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        portfolio.get_portfolio_data()


def test_report_builder_fed_directly_checks_module_before_reading() -> None:
    builder = EarnedValueReportBuilder(
        access=ReportingAccessPolicy(user_session=None),
        cost_policy=object(),  # type: ignore[arg-type]
        evm_series_reader=object(),  # type: ignore[arg-type]
        tenant_context_service=object(),  # type: ignore[arg-type]
        calendar=object(),  # type: ignore[arg-type]
        module_catalog_service=_module_catalog(runtime_enabled=False),
    )
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        builder.get_earned_value("project-1")


def test_csv_import_capability_consumer_keeps_module_gate() -> None:
    imports = DataImportService.__new__(DataImportService)
    imports._module_catalog_service = _module_catalog(runtime_enabled=False)
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        imports.get_import_schema("tasks")


def test_resource_query_handler_checks_module_before_repository() -> None:
    query = ResourceQueryHandler(
        resource_repo=object(),  # type: ignore[arg-type]
        module_catalog_service=_module_catalog(runtime_enabled=False),
    )
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        query.list_resources()


def test_resource_command_desktop_boundary_checks_module_before_handler() -> None:
    api = ProjectManagementResourcesDesktopApi(
        resource_master_commands=object(),  # type: ignore[arg-type]
        resource_capability_commands=object(),  # type: ignore[arg-type]
        module_catalog_service=_module_catalog(runtime_enabled=False),
    )
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        api.add_resource_skill(
            SimpleNamespace(
                resource_id="resource-1", skill_code="planning", skill_name="Planning",
                proficiency="intermediate", notes="",
            )
        )
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        api.create_resource(SimpleNamespace(name="Resource"))


def test_resource_query_desktop_boundary_checks_module_before_handler() -> None:
    api = ProjectManagementResourcesDesktopApi(
        resource_capability_query=object(),  # type: ignore[arg-type]
        resource_context_query=object(),  # type: ignore[arg-type]
        module_catalog_service=_module_catalog(runtime_enabled=False),
    )
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        api.list_resource_skills_page("resource-1")
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        api.list_resource_projects_page("resource-1")


def test_composition_root_wiring_setters_are_exempt_from_the_module_gate() -> None:
    """set_approved_time_dispatcher is called unconditionally during service
    composition at application startup, before any tenant-scoped module
    entitlement should matter -- gating it behind module enablement made the
    whole application fail to start on any installation with Project
    Management disabled."""
    service = _GuardedService(_module_catalog(runtime_enabled=False))
    service.set_approved_time_dispatcher(lambda: None)
    assert service._dispatcher is not None


def test_consume_last_overallocation_warning_remains_exempt() -> None:
    service = _GuardedService(_module_catalog(runtime_enabled=False))
    assert service.consume_last_overallocation_warning() is None
