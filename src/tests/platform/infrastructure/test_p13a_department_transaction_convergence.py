from __future__ import annotations

import pytest

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    ValidationError,
)
from src.core.platform.contract.use_cases.master_data.department.commands import (
    DepartmentCreateCommand,
    DepartmentUpdateCommand,
)
from src.core.platform.contract.use_cases.master_data.employee.commands import (
    EmployeeCreateCommand,
)
from src.core.platform.contract.use_cases.master_data.site.commands import (
    SiteCreateCommand,
)
from src.core.platform.domain.master_data.department.events import (
    DepartmentCreated,
    DepartmentProfileUpdated,
)
from src.core.platform.infrastructure.persistence.uow.master_data.department_unit_of_work import (
    SqlAlchemyDepartmentUnitOfWork,
)

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _spy(services, event_type):
    calls = []
    services["department_commands"]._uow_factory._post_commit_bus.subscribe(
        event_type, lambda event, context: calls.append(event)
    )
    return calls


def test_two_independent_create_department_calls_use_genuinely_different_sessions(services, monkeypatch):
    created_sessions = []
    original_create = type(services["department_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        created_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(services["department_commands"]._uow_factory), "create", _spy_create)

    services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("FRESH-A"), name="Fresh A"))
    services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("FRESH-B"), name="Fresh B"))

    assert len(created_sessions) == 2
    assert created_sessions[0] is not created_sessions[1]
    assert all(s is not services["session"] for s in created_sessions)


def test_create_department_repository_and_audit_share_the_uow_session(services, monkeypatch):
    seen = {}
    original_create = type(services["department_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["departments_repo_session"] = uow.departments.session
        seen["sites_repo_session"] = uow.sites.session
        seen["employees_repo_session"] = uow.employees.session
        seen["audit_session"] = uow._enterprise_audit_service._session
        return uow

    monkeypatch.setattr(type(services["department_commands"]._uow_factory), "create", _spy_create)

    services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("SHARE"), name="Shared Session Department"))

    assert seen["uow_session"] is seen["departments_repo_session"]
    assert seen["uow_session"] is seen["sites_repo_session"]
    assert seen["uow_session"] is seen["employees_repo_session"]
    assert seen["uow_session"] is seen["audit_session"]


def test_create_department_success_commits_and_records_event_only_after_commit(services):
    calls = _spy(services, DepartmentCreated)

    code = _unique_code("CREATE-OK")
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=code, name="Create Ok"))

    assert department.department_code == code
    assert [e.department_id for e in calls] == [department.id]
    reloaded = services["department_query"]._department_repo.get(department.id)
    assert reloaded is not None
    assert reloaded.department_code == code


def test_update_department_success_commits_and_records_event_only_after_commit(services):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("UPDATE-OK"), name="Before Update"))
    calls = _spy(services, DepartmentProfileUpdated)

    updated = services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, name="After Update", expected_version=department.version))

    assert updated.name == "After Update"
    assert [e.department_id for e in calls] == [updated.id]
    reloaded = services["department_query"]._department_repo.get(department.id)
    assert reloaded.name == "After Update"


def test_create_department_duplicate_code_validation_failure_rolls_back_and_records_nothing(services, monkeypatch):
    code = _unique_code("DUPE")
    services["department_commands"].create_department(DepartmentCreateCommand(department_code=code, name="First"))

    captured_uow = {}
    original_create = type(services["department_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(services["department_commands"]._uow_factory), "create", _spy_create)
    calls = _spy(services, DepartmentCreated)

    with pytest.raises(ValidationError, match="Department code already exists"):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=code, name="Second"))

    uow = captured_uow["uow"]
    assert uow._committed is False
    assert uow._closed is True
    assert calls == []


def test_update_department_duplicate_code_validation_failure_rolls_back_and_records_nothing(services):
    existing_code = _unique_code("DUPE-UPDATE-EXISTING")
    services["department_commands"].create_department(DepartmentCreateCommand(department_code=existing_code, name="Existing"))
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("DUPE-UPDATE-TARGET"), name="Target"))
    calls = _spy(services, DepartmentProfileUpdated)

    with pytest.raises(ValidationError, match="Department code already exists"):
        services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, department_code=existing_code, expected_version=department.version))

    reloaded = services["department_query"]._department_repo.get(department.id)
    assert reloaded.department_code != existing_code
    assert calls == []


def test_update_department_cannot_be_its_own_parent_rolls_back_and_records_nothing(services):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("SELF-PARENT"), name="Self Parent"))
    calls = _spy(services, DepartmentProfileUpdated)

    with pytest.raises(ValidationError, match="cannot be its own parent"):
        services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, parent_department_id=department.id, expected_version=department.version))

    assert calls == []


