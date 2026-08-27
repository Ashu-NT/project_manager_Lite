from __future__ import annotations

import pytest

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.infrastructure.persistence.uow.department_unit_of_work import (
    SqlAlchemyDepartmentUnitOfWork,
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


def test_two_independent_create_department_calls_use_genuinely_different_sessions(services, monkeypatch):
    department_service = services["department_service"]
    created_sessions = []
    original_create = type(department_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        created_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(department_service._uow_factory), "create", _spy_create)

    department_service.create_department(department_code=_unique_code("FRESH-A"), name="Fresh A")
    department_service.create_department(department_code=_unique_code("FRESH-B"), name="Fresh B")

    assert len(created_sessions) == 2
    assert created_sessions[0] is not created_sessions[1]
    assert all(s is not department_service._session for s in created_sessions)


def test_create_department_repository_and_audit_share_the_uow_session(services, monkeypatch):
    department_service = services["department_service"]
    seen = {}
    original_create = type(department_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["departments_repo_session"] = uow.departments.session
        seen["sites_repo_session"] = uow.sites.session
        seen["employees_repo_session"] = uow.employees.session
        seen["audit_session"] = uow._enterprise_audit_service._session
        return uow

    monkeypatch.setattr(type(department_service._uow_factory), "create", _spy_create)

    department_service.create_department(
        department_code=_unique_code("SHARE"), name="Shared Session Department"
    )

    assert seen["uow_session"] is seen["departments_repo_session"]
    assert seen["uow_session"] is seen["sites_repo_session"]
    assert seen["uow_session"] is seen["employees_repo_session"]
    assert seen["uow_session"] is seen["audit_session"]


def test_create_department_success_commits_and_emits_only_after_commit(services):
    department_service = services["department_service"]
    calls = _spy_signal(domain_events.departments_changed)

    code = _unique_code("CREATE-OK")
    department = department_service.create_department(department_code=code, name="Create Ok")

    assert department.department_code == code
    assert calls == [department.id]
    reloaded = department_service._department_repo.get(department.id)
    assert reloaded is not None
    assert reloaded.department_code == code


def test_update_department_success_commits_and_emits_only_after_commit(services):
    department_service = services["department_service"]
    department = department_service.create_department(
        department_code=_unique_code("UPDATE-OK"), name="Before Update"
    )
    calls = _spy_signal(domain_events.departments_changed)

    updated = department_service.update_department(
        department.id, name="After Update", expected_version=department.version
    )

    assert updated.name == "After Update"
    assert calls == [updated.id]
    reloaded = department_service._department_repo.get(department.id)
    assert reloaded.name == "After Update"


def test_create_department_duplicate_code_validation_failure_rolls_back_and_emits_nothing(services, monkeypatch):
    department_service = services["department_service"]
    code = _unique_code("DUPE")
    department_service.create_department(department_code=code, name="First")

    captured_uow = {}
    original_create = type(department_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(department_service._uow_factory), "create", _spy_create)
    calls = _spy_signal(domain_events.departments_changed)

    with pytest.raises(ValidationError, match="Department code already exists"):
        department_service.create_department(department_code=code, name="Second")

    uow = captured_uow["uow"]
    assert uow._committed is False
    assert uow._closed is True
    assert calls == []


def test_update_department_duplicate_code_validation_failure_rolls_back_and_emits_nothing(services):
    department_service = services["department_service"]
    existing_code = _unique_code("DUPE-UPDATE-EXISTING")
    department_service.create_department(department_code=existing_code, name="Existing")
    department = department_service.create_department(
        department_code=_unique_code("DUPE-UPDATE-TARGET"), name="Target"
    )
    calls = _spy_signal(domain_events.departments_changed)

    with pytest.raises(ValidationError, match="Department code already exists"):
        department_service.update_department(
            department.id, department_code=existing_code, expected_version=department.version
        )

    reloaded = department_service._department_repo.get(department.id)
    assert reloaded.department_code != existing_code
    assert calls == []


def test_update_department_cannot_be_its_own_parent_rolls_back_and_emits_nothing(services):
    department_service = services["department_service"]
    department = department_service.create_department(
        department_code=_unique_code("SELF-PARENT"), name="Self Parent"
    )
    calls = _spy_signal(domain_events.departments_changed)

    with pytest.raises(ValidationError, match="cannot be its own parent"):
        department_service.update_department(
            department.id, parent_department_id=department.id, expected_version=department.version
        )

    assert calls == []


def test_create_department_cross_organization_parent_denied_and_emits_nothing(services):
    department_service = services["department_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    other_organization = organization_service.create_organization(
        organization_code=_unique_code("DEPT-CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    foreign_parent = department_service.create_department(
        department_code=_unique_code("FOREIGN-PARENT"), name="Foreign Parent"
    )
    tenant_context_service.set_active_organization(default_organization.id)

    calls = _spy_signal(domain_events.departments_changed)
    with pytest.raises(ValidationError, match="Parent department must belong to the active organization"):
        department_service.create_department(
            department_code=_unique_code("DEPT-CROSSORG-CHILD"),
            name="Child",
            parent_department_id=foreign_parent.id,
        )

    assert calls == []


def test_create_department_cross_organization_site_denied_and_emits_nothing(services):
    department_service = services["department_service"]
    site_service = services["site_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    other_organization = organization_service.create_organization(
        organization_code=_unique_code("DEPT-SITE-CROSSORG-OTHER"),
        display_name="Other Org For Site",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    foreign_site = site_service.create_site(site_code=_unique_code("FOREIGN-SITE"), name="Foreign Site")
    tenant_context_service.set_active_organization(default_organization.id)

    calls = _spy_signal(domain_events.departments_changed)
    with pytest.raises(ValidationError, match="Department site must belong to the active organization"):
        department_service.create_department(
            department_code=_unique_code("DEPT-SITE-CROSSORG-CHILD"),
            name="Child Of Foreign Site",
            site_id=foreign_site.id,
        )

    assert calls == []


def test_create_department_invalid_manager_employee_denied_and_emits_nothing(services):
    department_service = services["department_service"]
    calls = _spy_signal(domain_events.departments_changed)

    with pytest.raises(ValidationError, match="Department manager employee does not exist"):
        department_service.create_department(
            department_code=_unique_code("BADMANAGER"),
            name="Bad Manager Dept",
            manager_employee_id="does-not-exist",
        )

    assert calls == []


def test_create_department_same_org_manager_accepted(services):
    employee = services["employee_service"].create_employee(
        employee_code=_unique_code("MGR-SAMEORG"), full_name="Same Org Manager"
    )

    department_service = services["department_service"]
    department = department_service.create_department(
        department_code=_unique_code("SAMEORG-MGR-DEPT"),
        name="Same Org Manager Dept",
        manager_employee_id=employee.id,
    )

    assert department.manager_employee_id == employee.id


def test_create_department_cross_organization_manager_denied_and_emits_nothing(services):
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    other_organization = organization_service.create_organization(
        organization_code=_unique_code("DEPT-MGR-CROSSORG-OTHER"),
        display_name="Other Org For Manager",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    foreign_manager = services["employee_service"].create_employee(
        employee_code=_unique_code("FOREIGN-MGR"), full_name="Foreign Manager"
    )
    tenant_context_service.set_active_organization(default_organization.id)

    department_service = services["department_service"]
    calls = _spy_signal(domain_events.departments_changed)

    with pytest.raises(ValidationError, match="Department manager employee does not exist"):
        department_service.create_department(
            department_code=_unique_code("DEPT-MGR-CROSSORG-CHILD"),
            name="Dept With Foreign Manager",
            manager_employee_id=foreign_manager.id,
        )

    assert calls == []


def test_update_department_cross_organization_manager_denied_and_emits_nothing(services):
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    department_service = services["department_service"]
    department = department_service.create_department(
        department_code=_unique_code("DEPT-MGR-UPDATE-CROSSORG"), name="Dept For Manager Update"
    )

    other_organization = organization_service.create_organization(
        organization_code=_unique_code("DEPT-MGR-UPDATE-CROSSORG-OTHER"),
        display_name="Other Org For Manager Update",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    foreign_manager = services["employee_service"].create_employee(
        employee_code=_unique_code("FOREIGN-MGR-UPDATE"), full_name="Foreign Manager Update"
    )
    tenant_context_service.set_active_organization(default_organization.id)

    calls = _spy_signal(domain_events.departments_changed)
    with pytest.raises(ValidationError, match="Department manager employee does not exist"):
        department_service.update_department(
            department.id,
            manager_employee_id=foreign_manager.id,
            expected_version=department.version,
        )

    assert calls == []
    reloaded = department_service._department_repo.get(department.id)
    assert reloaded.manager_employee_id is None


def test_update_department_unchanged_manager_remains_valid(services):
    employee = services["employee_service"].create_employee(
        employee_code=_unique_code("MGR-UNCHANGED"), full_name="Unchanged Manager"
    )
    department_service = services["department_service"]
    department = department_service.create_department(
        department_code=_unique_code("MGR-UNCHANGED-DEPT"),
        name="Before",
        manager_employee_id=employee.id,
    )

    updated = department_service.update_department(
        department.id, name="After", expected_version=department.version
    )

    assert updated.manager_employee_id == employee.id
    assert updated.name == "After"


def test_update_department_manager_can_be_cleared(services):
    employee = services["employee_service"].create_employee(
        employee_code=_unique_code("MGR-CLEAR"), full_name="Clearable Manager"
    )
    department_service = services["department_service"]
    department = department_service.create_department(
        department_code=_unique_code("MGR-CLEAR-DEPT"),
        name="Clear Manager Dept",
        manager_employee_id=employee.id,
    )

    updated = department_service.update_department(
        department.id, manager_employee_id="", expected_version=department.version
    )

    assert updated.manager_employee_id is None


def test_update_department_stale_version_raises_and_does_not_mutate(services):
    department_service = services["department_service"]
    department = department_service.create_department(
        department_code=_unique_code("STALE"), name="Stale Department"
    )

    with pytest.raises(ConcurrencyError):
        department_service.update_department(
            department.id, name="Should Not Apply", expected_version=department.version + 1
        )

    reloaded = department_service._department_repo.get(department.id)
    assert reloaded.name == "Stale Department"


def test_create_department_authorization_failure_opens_no_uow(services, monkeypatch):
    department_service = services["department_service"]
    original_create = type(department_service._uow_factory).create
    create_calls = []

    def _spy_create(self, *, context):
        create_calls.append(1)
        return original_create(self, context=context)

    monkeypatch.setattr(type(department_service._uow_factory), "create", _spy_create)

    def _deny(*args, **kwargs):
        raise BusinessRuleError("Permission denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.department.department_commands.require_permission",
        _deny,
    )

    with pytest.raises(BusinessRuleError):
        department_service.create_department(department_code=_unique_code("AUTHFAIL"), name="No Access")

    assert create_calls == []


def test_update_department_authorization_failure_opens_no_uow(services, monkeypatch):
    department_service = services["department_service"]
    department = department_service.create_department(
        department_code=_unique_code("AUTHFAIL-UPDATE"), name="Before Deny"
    )

    original_create = type(department_service._uow_factory).create
    create_calls = []

    def _spy_create(self, *, context):
        create_calls.append(1)
        return original_create(self, context=context)

    monkeypatch.setattr(type(department_service._uow_factory), "create", _spy_create)

    def _deny(*args, **kwargs):
        raise BusinessRuleError("Permission denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.department.department_commands.require_permission",
        _deny,
    )

    with pytest.raises(BusinessRuleError):
        department_service.update_department(department.id, name="Should Not Apply")

    assert create_calls == []
    reloaded = department_service._department_repo.get(department.id)
    assert reloaded.name == "Before Deny"


def test_create_department_audit_failure_rolls_back_and_emits_nothing(services, monkeypatch):
    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated create_department audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    department_service = services["department_service"]
    calls = _spy_signal(domain_events.departments_changed)
    code = _unique_code("AUDITFAIL-CREATE")

    with pytest.raises(RuntimeError, match="simulated create_department audit failure"):
        department_service.create_department(department_code=code, name="Audit Fail")

    monkeypatch.undo()
    assert department_service._department_repo.get_by_code(
        department_service._tenant_context_service.get_active_organization().id, code
    ) is None
    assert calls == []


def test_update_department_audit_failure_rolls_back_and_emits_nothing(services, monkeypatch):
    department_service = services["department_service"]
    department = department_service.create_department(
        department_code=_unique_code("AUDITFAIL-UPDATE"), name="Before Audit Fail"
    )

    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated update_department audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    calls = _spy_signal(domain_events.departments_changed)

    with pytest.raises(RuntimeError, match="simulated update_department audit failure"):
        department_service.update_department(
            department.id, name="Should Not Apply", expected_version=department.version
        )

    monkeypatch.undo()
    reloaded = department_service._department_repo.get(department.id)
    assert reloaded.name == "Before Audit Fail"
    assert calls == []


def test_create_department_commit_failure_leaves_no_partial_state_and_emits_nothing(services, monkeypatch):
    department_service = services["department_service"]

    captured_uow = {}
    original_create = type(department_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(department_service._uow_factory), "create", _spy_create)

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyDepartmentUnitOfWork, "commit", _fail_commit)
    calls = _spy_signal(domain_events.departments_changed)

    code = _unique_code("COMMITFAIL")
    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        department_service.create_department(department_code=code, name="Commit Fail")

    uow = captured_uow["uow"]
    assert uow._committed is False, "commit() failing must never mark the UoW committed"
    assert uow._closed is True, "the UoW's own __exit__ must still roll back and close"
    assert calls == []


def test_update_department_commit_failure_leaves_no_partial_state_and_emits_nothing(services, monkeypatch):
    department_service = services["department_service"]
    department = department_service.create_department(
        department_code=_unique_code("COMMITFAIL-UPDATE"), name="Before Commit Fail"
    )

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyDepartmentUnitOfWork, "commit", _fail_commit)
    calls = _spy_signal(domain_events.departments_changed)

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        department_service.update_department(
            department.id, name="Should Not Apply", expected_version=department.version
        )

    reloaded = department_service._department_repo.get(department.id)
    assert reloaded.name == "Before Commit Fail"
    assert calls == []


def test_no_global_mutation_session_touch_during_migrated_create(services):
    department_service = services["department_service"]
    legacy_session = department_service._session
    legacy_session.commit()

    department_service.create_department(department_code=_unique_code("ISOLATED"), name="Isolated Department")

    assert len(legacy_session.new) == 0
    assert len(legacy_session.dirty) == 0


def test_update_department_uses_a_fresh_uow_distinct_from_the_legacy_session(services, monkeypatch):
    department_service = services["department_service"]
    department = department_service.create_department(
        department_code=_unique_code("FRESH-UPDATE"), name="Before Update"
    )

    seen = {}
    original_create = type(department_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        return uow

    monkeypatch.setattr(type(department_service._uow_factory), "create", _spy_create)

    updated = department_service.update_department(
        department.id, name="After Update", expected_version=department.version
    )

    assert updated.name == "After Update"
    assert seen["uow_session"] is not department_service._session


def test_admin_console_still_reacts_to_departments_changed_unchanged(services):
    from src.ui_qml.platform.controllers.admin_console.domain_event_binder import bind_domain_events

    refresh_calls = []

    class _FakeController:
        def __init__(self):
            self._domain_event_subscriptions = []

        def _subscribe_domain_signal(self, signal, callback):
            signal.connect(callback)
            self._domain_event_subscriptions.append((signal, callback))

        def _request_domain_refresh(self):
            refresh_calls.append("refresh")

    bind_domain_events(_FakeController())

    services["department_service"].create_department(
        department_code=_unique_code("ADMIN-REFRESH"), name="Admin Refresh Department"
    )

    assert refresh_calls == ["refresh"]
