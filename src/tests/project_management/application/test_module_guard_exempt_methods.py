from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop.resources.api import (
    ProjectManagementResourcesDesktopApi,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.dashboard.services.dashboard_service import (
    DashboardService,
)
from src.core.modules.project_management.application.resources.catalog.resource_service import (
    ResourceService,
)
from src.core.modules.project_management.application.resources.project_resources.project_resource_service import (
    ProjectResourceService,
)
from src.core.modules.project_management.application.risk.register_service import (
    RegisterService,
)
from src.core.modules.project_management.application.tasks.service import TaskService
from src.core.modules.project_management.domain.risk.register import RegisterEntryType
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


def test_register_write_facade_still_checks_module_before_handler() -> None:
    service = RegisterService(
        project_repo=object(),
        register_repo=object(),
        module_catalog_service=_module_catalog(runtime_enabled=False),
        lifecycle_handler=object(),
    )
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        service.create_entry("project-1", entry_type=RegisterEntryType.RISK, title="Risk")


def test_project_resource_read_facade_still_checks_module_before_handler() -> None:
    service = ProjectResourceService(
        command_handler=object(),
        query_handler=object(),
        module_catalog_service=_module_catalog(runtime_enabled=False),
    )
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        service.list_by_project("project-1")
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        service.add_to_project("project-1", "resource-1")


def test_task_detail_query_facade_checks_module_before_handler() -> None:
    service = TaskService.__new__(TaskService)
    service._module_catalog_service = _module_catalog(runtime_enabled=False)
    service._detail_query = SimpleNamespace(get_task=lambda _task_id: pytest.fail("handler called"))
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        service.get_task("task-1")


def test_dashboard_capability_consumer_keeps_module_gate() -> None:
    dashboard = DashboardService.__new__(DashboardService)
    dashboard._module_catalog_service = _module_catalog(runtime_enabled=False)
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        dashboard.get_dashboard_data("project-1")


def test_csv_import_capability_consumer_keeps_module_gate() -> None:
    imports = DataImportService.__new__(DataImportService)
    imports._module_catalog_service = _module_catalog(runtime_enabled=False)
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        imports.get_import_schema("tasks")


def test_resource_capability_query_facade_checks_module_before_handler() -> None:
    service = ResourceService(
        resource_repo=object(),
        master_command_handler=object(),
        capability_command_handler=object(),
        module_catalog_service=_module_catalog(runtime_enabled=False),
    )
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        service.add_resource_skill("resource-1", "planning", "Planning")
    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        service.create_resource("Resource")


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