def test_create_department_cross_organization_parent_denied_and_records_nothing(services):
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    other_organization = services["organization_commands"].create_organization(
        organization_code=_unique_code("DEPT-CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    foreign_parent = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("FOREIGN-PARENT"), name="Foreign Parent"))
    tenant_context_service.set_active_organization(default_organization.id)

    calls = _spy(services, DepartmentCreated)
    with pytest.raises(ValidationError, match="Parent department must belong to the active organization"):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("DEPT-CROSSORG-CHILD"), name="Child", parent_department_id=foreign_parent.id))

    assert calls == []


def test_create_department_cross_organization_site_denied_and_records_nothing(services):
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    other_organization = services["organization_commands"].create_organization(
        organization_code=_unique_code("DEPT-SITE-CROSSORG-OTHER"),
        display_name="Other Org For Site",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    foreign_site = services["site_commands"].create_site(SiteCreateCommand(site_code=_unique_code("FOREIGN-SITE"), name="Foreign Site"))
    tenant_context_service.set_active_organization(default_organization.id)

    calls = _spy(services, DepartmentCreated)
    with pytest.raises(ValidationError, match="Department site must belong to the active organization"):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("DEPT-SITE-CROSSORG-CHILD"), name="Child Of Foreign Site", site_id=foreign_site.id))

    assert calls == []


def test_create_department_invalid_head_of_department_employee_denied_and_records_nothing(services):
    calls = _spy(services, DepartmentCreated)

    with pytest.raises(ValidationError, match="Department Head of Department must reference an existing employee"):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("BADHOD"), name="Bad HOD Dept", head_of_department_employee_id="does-not-exist"))

    assert calls == []


def test_create_department_same_org_but_different_department_head_of_department_rejected(services):
    """A brand-new department has no id any employee could already
    reference -- Create never accepts an HOD, even one from the same
    organization. Assignment is an Edit-only step once an employee is
    actually scoped to this exact department (see the Update tests below)."""
    home_department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("SAMEORG-HOD-HOME"), name="Same Org HOD Home Dept"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("HOD-SAMEORG"), full_name="Same Org Head of Department", department_id=home_department.id))

    with pytest.raises(ValidationError, match="must be an employee assigned to this department"):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("SAMEORG-HOD-DEPT"), name="Same Org HOD Dept", head_of_department_employee_id=employee.id))


def test_create_department_cross_organization_head_of_department_denied_and_records_nothing(services):
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    other_organization = services["organization_commands"].create_organization(
        organization_code=_unique_code("DEPT-HOD-CROSSORG-OTHER"),
        display_name="Other Org For HOD",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    foreign_home_department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("FOREIGN-HOD-HOME"), name="Foreign HOD Home Dept"))
    foreign_head_of_department = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("FOREIGN-HOD"), full_name="Foreign Head of Department", department_id=foreign_home_department.id))
    tenant_context_service.set_active_organization(default_organization.id)

    calls = _spy(services, DepartmentCreated)

    with pytest.raises(ValidationError, match="Department Head of Department must reference an existing employee"):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("DEPT-HOD-CROSSORG-CHILD"), name="Dept With Foreign HOD", head_of_department_employee_id=foreign_head_of_department.id))

    assert calls == []


def test_update_department_cross_organization_head_of_department_denied_and_records_nothing(services):
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("DEPT-HOD-UPDATE-CROSSORG"), name="Dept For HOD Update"))

    other_organization = services["organization_commands"].create_organization(
        organization_code=_unique_code("DEPT-HOD-UPDATE-CROSSORG-OTHER"),
        display_name="Other Org For HOD Update",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    foreign_home_department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("FOREIGN-HOD-UPDATE-HOME"), name="Foreign HOD Update Home Dept"))
    foreign_head_of_department = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("FOREIGN-HOD-UPDATE"), full_name="Foreign Head of Department Update", department_id=foreign_home_department.id))
    tenant_context_service.set_active_organization(default_organization.id)

    calls = _spy(services, DepartmentProfileUpdated)
    with pytest.raises(ValidationError, match="Department Head of Department must reference an existing employee"):
        services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, head_of_department_employee_id=foreign_head_of_department.id, expected_version=department.version))

    assert calls == []
    reloaded = services["department_query"]._department_repo.get(department.id)
    assert reloaded.head_of_department_employee_id is None


def test_update_department_unchanged_head_of_department_remains_valid(services):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("HOD-UNCHANGED-DEPT"), name="Before"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("HOD-UNCHANGED"), full_name="Unchanged Head of Department", department_id=department.id))
    department = services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, head_of_department_employee_id=employee.id, expected_version=department.version))
    assert department.head_of_department_employee_id == employee.id

    updated = services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, name="After", expected_version=department.version))

    assert updated.head_of_department_employee_id == employee.id
    assert updated.name == "After"


def test_update_department_head_of_department_can_be_cleared(services):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("HOD-CLEAR-DEPT"), name="Clear HOD Dept"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("HOD-CLEAR"), full_name="Clearable Head of Department", department_id=department.id))
    department = services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, head_of_department_employee_id=employee.id, expected_version=department.version))
    assert department.head_of_department_employee_id == employee.id

    updated = services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, head_of_department_employee_id="", expected_version=department.version))

    assert updated.head_of_department_employee_id is None


