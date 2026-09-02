from __future__ import annotations

import inspect
import re

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.domain.enums import WorkerType
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.domain.master_data.employee.events import EmployeeCreated, EmployeeProfileUpdated
from src.core.shared.events.domain_events import domain_events
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.platform.context import PlatformWorkspaceCatalog

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _platform_catalog(services) -> PlatformWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return PlatformWorkspaceCatalog(desktop_api_registry=registry)


def _pm_catalog(services) -> ProjectManagementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)


def _spy(services, event_type):
    calls = []
    services["employee_service"]._uow_factory._post_commit_bus.subscribe(
        event_type, lambda event, context: calls.append(event)
    )
    return calls


def test_create_produces_exactly_one_employee_created(services):
    calls = _spy(services, EmployeeCreated)
    employee = services["employee_service"].create_employee(
        employee_code=_unique_code("P12B-CREATE"), full_name="Ada Lovelace"
    )
    assert [e.employee_id for e in calls] == [employee.id]
    assert calls[0].organization_id == employee.organization_id


def test_real_update_produces_exactly_one_employee_profile_updated(services):
    employee_service = services["employee_service"]
    employee = employee_service.create_employee(
        employee_code=_unique_code("P12B-UPDATE"), full_name="Before"
    )
    calls = _spy(services, EmployeeProfileUpdated)

    employee_service.update_employee(
        employee.id, full_name="After", expected_version=employee.version
    )

    assert [e.employee_id for e in calls] == [employee.id]


def test_no_op_update_produces_zero_events_zero_write_zero_audit(services, monkeypatch):
    employee_service = services["employee_service"]
    employee = employee_service.create_employee(
        employee_code=_unique_code("P12B-NOOP"), full_name="Same Name", title="Planner"
    )
    calls = _spy(services, EmployeeProfileUpdated)
    audit_calls = []
    monkeypatch.setattr(
        EnterpriseAuditService, "record", lambda self, **kwargs: audit_calls.append(kwargs)
    )

    result = employee_service.update_employee(
        employee.id,
        full_name="Same Name",
        title="Planner",
        expected_version=employee.version,
    )

    assert result.version == employee.version
    assert calls == []
    assert audit_calls == []
    reloaded = employee_service._employee_repo.get(employee.id)
    assert reloaded.version == employee.version


def test_admin_console_employee_sub_controller_refreshes_after_committed_create(services):
    catalog = _platform_catalog(services)
    catalog.adminWorkspace.employees

    refresh_calls = []
    catalog.adminWorkspace._employee_controller.refresh = (
        lambda: refresh_calls.append("admin-employees") or None
    )

    services["employee_service"].create_employee(
        employee_code=_unique_code("P12B-ADMIN"), full_name="Admin Refresh Employee"
    )

    assert refresh_calls == ["admin-employees"]


def test_admin_console_refresh_does_not_fire_before_commit_or_on_rollback(services):
    catalog = _platform_catalog(services)
    catalog.adminWorkspace.employees

    refresh_calls = []
    catalog.adminWorkspace._employee_controller.refresh = (
        lambda: refresh_calls.append("admin-employees") or None
    )

    employee_service = services["employee_service"]
    code = _unique_code("P12B-ADMIN-ROLLBACK")
    employee_service.create_employee(employee_code=code, full_name="First")

    from src.core.platform.common.exceptions import ValidationError

    with pytest.raises(ValidationError):
        employee_service.create_employee(employee_code=code, full_name="Second")

    assert refresh_calls == ["admin-employees"]


def test_pm_resources_narrow_refresh_after_committed_employee_create_with_no_linked_resource(services):
    catalog = _pm_catalog(services)
    resources_workspace = catalog.resourcesWorkspace

    narrow_calls = []
    full_calls = []
    resources_workspace.refresh_employee_options = lambda: narrow_calls.append("narrow")
    resources_workspace.refresh = lambda: full_calls.append("full")

    services["employee_service"].create_employee(
        employee_code=_unique_code("P12B-PM-NARROW"), full_name="No Linked Resource Employee"
    )

    assert narrow_calls == ["narrow"]
    assert full_calls == []


