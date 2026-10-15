from __future__ import annotations

import pytest

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.application.master_data.department.dto.commands.department import (
    DepartmentCreateCommand,
)
from src.core.platform.application.master_data.employee.dto.commands.employee import (
    EmployeeCreateCommand,
    EmployeeUpdateCommand,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.domain.master_data.employee.events import (
    EmployeeCreated,
    EmployeeProfileUpdated,
)
from src.core.platform.infrastructure.persistence.uow.master_data.employee_unit_of_work import (
    SqlAlchemyEmployeeUnitOfWork,
)

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _spy(services, event_type):
    calls = []
    services["employee_commands"]._uow_factory._post_commit_bus.subscribe(
        event_type, lambda event, context: calls.append(event)
    )
    return calls


@pytest.fixture
def department_id(services) -> str:
    """These tests exercise UnitOfWork/transaction behavior, not department
    semantics -- one throwaway department per test satisfies Employee's
    required department_id."""
    return services["department_commands"].create_department(DepartmentCreateCommand(department_code=_unique_code("DEPT"), name="Convergence Test Department")).id


def test_two_independent_create_employee_calls_use_genuinely_different_sessions(services, monkeypatch, department_id):
    created_sessions = []
    original_create = type(services["employee_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        created_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(services["employee_commands"]._uow_factory), "create", _spy_create)

    services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("FRESH-A"), full_name="Fresh A", department_id=department_id))
    services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("FRESH-B"), full_name="Fresh B", department_id=department_id))

    assert len(created_sessions) == 2
    assert created_sessions[0] is not created_sessions[1]
    assert all(s is not services["session"] for s in created_sessions)


def test_create_employee_repository_and_audit_share_the_uow_session(services, monkeypatch, department_id):
    seen = {}
    original_create = type(services["employee_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["employees_repo_session"] = uow.employees.session
        seen["audit_session"] = uow._enterprise_audit_service._session
        return uow

    monkeypatch.setattr(type(services["employee_commands"]._uow_factory), "create", _spy_create)

    services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("SHARE"), full_name="Shared Session Employee", department_id=department_id))

    assert seen["uow_session"] is seen["employees_repo_session"]
    assert seen["uow_session"] is seen["audit_session"]


def test_create_employee_success_commits_and_records_event_only_after_commit(services, department_id):
    calls = _spy(services, EmployeeCreated)

    code = _unique_code("CREATE-OK")
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=code, full_name="Create Ok", department_id=department_id))

    assert employee.employee_code == code
    assert [e.employee_id for e in calls] == [employee.id]
    reloaded = services["employee_query"]._employee_repo.get(employee.id)
    assert reloaded is not None
    assert reloaded.employee_code == code


def test_update_employee_success_commits_and_records_event_only_after_commit(services, department_id):
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("UPDATE-OK"), full_name="Before Update", department_id=department_id))
    calls = _spy(services, EmployeeProfileUpdated)

    updated = services["employee_commands"].update_employee(EmployeeUpdateCommand(employee_id=employee.id, full_name="After Update", expected_version=employee.version))

    assert updated.full_name == "After Update"
    assert [e.employee_id for e in calls] == [updated.id]
    reloaded = services["employee_query"]._employee_repo.get(employee.id)
    assert reloaded.full_name == "After Update"


def test_create_employee_duplicate_code_validation_failure_rolls_back_and_records_nothing(services, monkeypatch, department_id):
    code = _unique_code("DUPE")
    services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=code, full_name="First", department_id=department_id))

    captured_uow = {}
    original_create = type(services["employee_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(services["employee_commands"]._uow_factory), "create", _spy_create)
    calls = _spy(services, EmployeeCreated)

    with pytest.raises(ValidationError, match="Employee code already exists"):
        services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=code, full_name="Second", department_id=department_id))

    uow = captured_uow["uow"]
    assert uow._committed is False
    assert uow._closed is True
    assert calls == []


def test_update_employee_duplicate_code_validation_failure_rolls_back_and_records_nothing(services, department_id):
    existing_code = _unique_code("DUPE-UPDATE-EXISTING")
    services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=existing_code, full_name="Existing", department_id=department_id))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("DUPE-UPDATE-TARGET"), full_name="Target", department_id=department_id))
    calls = _spy(services, EmployeeProfileUpdated)

    with pytest.raises(ValidationError, match="Employee code already exists"):
        services["employee_commands"].update_employee(EmployeeUpdateCommand(employee_id=employee.id, employee_code=existing_code, expected_version=employee.version))

    reloaded = services["employee_query"]._employee_repo.get(employee.id)
    assert reloaded.employee_code != existing_code
    assert calls == []


def test_update_employee_stale_version_raises_and_does_not_mutate(services, department_id):
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("STALE"), full_name="Stale Employee", department_id=department_id))

    with pytest.raises(ConcurrencyError):
        services["employee_commands"].update_employee(EmployeeUpdateCommand(employee_id=employee.id, full_name="Should Not Apply", expected_version=employee.version + 1))

    reloaded = services["employee_query"]._employee_repo.get(employee.id)
    assert reloaded.full_name == "Stale Employee"


def test_create_employee_authorization_failure_opens_no_uow(services, monkeypatch, department_id):
    original_create = type(services["employee_commands"]._uow_factory).create
    create_calls = []

    def _spy_create(self, *, context):
        create_calls.append(1)
        return original_create(self, context=context)

    monkeypatch.setattr(type(services["employee_commands"]._uow_factory), "create", _spy_create)

    def _deny(*args, **kwargs):
        raise BusinessRuleError("Permission denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.employee.commands.employee_commands.require_permission",
        _deny,
    )

    with pytest.raises(BusinessRuleError):
        services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("AUTHFAIL"), full_name="No Access", department_id=department_id))

    assert create_calls == []


