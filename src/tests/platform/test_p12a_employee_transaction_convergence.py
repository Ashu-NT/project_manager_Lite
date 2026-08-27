from __future__ import annotations

import pytest

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.infrastructure.persistence.employee_unit_of_work import (
    SqlAlchemyEmployeeUnitOfWork,
)
from src.core.shared.events.domain_events import domain_events

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _spy_signal(signal):
    calls = []
    signal.connect(lambda payload: calls.append(payload))
    return calls


def test_two_independent_create_employee_calls_use_genuinely_different_sessions(services, monkeypatch):
    employee_service = services["employee_service"]
    created_sessions = []
    original_create = type(employee_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        created_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(employee_service._uow_factory), "create", _spy_create)

    employee_service.create_employee(employee_code=_unique_code("FRESH-A"), full_name="Fresh A")
    employee_service.create_employee(employee_code=_unique_code("FRESH-B"), full_name="Fresh B")

    assert len(created_sessions) == 2
    assert created_sessions[0] is not created_sessions[1]
    assert all(s is not employee_service._session for s in created_sessions)


def test_create_employee_repository_and_audit_share_the_uow_session(services, monkeypatch):
    employee_service = services["employee_service"]
    seen = {}
    original_create = type(employee_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["employees_repo_session"] = uow.employees.session
        seen["audit_session"] = uow._enterprise_audit_service._session
        return uow

    monkeypatch.setattr(type(employee_service._uow_factory), "create", _spy_create)

    employee_service.create_employee(employee_code=_unique_code("SHARE"), full_name="Shared Session Employee")

    assert seen["uow_session"] is seen["employees_repo_session"]
    assert seen["uow_session"] is seen["audit_session"]


def test_create_employee_success_commits_and_emits_only_after_commit(services):
    employee_service = services["employee_service"]
    calls = _spy_signal(domain_events.employees_changed)

    code = _unique_code("CREATE-OK")
    employee = employee_service.create_employee(employee_code=code, full_name="Create Ok")

    assert employee.employee_code == code
    assert calls == [employee.id]
    reloaded = employee_service._employee_repo.get(employee.id)
    assert reloaded is not None
    assert reloaded.employee_code == code


def test_update_employee_success_commits_and_emits_only_after_commit(services):
    employee_service = services["employee_service"]
    employee = employee_service.create_employee(
        employee_code=_unique_code("UPDATE-OK"), full_name="Before Update"
    )
    calls = _spy_signal(domain_events.employees_changed)

    updated = employee_service.update_employee(
        employee.id, full_name="After Update", expected_version=employee.version
    )

    assert updated.full_name == "After Update"
    assert calls == [updated.id]
    reloaded = employee_service._employee_repo.get(employee.id)
    assert reloaded.full_name == "After Update"


def test_create_employee_duplicate_code_validation_failure_rolls_back_and_emits_nothing(services, monkeypatch):
    employee_service = services["employee_service"]
    code = _unique_code("DUPE")
    employee_service.create_employee(employee_code=code, full_name="First")

    captured_uow = {}
    original_create = type(employee_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(employee_service._uow_factory), "create", _spy_create)
    calls = _spy_signal(domain_events.employees_changed)

    with pytest.raises(ValidationError, match="Employee code already exists"):
        employee_service.create_employee(employee_code=code, full_name="Second")

    uow = captured_uow["uow"]
    assert uow._committed is False
    assert uow._closed is True
    assert calls == []


def test_update_employee_duplicate_code_validation_failure_rolls_back_and_emits_nothing(services):
    employee_service = services["employee_service"]
    existing_code = _unique_code("DUPE-UPDATE-EXISTING")
    employee_service.create_employee(employee_code=existing_code, full_name="Existing")
    employee = employee_service.create_employee(
        employee_code=_unique_code("DUPE-UPDATE-TARGET"), full_name="Target"
    )
    calls = _spy_signal(domain_events.employees_changed)

    with pytest.raises(ValidationError, match="Employee code already exists"):
        employee_service.update_employee(
            employee.id, employee_code=existing_code, expected_version=employee.version
        )

    reloaded = employee_service._employee_repo.get(employee.id)
    assert reloaded.employee_code != existing_code
    assert calls == []


def test_update_employee_stale_version_raises_and_does_not_mutate(services):
    employee_service = services["employee_service"]
    employee = employee_service.create_employee(
        employee_code=_unique_code("STALE"), full_name="Stale Employee"
    )

    with pytest.raises(ConcurrencyError):
        employee_service.update_employee(
            employee.id, full_name="Should Not Apply", expected_version=employee.version + 1
        )

    reloaded = employee_service._employee_repo.get(employee.id)
    assert reloaded.full_name == "Stale Employee"


def test_create_employee_authorization_failure_opens_no_uow(services, monkeypatch):
    employee_service = services["employee_service"]
    original_create = type(employee_service._uow_factory).create
    create_calls = []

    def _spy_create(self, *, context):
        create_calls.append(1)
        return original_create(self, context=context)

    monkeypatch.setattr(type(employee_service._uow_factory), "create", _spy_create)

    def _deny(*args, **kwargs):
        raise BusinessRuleError("Permission denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.employee.employee_service.require_permission",
        _deny,
    )

    with pytest.raises(BusinessRuleError):
        employee_service.create_employee(employee_code=_unique_code("AUTHFAIL"), full_name="No Access")

    assert create_calls == []


def test_update_employee_authorization_failure_opens_no_uow(services, monkeypatch):
    employee_service = services["employee_service"]
    employee = employee_service.create_employee(
        employee_code=_unique_code("AUTHFAIL-UPDATE"), full_name="Before Deny"
    )

    original_create = type(employee_service._uow_factory).create
    create_calls = []

    def _spy_create(self, *, context):
        create_calls.append(1)
        return original_create(self, context=context)

    monkeypatch.setattr(type(employee_service._uow_factory), "create", _spy_create)

    def _deny(*args, **kwargs):
        raise BusinessRuleError("Permission denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.employee.employee_service.require_permission",
        _deny,
    )

    with pytest.raises(BusinessRuleError):
        employee_service.update_employee(employee.id, full_name="Should Not Apply")

    assert create_calls == []
    reloaded = employee_service._employee_repo.get(employee.id)
    assert reloaded.full_name == "Before Deny"


def test_cross_organization_update_is_denied_as_not_found(services):
    employee_service = services["employee_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    employee = employee_service.create_employee(
        employee_code=_unique_code("CROSSORG"), full_name="Home Org Employee"
    )

    other_organization = organization_service.create_organization(
        organization_code=_unique_code("CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    try:
        with pytest.raises(NotFoundError):
            employee_service.update_employee(employee.id, full_name="Hijacked")
    finally:
        tenant_context_service.set_active_organization(default_organization.id)

    reloaded = employee_service._employee_repo.get(employee.id)
    assert reloaded.full_name == "Home Org Employee"


def test_create_employee_audit_failure_rolls_back_and_emits_nothing(services, monkeypatch):
    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated create_employee audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    employee_service = services["employee_service"]
    calls = _spy_signal(domain_events.employees_changed)
    code = _unique_code("AUDITFAIL-CREATE")

    with pytest.raises(RuntimeError, match="simulated create_employee audit failure"):
        employee_service.create_employee(employee_code=code, full_name="Audit Fail")

    monkeypatch.undo()
    assert employee_service._employee_repo.get_by_code(code) is None
    assert calls == []


def test_update_employee_audit_failure_rolls_back_and_emits_nothing(services, monkeypatch):
    employee_service = services["employee_service"]
    employee = employee_service.create_employee(
        employee_code=_unique_code("AUDITFAIL-UPDATE"), full_name="Before Audit Fail"
    )

    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated update_employee audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    calls = _spy_signal(domain_events.employees_changed)

    with pytest.raises(RuntimeError, match="simulated update_employee audit failure"):
        employee_service.update_employee(
            employee.id, full_name="Should Not Apply", expected_version=employee.version
        )

    monkeypatch.undo()
    reloaded = employee_service._employee_repo.get(employee.id)
    assert reloaded.full_name == "Before Audit Fail"
    assert calls == []


def test_create_employee_commit_failure_leaves_no_partial_state_and_emits_nothing(services, monkeypatch):
    employee_service = services["employee_service"]

    captured_uow = {}
    original_create = type(employee_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(employee_service._uow_factory), "create", _spy_create)

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyEmployeeUnitOfWork, "commit", _fail_commit)
    calls = _spy_signal(domain_events.employees_changed)

    code = _unique_code("COMMITFAIL")
    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        employee_service.create_employee(employee_code=code, full_name="Commit Fail")

    uow = captured_uow["uow"]
    assert uow._committed is False, "commit() failing must never mark the UoW committed"
    assert uow._closed is True, "the UoW's own __exit__ must still roll back and close"
    assert employee_service._employee_repo.get_by_code(code) is None
    assert calls == []


def test_update_employee_commit_failure_leaves_no_partial_state_and_emits_nothing(services, monkeypatch):
    employee_service = services["employee_service"]
    employee = employee_service.create_employee(
        employee_code=_unique_code("COMMITFAIL-UPDATE"), full_name="Before Commit Fail"
    )

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyEmployeeUnitOfWork, "commit", _fail_commit)
    calls = _spy_signal(domain_events.employees_changed)

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        employee_service.update_employee(
            employee.id, full_name="Should Not Apply", expected_version=employee.version
        )

    reloaded = employee_service._employee_repo.get(employee.id)
    assert reloaded.full_name == "Before Commit Fail"
    assert calls == []


def test_no_global_mutation_session_touch_during_migrated_create(services):
    employee_service = services["employee_service"]
    legacy_session = employee_service._session
    legacy_session.commit()  # settle any pending state from fixture setup

    employee_service.create_employee(employee_code=_unique_code("ISOLATED"), full_name="Isolated Employee")

    assert len(legacy_session.new) == 0
    assert len(legacy_session.dirty) == 0


def test_update_employee_uses_a_fresh_uow_distinct_from_the_legacy_session(services, monkeypatch):
    employee_service = services["employee_service"]
    employee = employee_service.create_employee(
        employee_code=_unique_code("FRESH-UPDATE"), full_name="Before Update"
    )

    seen = {}
    original_create = type(employee_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        return uow

    monkeypatch.setattr(type(employee_service._uow_factory), "create", _spy_create)

    updated = employee_service.update_employee(
        employee.id, full_name="After Update", expected_version=employee.version
    )

    assert updated.full_name == "After Update"
    assert seen["uow_session"] is not employee_service._session


def test_admin_console_and_pm_resources_binders_still_react_to_employees_changed(services):
    from src.ui_qml.platform.controllers.admin_console.domain_event_binder import bind_domain_events as bind_admin_domain_events
    from src.ui_qml.modules.project_management.controllers.resources.resource_domain_event_binder import (
        bind_resource_domain_events,
    )

    admin_refresh_calls = []
    resource_refresh_calls = []

    class _FakeController:
        _selected_resource_id = None

        def __init__(self):
            self._domain_event_subscriptions = []

        def _subscribe_domain_signal(self, signal, callback):
            signal.connect(callback)
            self._domain_event_subscriptions.append((signal, callback))

    class _FakeAdminController(_FakeController):
        def _request_domain_refresh(self):
            admin_refresh_calls.append("refresh")

    class _FakeResourceController(_FakeController):
        def _request_domain_refresh(self):
            resource_refresh_calls.append("refresh")

    bind_admin_domain_events(_FakeAdminController())
    bind_resource_domain_events(_FakeResourceController())

    services["employee_service"].create_employee(
        employee_code=_unique_code("ADMIN-PM-REFRESH"), full_name="Admin PM Refresh Employee"
    )

    assert admin_refresh_calls == ["refresh"]
    assert resource_refresh_calls == ["refresh"]
