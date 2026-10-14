from __future__ import annotations

import inspect
import re

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.application.master_data.department.dto import (
    DepartmentCreateCommand,
    DepartmentUpdateCommand,
)
from src.core.platform.application.master_data.employee.dto import (
    EmployeeCreateCommand,
)
from src.core.platform.application.master_data.site.dto import (
    SiteCreateCommand,
)
from src.core.platform.domain.master_data.department.events import (
    DepartmentCreated,
    DepartmentProfileUpdated,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _platform_catalog(services) -> PlatformWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return PlatformWorkspaceCatalog(desktop_api_registry=registry)


def _spy(services, event_type):
    calls = []
    services["department_commands"]._uow_factory._post_commit_bus.subscribe(
        event_type, lambda event, context: calls.append(event)
    )
    return calls


def test_create_produces_exactly_one_department_created(services):
    calls = _spy(services, DepartmentCreated)
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-CREATE"), name="Engineering"))
    assert [e.department_id for e in calls] == [department.id]
    assert calls[0].organization_id == department.organization_id


def test_real_update_produces_exactly_one_department_profile_updated(services):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-UPDATE"), name="Before"))
    calls = _spy(services, DepartmentProfileUpdated)

    services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, name="After", expected_version=department.version))

    assert [e.department_id for e in calls] == [department.id]


def test_no_op_update_produces_zero_events_zero_write_zero_audit_zero_updated_at_bump(services, monkeypatch):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-NOOP"), name="Same Name", department_type="ops"))
    before = services["department_query"]._department_repo.get(department.id)
    calls = _spy(services, DepartmentProfileUpdated)
    audit_calls = []
    monkeypatch.setattr(
        EnterpriseAuditService, "record", lambda self, **kwargs: audit_calls.append(kwargs)
    )

    result = services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, name="Same Name", department_type="ops", expected_version=department.version))

    assert result.version == department.version
    assert calls == []
    assert audit_calls == []
    reloaded = services["department_query"]._department_repo.get(department.id)
    assert reloaded.version == before.version
    assert reloaded.updated_at == before.updated_at


def test_self_parent_rejection_produces_zero_event(services):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-SELFPARENT"), name="Self Parent"))
    calls = _spy(services, DepartmentProfileUpdated)

    from src.core.platform.common.exceptions import ValidationError

    with pytest.raises(ValidationError):
        services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, parent_department_id=department.id, expected_version=department.version))

    assert calls == []


def test_cross_org_parent_rejection_produces_zero_event(services):
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    other_organization = services["organization_commands"].create_organization(
        organization_code=_unique_code("P13B-PARENT-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    foreign_parent = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-FOREIGN-PARENT"), name="Foreign Parent"))
    tenant_context_service.set_active_organization(default_organization.id)

    calls = _spy(services, DepartmentCreated)
    from src.core.platform.common.exceptions import ValidationError

    with pytest.raises(ValidationError):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-CROSSORG-CHILD"), name="Child", parent_department_id=foreign_parent.id))

    assert calls == []


def test_cross_org_site_rejection_produces_zero_event(services):
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    other_organization = services["organization_commands"].create_organization(
        organization_code=_unique_code("P13B-SITE-OTHER"),
        display_name="Other Org For Site",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    foreign_site = services["site_commands"].create_site(SiteCreateCommand(site_code=_unique_code("P13B-FOREIGN-SITE"), name="Foreign Site"))
    tenant_context_service.set_active_organization(default_organization.id)

    calls = _spy(services, DepartmentCreated)
    from src.core.platform.common.exceptions import ValidationError

    with pytest.raises(ValidationError):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-SITE-CHILD"), name="Child Of Foreign Site", site_id=foreign_site.id))

    assert calls == []


def test_cross_org_head_of_department_rejection_produces_zero_event(services):
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    other_organization = services["organization_commands"].create_organization(
        organization_code=_unique_code("P13B-HOD-OTHER"),
        display_name="Other Org For HOD",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    foreign_department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-FOREIGN-DEPT"), name="Foreign Department"))
    foreign_head_of_department = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("P13B-FOREIGN-HOD"), full_name="Foreign Head of Department", department_id=foreign_department.id))
    tenant_context_service.set_active_organization(default_organization.id)

    calls = _spy(services, DepartmentCreated)
    from src.core.platform.common.exceptions import ValidationError

    with pytest.raises(ValidationError):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-HOD-CHILD"), name="Dept With Foreign HOD", head_of_department_employee_id=foreign_head_of_department.id))

    assert calls == []


def test_authorization_failure_produces_zero_event(services, monkeypatch):
    calls = _spy(services, DepartmentCreated)

    from src.core.platform.common.exceptions import BusinessRuleError

    def _deny(*args, **kwargs):
        raise BusinessRuleError("Permission denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.department.commands.department_commands.require_permission",
        _deny,
    )

    with pytest.raises(BusinessRuleError):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-AUTHFAIL"), name="No Access"))

    assert calls == []


