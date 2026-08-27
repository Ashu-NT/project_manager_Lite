from __future__ import annotations

import pytest

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.infrastructure.persistence.uow.party_unit_of_work import (
    SqlAlchemyPartyUnitOfWork,
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


def test_two_independent_create_party_calls_use_genuinely_different_sessions(services, monkeypatch):
    party_service = services["party_service"]
    created_sessions = []
    original_create = type(party_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        created_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(party_service._uow_factory), "create", _spy_create)

    party_service.create_party(party_code=_unique_code("FRESH-A"), party_name="Fresh A")
    party_service.create_party(party_code=_unique_code("FRESH-B"), party_name="Fresh B")

    assert len(created_sessions) == 2
    assert created_sessions[0] is not created_sessions[1]
    assert all(s is not party_service._session for s in created_sessions)


def test_create_party_repository_and_audit_share_the_uow_session(services, monkeypatch):
    party_service = services["party_service"]
    seen = {}
    original_create = type(party_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["parties_repo_session"] = uow.parties.session
        seen["audit_session"] = uow._enterprise_audit_service._session
        return uow

    monkeypatch.setattr(type(party_service._uow_factory), "create", _spy_create)

    party_service.create_party(party_code=_unique_code("SHARE"), party_name="Shared Session Party")

    assert seen["uow_session"] is seen["parties_repo_session"]
    assert seen["uow_session"] is seen["audit_session"]


def test_create_party_success_commits_and_emits_only_after_commit(services):
    party_service = services["party_service"]
    calls = _spy_signal(domain_events.parties_changed)

    code = _unique_code("CREATE-OK")
    party = party_service.create_party(party_code=code, party_name="Create Ok")

    assert party.party_code == code
    assert calls == [party.id]
    reloaded = party_service._party_repo.get(party.id)
    assert reloaded is not None
    assert reloaded.party_code == code


def test_update_party_success_commits_and_emits_only_after_commit(services):
    party_service = services["party_service"]
    party = party_service.create_party(party_code=_unique_code("UPDATE-OK"), party_name="Before Update")
    calls = _spy_signal(domain_events.parties_changed)

    updated = party_service.update_party(party.id, party_name="After Update", expected_version=party.version)

    assert updated.party_name == "After Update"
    assert calls == [updated.id]
    reloaded = party_service._party_repo.get(party.id)
    assert reloaded.party_name == "After Update"


def test_create_party_duplicate_code_validation_failure_rolls_back_and_emits_nothing(services, monkeypatch):
    party_service = services["party_service"]
    code = _unique_code("DUPE")
    party_service.create_party(party_code=code, party_name="First")

    captured_uow = {}
    original_create = type(party_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(party_service._uow_factory), "create", _spy_create)
    calls = _spy_signal(domain_events.parties_changed)

    with pytest.raises(ValidationError, match="Party code already exists"):
        party_service.create_party(party_code=code, party_name="Second")

    uow = captured_uow["uow"]
    assert uow._committed is False
    assert uow._closed is True
    assert calls == []


def test_update_party_duplicate_code_validation_failure_rolls_back_and_emits_nothing(services):
    party_service = services["party_service"]
    existing_code = _unique_code("DUPE-UPDATE-EXISTING")
    party_service.create_party(party_code=existing_code, party_name="Existing")
    party = party_service.create_party(party_code=_unique_code("DUPE-UPDATE-TARGET"), party_name="Target")
    calls = _spy_signal(domain_events.parties_changed)

    with pytest.raises(ValidationError, match="Party code already exists"):
        party_service.update_party(party.id, party_code=existing_code, expected_version=party.version)

    reloaded = party_service._party_repo.get(party.id)
    assert reloaded.party_code != existing_code
    assert calls == []


def test_update_party_cross_organization_denied_as_not_found_and_emits_nothing(services):
    party_service = services["party_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    party = party_service.create_party(party_code=_unique_code("CROSSORG"), party_name="Home Org Party")

    other_organization = organization_service.create_organization(
        organization_code=_unique_code("CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    calls = _spy_signal(domain_events.parties_changed)
    try:
        with pytest.raises(NotFoundError):
            party_service.update_party(party.id, party_name="Hijacked")
    finally:
        tenant_context_service.set_active_organization(default_organization.id)

    assert calls == []
    reloaded = party_service._party_repo.get(party.id)
    assert reloaded.party_name == "Home Org Party"


def test_update_party_stale_version_raises_and_does_not_mutate(services):
    party_service = services["party_service"]
    party = party_service.create_party(party_code=_unique_code("STALE"), party_name="Stale Party")

    with pytest.raises(ConcurrencyError):
        party_service.update_party(party.id, party_name="Should Not Apply", expected_version=party.version + 1)

    reloaded = party_service._party_repo.get(party.id)
    assert reloaded.party_name == "Stale Party"


def test_create_party_authorization_failure_opens_no_uow(services, monkeypatch):
    party_service = services["party_service"]
    original_create = type(party_service._uow_factory).create
    create_calls = []

    def _spy_create(self, *, context):
        create_calls.append(1)
        return original_create(self, context=context)

    monkeypatch.setattr(type(party_service._uow_factory), "create", _spy_create)

    def _deny(*args, **kwargs):
        raise BusinessRuleError("Permission denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.party.party_service.require_permission",
        _deny,
    )

    with pytest.raises(BusinessRuleError):
        party_service.create_party(party_code=_unique_code("AUTHFAIL"), party_name="No Access")

    assert create_calls == []


def test_update_party_authorization_failure_opens_no_uow(services, monkeypatch):
    party_service = services["party_service"]
    party = party_service.create_party(party_code=_unique_code("AUTHFAIL-UPDATE"), party_name="Before Deny")

    original_create = type(party_service._uow_factory).create
    create_calls = []

    def _spy_create(self, *, context):
        create_calls.append(1)
        return original_create(self, context=context)

    monkeypatch.setattr(type(party_service._uow_factory), "create", _spy_create)

    def _deny(*args, **kwargs):
        raise BusinessRuleError("Permission denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.party.party_service.require_permission",
        _deny,
    )

    with pytest.raises(BusinessRuleError):
        party_service.update_party(party.id, party_name="Should Not Apply")

    assert create_calls == []
    reloaded = party_service._party_repo.get(party.id)
    assert reloaded.party_name == "Before Deny"


def test_create_party_audit_failure_rolls_back_and_emits_nothing(services, monkeypatch):
    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated create_party audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    party_service = services["party_service"]
    calls = _spy_signal(domain_events.parties_changed)
    code = _unique_code("AUDITFAIL-CREATE")

    with pytest.raises(RuntimeError, match="simulated create_party audit failure"):
        party_service.create_party(party_code=code, party_name="Audit Fail")

    monkeypatch.undo()
    organization = party_service._tenant_context_service.get_active_organization()
    assert party_service._party_repo.get_by_code(organization.id, code) is None
    assert calls == []


def test_update_party_audit_failure_rolls_back_and_emits_nothing(services, monkeypatch):
    party_service = services["party_service"]
    party = party_service.create_party(party_code=_unique_code("AUDITFAIL-UPDATE"), party_name="Before Audit Fail")

    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated update_party audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    calls = _spy_signal(domain_events.parties_changed)

    with pytest.raises(RuntimeError, match="simulated update_party audit failure"):
        party_service.update_party(party.id, party_name="Should Not Apply", expected_version=party.version)

    monkeypatch.undo()
    reloaded = party_service._party_repo.get(party.id)
    assert reloaded.party_name == "Before Audit Fail"
    assert calls == []


def test_create_party_commit_failure_leaves_no_partial_state_and_emits_nothing(services, monkeypatch):
    party_service = services["party_service"]

    captured_uow = {}
    original_create = type(party_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(party_service._uow_factory), "create", _spy_create)

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyPartyUnitOfWork, "commit", _fail_commit)
    calls = _spy_signal(domain_events.parties_changed)

    code = _unique_code("COMMITFAIL")
    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        party_service.create_party(party_code=code, party_name="Commit Fail")

    uow = captured_uow["uow"]
    assert uow._committed is False, "commit() failing must never mark the UoW committed"
    assert uow._closed is True, "the UoW's own __exit__ must still roll back and close"
    assert calls == []


def test_update_party_commit_failure_leaves_no_partial_state_and_emits_nothing(services, monkeypatch):
    party_service = services["party_service"]
    party = party_service.create_party(party_code=_unique_code("COMMITFAIL-UPDATE"), party_name="Before Commit Fail")

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyPartyUnitOfWork, "commit", _fail_commit)
    calls = _spy_signal(domain_events.parties_changed)

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        party_service.update_party(party.id, party_name="Should Not Apply", expected_version=party.version)

    reloaded = party_service._party_repo.get(party.id)
    assert reloaded.party_name == "Before Commit Fail"
    assert calls == []


def test_no_global_mutation_session_touch_during_migrated_create(services):
    party_service = services["party_service"]
    legacy_session = party_service._session
    legacy_session.commit()

    party_service.create_party(party_code=_unique_code("ISOLATED"), party_name="Isolated Party")

    assert len(legacy_session.new) == 0
    assert len(legacy_session.dirty) == 0


def test_update_party_uses_a_fresh_uow_distinct_from_the_legacy_session(services, monkeypatch):
    party_service = services["party_service"]
    party = party_service.create_party(party_code=_unique_code("FRESH-UPDATE"), party_name="Before Update")

    seen = {}
    original_create = type(party_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        return uow

    monkeypatch.setattr(type(party_service._uow_factory), "create", _spy_create)

    updated = party_service.update_party(party.id, party_name="After Update", expected_version=party.version)

    assert updated.party_name == "After Update"
    assert seen["uow_session"] is not party_service._session


def test_admin_console_still_reacts_to_parties_changed_unchanged(services):
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

    services["party_service"].create_party(party_code=_unique_code("ADMIN-REFRESH"), party_name="Admin Refresh Party")

    assert refresh_calls == ["refresh"]


def test_inventory_procurement_representative_consumer_still_reacts_to_parties_changed_unchanged(services):
    from src.ui_qml.modules.inventory_procurement.controllers.inventory.inventory_domain_event_binder import (
        bind_domain_events as bind_inventory_domain_events,
    )

    refresh_calls = []

    class _FakeController:
        def __init__(self):
            self._domain_event_subscriptions = []

        def _subscribe_domain_signal(self, signal, callback):
            signal.connect(callback)
            self._domain_event_subscriptions.append((signal, callback))

        def _request_domain_refresh(self):
            refresh_calls.append("refresh")

    bind_inventory_domain_events(_FakeController())

    services["party_service"].create_party(party_code=_unique_code("INV-REFRESH"), party_name="Inventory Refresh Party")

    assert refresh_calls == ["refresh"]


def test_no_new_party_domain_event_introduced():
    import glob
    import re

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if re.search(r"\bPartyCreated\b", source) or re.search(r"\bPartyProfileUpdated\b", source) or re.search(r"\bPartyChanged\b", source):
            hits.append(normalized)
    assert hits == [], hits


def test_parties_changed_field_still_present():
    assert hasattr(domain_events, "parties_changed")


def test_canonical_party_uow_retained_no_raw_session_commit():
    import inspect

    import src.core.platform.application.master_data.party.party_service as party_service_module

    source = inspect.getsource(party_service_module.PartyService.create_party) + inspect.getsource(
        party_service_module.PartyService.update_party
    )
    assert "self._session.commit(" not in source
    assert "self._session.rollback(" not in source
    assert "uow.commit()" in source


def test_no_platform_to_business_module_concrete_infrastructure_import():
    import inspect

    import src.core.platform.infrastructure.persistence.uow.party_unit_of_work as infra_module

    source = inspect.getsource(infra_module)
    assert "core.modules" not in source