def test_update_department_stale_version_raises_and_does_not_mutate(services):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("STALE"), name="Stale Department"))

    with pytest.raises(ConcurrencyError):
        services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, name="Should Not Apply", expected_version=department.version + 1))

    reloaded = services["department_query"]._department_repo.get(department.id)
    assert reloaded.name == "Stale Department"


def test_create_department_authorization_failure_opens_no_uow(services, monkeypatch):
    original_create = type(services["department_commands"]._uow_factory).create
    create_calls = []

    def _spy_create(self, *, context):
        create_calls.append(1)
        return original_create(self, context=context)

    monkeypatch.setattr(type(services["department_commands"]._uow_factory), "create", _spy_create)

    def _deny(*args, **kwargs):
        raise BusinessRuleError("Permission denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.department.commands.department_commands.require_permission",
        _deny,
    )

    with pytest.raises(BusinessRuleError):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("AUTHFAIL"), name="No Access"))

    assert create_calls == []


def test_update_department_authorization_failure_opens_no_uow(services, monkeypatch):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("AUTHFAIL-UPDATE"), name="Before Deny"))

    original_create = type(services["department_commands"]._uow_factory).create
    create_calls = []

    def _spy_create(self, *, context):
        create_calls.append(1)
        return original_create(self, context=context)

    monkeypatch.setattr(type(services["department_commands"]._uow_factory), "create", _spy_create)

    def _deny(*args, **kwargs):
        raise BusinessRuleError("Permission denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.department.commands.department_commands.require_permission",
        _deny,
    )

    with pytest.raises(BusinessRuleError):
        services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, name="Should Not Apply"))

    assert create_calls == []
    reloaded = services["department_query"]._department_repo.get(department.id)
    assert reloaded.name == "Before Deny"


def test_create_department_audit_failure_rolls_back_and_records_nothing(services, monkeypatch):
    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated create_department audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    calls = _spy(services, DepartmentCreated)
    code = _unique_code("AUDITFAIL-CREATE")

    with pytest.raises(RuntimeError, match="simulated create_department audit failure"):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=code, name="Audit Fail"))

    monkeypatch.undo()
    assert services["department_query"]._department_repo.get_by_code(
        services["tenant_context_service"].get_active_organization().id, code
    ) is None
    assert calls == []


def test_update_department_audit_failure_rolls_back_and_records_nothing(services, monkeypatch):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("AUDITFAIL-UPDATE"), name="Before Audit Fail"))

    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated update_department audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    calls = _spy(services, DepartmentProfileUpdated)

    with pytest.raises(RuntimeError, match="simulated update_department audit failure"):
        services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, name="Should Not Apply", expected_version=department.version))

    monkeypatch.undo()
    reloaded = services["department_query"]._department_repo.get(department.id)
    assert reloaded.name == "Before Audit Fail"
    assert calls == []


def test_create_department_commit_failure_leaves_no_partial_state_and_records_nothing(services, monkeypatch):

    captured_uow = {}
    original_create = type(services["department_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(services["department_commands"]._uow_factory), "create", _spy_create)

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyDepartmentUnitOfWork, "commit", _fail_commit)
    calls = _spy(services, DepartmentCreated)

    code = _unique_code("COMMITFAIL")
    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code=code, name="Commit Fail"))

    uow = captured_uow["uow"]
    assert uow._committed is False, "commit() failing must never mark the UoW committed"
    assert uow._closed is True, "the UoW's own __exit__ must still roll back and close"
    assert calls == []


def test_update_department_commit_failure_leaves_no_partial_state_and_records_nothing(services, monkeypatch):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("COMMITFAIL-UPDATE"), name="Before Commit Fail"))

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyDepartmentUnitOfWork, "commit", _fail_commit)
    calls = _spy(services, DepartmentProfileUpdated)

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, name="Should Not Apply", expected_version=department.version))

    reloaded = services["department_query"]._department_repo.get(department.id)
    assert reloaded.name == "Before Commit Fail"
    assert calls == []


def test_no_global_mutation_session_touch_during_migrated_create(services):
    legacy_session = services["session"]
    legacy_session.commit()

    services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("ISOLATED"), name="Isolated Department"))

    assert len(legacy_session.new) == 0
    assert len(legacy_session.dirty) == 0


def test_update_department_uses_a_fresh_uow_distinct_from_the_legacy_session(services, monkeypatch):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("FRESH-UPDATE"), name="Before Update"))

    seen = {}
    original_create = type(services["department_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        return uow

    monkeypatch.setattr(type(services["department_commands"]._uow_factory), "create", _spy_create)

    updated = services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, name="After Update", expected_version=department.version))

    assert updated.name == "After Update"
    assert seen["uow_session"] is not services["session"]