def test_update_employee_authorization_failure_opens_no_uow(services, monkeypatch, department_id):
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("AUTHFAIL-UPDATE"), full_name="Before Deny", department_id=department_id))

    original_create = type(services["employee_commands"]._uow_factory).create
    create_calls = []

    def _spy_create(self, *, context):
        create_calls.append(1)
        return original_create(self, context=context)

    monkeypatch.setattr(type(services["employee_commands"]._uow_factory), "create", _spy_create)

    def _deny(*args, **kwargs):
        raise BusinessRuleError("Permission denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.employee.commands.employee_commands.require_permission",
        _deny,
    )

    with pytest.raises(BusinessRuleError):
        services["employee_commands"].update_employee(EmployeeUpdateCommand(employee_id=employee.id, full_name="Should Not Apply"))

    assert create_calls == []
    reloaded = services["employee_query"]._employee_repo.get(employee.id)
    assert reloaded.full_name == "Before Deny"


def test_cross_organization_update_is_denied_as_not_found(services, department_id):
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("CROSSORG"), full_name="Home Org Employee", department_id=department_id))

    other_organization = services["organization_commands"].create_organization(
        organization_code=_unique_code("CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    try:
        with pytest.raises(NotFoundError):
            services["employee_commands"].update_employee(EmployeeUpdateCommand(employee_id=employee.id, full_name="Hijacked"))
    finally:
        tenant_context_service.set_active_organization(default_organization.id)

    reloaded = services["employee_query"]._employee_repo.get(employee.id)
    assert reloaded.full_name == "Home Org Employee"


def test_create_employee_audit_failure_rolls_back_and_records_nothing(services, monkeypatch, department_id):
    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated create_employee audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    calls = _spy(services, EmployeeCreated)
    code = _unique_code("AUDITFAIL-CREATE")

    with pytest.raises(RuntimeError, match="simulated create_employee audit failure"):
        services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=code, full_name="Audit Fail", department_id=department_id))

    monkeypatch.undo()
    assert services["employee_query"]._employee_repo.get_by_code(code) is None
    assert calls == []


def test_update_employee_audit_failure_rolls_back_and_records_nothing(services, monkeypatch, department_id):
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("AUDITFAIL-UPDATE"), full_name="Before Audit Fail", department_id=department_id))

    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated update_employee audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    calls = _spy(services, EmployeeProfileUpdated)

    with pytest.raises(RuntimeError, match="simulated update_employee audit failure"):
        services["employee_commands"].update_employee(EmployeeUpdateCommand(employee_id=employee.id, full_name="Should Not Apply", expected_version=employee.version))

    monkeypatch.undo()
    reloaded = services["employee_query"]._employee_repo.get(employee.id)
    assert reloaded.full_name == "Before Audit Fail"
    assert calls == []


def test_create_employee_commit_failure_leaves_no_partial_state_and_records_nothing(services, monkeypatch, department_id):

    captured_uow = {}
    original_create = type(services["employee_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(services["employee_commands"]._uow_factory), "create", _spy_create)

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyEmployeeUnitOfWork, "commit", _fail_commit)
    calls = _spy(services, EmployeeCreated)

    code = _unique_code("COMMITFAIL")
    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=code, full_name="Commit Fail", department_id=department_id))

    uow = captured_uow["uow"]
    assert uow._committed is False, "commit() failing must never mark the UoW committed"
    assert uow._closed is True, "the UoW's own __exit__ must still roll back and close"
    assert services["employee_query"]._employee_repo.get_by_code(code) is None
    assert calls == []


def test_update_employee_commit_failure_leaves_no_partial_state_and_records_nothing(services, monkeypatch, department_id):
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("COMMITFAIL-UPDATE"), full_name="Before Commit Fail", department_id=department_id))

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyEmployeeUnitOfWork, "commit", _fail_commit)
    calls = _spy(services, EmployeeProfileUpdated)

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        services["employee_commands"].update_employee(EmployeeUpdateCommand(employee_id=employee.id, full_name="Should Not Apply", expected_version=employee.version))

    reloaded = services["employee_query"]._employee_repo.get(employee.id)
    assert reloaded.full_name == "Before Commit Fail"
    assert calls == []


def test_no_global_mutation_session_touch_during_migrated_create(services, department_id):
    legacy_session = services["session"]
    legacy_session.commit()

    services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("ISOLATED"), full_name="Isolated Employee", department_id=department_id))

    assert len(legacy_session.new) == 0
    assert len(legacy_session.dirty) == 0


def test_update_employee_uses_a_fresh_uow_distinct_from_the_legacy_session(services, monkeypatch, department_id):
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code=_unique_code("FRESH-UPDATE"), full_name="Before Update", department_id=department_id))

    seen = {}
    original_create = type(services["employee_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        return uow

    monkeypatch.setattr(type(services["employee_commands"]._uow_factory), "create", _spy_create)

    updated = services["employee_commands"].update_employee(EmployeeUpdateCommand(employee_id=employee.id, full_name="After Update", expected_version=employee.version))

    assert updated.full_name == "After Update"
    assert seen["uow_session"] is not services["session"]