def test_no_duplicate_pm_refresh_when_employee_update_touches_a_linked_resource(services):
    employee_service = services["employee_service"]
    resource_service = services["resource_service"]
    employee = employee_service.create_employee(
        employee_code=_unique_code("P12B-LINKED"), full_name="Linked Employee", title="Planner"
    )
    resource_service.create_resource(
        "", hourly_rate=100.0, worker_type=WorkerType.EMPLOYEE, employee_id=employee.id
    )

    catalog = _pm_catalog(services)
    resources_workspace = catalog.resourcesWorkspace

    narrow_calls = []
    full_calls = []
    resources_workspace.refresh_employee_options = lambda: narrow_calls.append("narrow")
    resources_workspace.refresh = lambda: full_calls.append("full")

    employee_service.update_employee(
        employee.id, title="Senior Planner", expected_version=employee.version
    )

    assert narrow_calls == ["narrow"]
    assert full_calls == ["full"]


def test_failed_employee_transaction_produces_zero_ui_refresh(services):
    platform_catalog = _platform_catalog(services)
    platform_catalog.adminWorkspace.employees
    pm_catalog = _pm_catalog(services)

    admin_calls = []
    pm_narrow_calls = []
    pm_full_calls = []
    platform_catalog.adminWorkspace._employee_controller.refresh = (
        lambda: admin_calls.append("admin") or None
    )
    pm_catalog.resourcesWorkspace.refresh_employee_options = lambda: pm_narrow_calls.append("narrow")
    pm_catalog.resourcesWorkspace.refresh = lambda: pm_full_calls.append("full")

    employee_service = services["employee_service"]
    code = _unique_code("P12B-FAILED")
    employee_service.create_employee(employee_code=code, full_name="Existing")

    from src.core.platform.common.exceptions import ValidationError

    with pytest.raises(ValidationError):
        employee_service.create_employee(employee_code=code, full_name="Duplicate")

    assert admin_calls == ["admin"]
    assert pm_narrow_calls == ["narrow"]
    assert pm_full_calls == []


def test_employees_changed_field_and_producers_are_fully_gone():
    assert not hasattr(domain_events, "employees_changed")

    import src.core.platform.application.master_data.employee.employee_service as employee_service_module

    source = inspect.getsource(employee_service_module)
    assert "employees_changed" not in source
    # P18B: employee_service.py's own remaining `domain_events.resources_changed` reference was
    # deleted too -- Employee is fully modernized and no longer touches any legacy Signal at
    # all, direct or cross-capability. See test_p18b_resource_view_invalidation.py for the
    # typed-event replacement (ResourceMasterEventFactory + ResourceMasterChanged).


def test_no_forbidden_employee_changed_event_name_exists():
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if re.search(r"\bEmployeeChanged\b", source):
            hits.append(normalized)
    assert hits == [], hits


def test_canonical_employee_uow_retained_no_raw_session_commit():
    import src.core.platform.application.master_data.employee.employee_service as employee_service_module
    from src.core.platform.application.master_data.employee.employee_service import EmployeeService

    source = inspect.getsource(EmployeeService.create_employee) + inspect.getsource(
        EmployeeService.update_employee
    )
    assert "self._session.commit(" not in source
    assert "self._session.rollback(" not in source
    assert "uow.commit()" in source
    assert "EmployeeUnitOfWorkFactory" in inspect.getsource(employee_service_module)


def test_no_platform_to_pm_concrete_infrastructure_import():
    import src.core.platform.infrastructure.persistence.uow.employee_unit_of_work as infra_module

    source = inspect.getsource(infra_module)
    assert "core.modules.project_management" not in source
    assert "SqlAlchemyResourceRepository" not in source


# P18B superseded test_resources_changed_unchanged_and_still_the_only_pm_resource_row_signal:
# `resources_changed` itself is now deleted -- Resource Master/Capability mutations (and the
# Employee-driven sync path this P12B test cared about) emit typed ResourceMasterChanged/
# ResourceCapabilityChanged through the canonical postcommit bus, routed to the Resources
# workspace via ResourceViewInvalidationAdapter. See test_p18b_resource_view_invalidation.py
# for the current characterization, including the employee-driven-sync-produces-exactly-one-
# resource-invalidation proof this test's own docstring was gesturing at. The import-boundary
# half of the old test is unchanged and still covered by test_no_platform_to_pm_concrete_
# infrastructure_import above (re-confirmed: P18B's new ResourceMasterEventFactory wiring lives
# in employee_service.py, not this UoW infra module).