def test_stale_version_failure_produces_zero_event(services):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-STALE"), name="Stale Department"))
    calls = _spy(services, DepartmentProfileUpdated)

    from src.core.platform.common.exceptions import ConcurrencyError

    with pytest.raises(ConcurrencyError):
        services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, name="Should Not Apply", expected_version=department.version + 1))

    assert calls == []


def test_audit_failure_rolls_back_and_produces_zero_postcommit_event(services, monkeypatch):
    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated department audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    calls = _spy(services, DepartmentCreated)
    code = _unique_code("P13B-AUDITFAIL")

    with pytest.raises(RuntimeError, match="simulated department audit failure"):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=code, name="Audit Fail"))

    monkeypatch.undo()
    assert calls == []


def test_commit_failure_produces_zero_postcommit_event(services, monkeypatch):
    from src.core.platform.infrastructure.persistence.uow.master_data.department_unit_of_work import (
        SqlAlchemyDepartmentUnitOfWork,
    )

    calls = _spy(services, DepartmentCreated)

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyDepartmentUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-COMMITFAIL"), name="Commit Fail"))

    assert calls == []


def test_admin_console_department_sub_controller_refreshes_after_committed_create(services):
    catalog = _platform_catalog(services)
    catalog.adminWorkspace.departments

    refresh_calls = []
    catalog.adminWorkspace._department_controller.refresh = (
        lambda: refresh_calls.append("admin-departments") or None
    )

    services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-ADMIN-CREATE"), name="Admin Refresh Department"))

    assert refresh_calls == ["admin-departments"]


def test_admin_console_department_sub_controller_refreshes_after_committed_update(services):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-ADMIN-UPDATE"), name="Before"))

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.departments

    refresh_calls = []
    catalog.adminWorkspace._department_controller.refresh = (
        lambda: refresh_calls.append("admin-departments") or None
    )

    services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, name="After", expected_version=department.version))

    assert refresh_calls == ["admin-departments"]


def test_admin_console_no_refresh_on_no_op_update(services):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-ADMIN-NOOP"), name="Same"))

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.departments

    refresh_calls = []
    catalog.adminWorkspace._department_controller.refresh = (
        lambda: refresh_calls.append("admin-departments") or None
    )

    services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, name="Same", expected_version=department.version))

    assert refresh_calls == []


def test_admin_console_no_refresh_on_failed_transaction(services):
    code = _unique_code("P13B-ADMIN-FAILED")
    services["department_commands"].create_department(DepartmentCreateCommand(department_code=code, name="Existing"))

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.departments

    refresh_calls = []
    catalog.adminWorkspace._department_controller.refresh = (
        lambda: refresh_calls.append("admin-departments") or None
    )

    from src.core.platform.common.exceptions import ValidationError

    with pytest.raises(ValidationError):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=code, name="Duplicate"))

    assert refresh_calls == []


def test_admin_console_no_refresh_on_cross_org_validation_failure(services):
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    other_organization = services["organization_commands"].create_organization(
        organization_code=_unique_code("P13B-ADMIN-CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    foreign_parent = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-ADMIN-FOREIGN-PARENT"), name="Foreign Parent"))
    tenant_context_service.set_active_organization(default_organization.id)

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.departments

    refresh_calls = []
    catalog.adminWorkspace._department_controller.refresh = (
        lambda: refresh_calls.append("admin-departments") or None
    )

    from src.core.platform.common.exceptions import ValidationError

    with pytest.raises(ValidationError):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("P13B-ADMIN-CROSSORG-CHILD"), name="Child", parent_department_id=foreign_parent.id))

    assert refresh_calls == []


def test_departments_changed_field_and_producers_are_fully_gone():
    import src.core.platform.application.master_data.department.commands.department_commands as commands_module

    source = inspect.getsource(commands_module)
    assert "departments_changed" not in source


def test_no_forbidden_department_changed_event_name_exists():
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if re.search(r"\bDepartmentChanged\b", source):
            hits.append(normalized)
    assert hits == [], hits


def test_canonical_department_uow_retained_no_raw_session_commit():
    import src.core.platform.application.master_data.department.commands.department_commands as commands_module

    source = inspect.getsource(commands_module.DepartmentCommandHandler.create_department) + inspect.getsource(
        commands_module.DepartmentCommandHandler.update_department
    )
    assert "service._session.commit(" not in source
    assert "service._session.rollback(" not in source
    assert "uow.commit()" in source


def test_no_platform_to_business_module_concrete_infrastructure_import():
    import src.core.platform.infrastructure.persistence.uow.master_data.department_unit_of_work as infra_module

    source = inspect.getsource(infra_module)
    assert "core.modules" not in source
