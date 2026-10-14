from __future__ import annotations

import pytest

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.contract.use_cases.master_data.party.commands import (
    PartyCreateCommand,
    PartyUpdateCommand,
)
from src.core.platform.domain.master_data.party.events import (
    PartyCreated,
    PartyProfileUpdated,
)
from src.core.platform.infrastructure.persistence.uow.master_data.party_unit_of_work import (
    SqlAlchemyPartyUnitOfWork,
)

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _spy_event(services, event_type):
    calls = []
    services["party_commands"]._uow_factory._post_commit_bus.subscribe(
        event_type, lambda event, context: calls.append(event)
    )
    return calls


def test_two_independent_create_party_calls_use_genuinely_different_sessions(services, monkeypatch):
    created_sessions = []
    original_create = type(services["party_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        created_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(services["party_commands"]._uow_factory), "create", _spy_create)

    services["party_commands"].create_party(PartyCreateCommand(party_code=_unique_code("FRESH-A"), party_name="Fresh A"))
    services["party_commands"].create_party(PartyCreateCommand(party_code=_unique_code("FRESH-B"), party_name="Fresh B"))

    assert len(created_sessions) == 2
    assert created_sessions[0] is not created_sessions[1]
    assert all(s is not services["session"] for s in created_sessions)


def test_create_party_repository_and_audit_share_the_uow_session(services, monkeypatch):
    seen = {}
    original_create = type(services["party_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["parties_repo_session"] = uow.parties.session
        seen["audit_session"] = uow._enterprise_audit_service._session
        return uow

    monkeypatch.setattr(type(services["party_commands"]._uow_factory), "create", _spy_create)

    services["party_commands"].create_party(PartyCreateCommand(party_code=_unique_code("SHARE"), party_name="Shared Session Party"))

    assert seen["uow_session"] is seen["parties_repo_session"]
    assert seen["uow_session"] is seen["audit_session"]


def test_create_party_success_commits_and_emits_only_after_commit(services):
    calls = _spy_event(services, PartyCreated)

    code = _unique_code("CREATE-OK")
    party = services["party_commands"].create_party(PartyCreateCommand(party_code=code, party_name="Create Ok"))

    assert party.party_code == code
    assert [e.party_id for e in calls] == [party.id]
    reloaded = services["party_query"]._party_repo.get(party.id)
    assert reloaded is not None
    assert reloaded.party_code == code


def test_update_party_success_commits_and_emits_only_after_commit(services):
    party = services["party_commands"].create_party(PartyCreateCommand(party_code=_unique_code("UPDATE-OK"), party_name="Before Update"))
    calls = _spy_event(services, PartyProfileUpdated)

    updated = services["party_commands"].update_party(PartyUpdateCommand(party_id=party.id, party_name="After Update", expected_version=party.version))

    assert updated.party_name == "After Update"
    assert [e.party_id for e in calls] == [updated.id]
    reloaded = services["party_query"]._party_repo.get(party.id)
    assert reloaded.party_name == "After Update"


def test_create_party_duplicate_code_validation_failure_rolls_back_and_emits_nothing(services, monkeypatch):
    code = _unique_code("DUPE")
    services["party_commands"].create_party(PartyCreateCommand(party_code=code, party_name="First"))

    captured_uow = {}
    original_create = type(services["party_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(services["party_commands"]._uow_factory), "create", _spy_create)
    calls = _spy_event(services, PartyCreated)

    with pytest.raises(ValidationError, match="Party code already exists"):
        services["party_commands"].create_party(PartyCreateCommand(party_code=code, party_name="Second"))

    uow = captured_uow["uow"]
    assert uow._committed is False
    assert uow._closed is True
    assert calls == []


def test_update_party_duplicate_code_validation_failure_rolls_back_and_emits_nothing(services):
    existing_code = _unique_code("DUPE-UPDATE-EXISTING")
    services["party_commands"].create_party(PartyCreateCommand(party_code=existing_code, party_name="Existing"))
    party = services["party_commands"].create_party(PartyCreateCommand(party_code=_unique_code("DUPE-UPDATE-TARGET"), party_name="Target"))
    calls = _spy_event(services, PartyProfileUpdated)

    with pytest.raises(ValidationError, match="Party code already exists"):
        services["party_commands"].update_party(PartyUpdateCommand(party_id=party.id, party_code=existing_code, expected_version=party.version))

    reloaded = services["party_query"]._party_repo.get(party.id)
    assert reloaded.party_code != existing_code
    assert calls == []


def test_update_party_cross_organization_denied_as_not_found_and_emits_nothing(services):
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    party = services["party_commands"].create_party(PartyCreateCommand(party_code=_unique_code("CROSSORG"), party_name="Home Org Party"))

    other_organization = services["organization_commands"].create_organization(
        organization_code=_unique_code("CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    calls = _spy_event(services, PartyProfileUpdated)
    try:
        with pytest.raises(NotFoundError):
            services["party_commands"].update_party(PartyUpdateCommand(party_id=party.id, party_name="Hijacked"))
    finally:
        tenant_context_service.set_active_organization(default_organization.id)

    assert calls == []
    reloaded = services["party_query"]._party_repo.get(party.id)
    assert reloaded.party_name == "Home Org Party"


def test_update_party_stale_version_raises_and_does_not_mutate(services):
    party = services["party_commands"].create_party(PartyCreateCommand(party_code=_unique_code("STALE"), party_name="Stale Party"))

    with pytest.raises(ConcurrencyError):
        services["party_commands"].update_party(PartyUpdateCommand(party_id=party.id, party_name="Should Not Apply", expected_version=party.version + 1))

    reloaded = services["party_query"]._party_repo.get(party.id)
    assert reloaded.party_name == "Stale Party"


def test_create_party_authorization_failure_opens_no_uow(services, monkeypatch):
    original_create = type(services["party_commands"]._uow_factory).create
    create_calls = []

    def _spy_create(self, *, context):
        create_calls.append(1)
        return original_create(self, context=context)

    monkeypatch.setattr(type(services["party_commands"]._uow_factory), "create", _spy_create)

    def _deny(*args, **kwargs):
        raise BusinessRuleError("Permission denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.party.commands.party_commands.require_permission",
        _deny,
    )

    with pytest.raises(BusinessRuleError):
        services["party_commands"].create_party(PartyCreateCommand(party_code=_unique_code("AUTHFAIL"), party_name="No Access"))

    assert create_calls == []


def test_update_party_authorization_failure_opens_no_uow(services, monkeypatch):
    party = services["party_commands"].create_party(PartyCreateCommand(party_code=_unique_code("AUTHFAIL-UPDATE"), party_name="Before Deny"))

    original_create = type(services["party_commands"]._uow_factory).create
    create_calls = []

    def _spy_create(self, *, context):
        create_calls.append(1)
        return original_create(self, context=context)

    monkeypatch.setattr(type(services["party_commands"]._uow_factory), "create", _spy_create)

    def _deny(*args, **kwargs):
        raise BusinessRuleError("Permission denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.party.commands.party_commands.require_permission",
        _deny,
    )

    with pytest.raises(BusinessRuleError):
        services["party_commands"].update_party(PartyUpdateCommand(party_id=party.id, party_name="Should Not Apply"))

    assert create_calls == []
    reloaded = services["party_query"]._party_repo.get(party.id)
    assert reloaded.party_name == "Before Deny"


def test_create_party_audit_failure_rolls_back_and_emits_nothing(services, monkeypatch):
    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated create_party audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    calls = _spy_event(services, PartyCreated)
    code = _unique_code("AUDITFAIL-CREATE")

    with pytest.raises(RuntimeError, match="simulated create_party audit failure"):
        services["party_commands"].create_party(PartyCreateCommand(party_code=code, party_name="Audit Fail"))

    monkeypatch.undo()
    organization = services["tenant_context_service"].get_active_organization()
    assert services["party_query"]._party_repo.get_by_code(organization.id, code) is None
    assert calls == []


def test_update_party_audit_failure_rolls_back_and_emits_nothing(services, monkeypatch):
    party = services["party_commands"].create_party(PartyCreateCommand(party_code=_unique_code("AUDITFAIL-UPDATE"), party_name="Before Audit Fail"))

    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated update_party audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    calls = _spy_event(services, PartyProfileUpdated)

    with pytest.raises(RuntimeError, match="simulated update_party audit failure"):
        services["party_commands"].update_party(PartyUpdateCommand(party_id=party.id, party_name="Should Not Apply", expected_version=party.version))

    monkeypatch.undo()
    reloaded = services["party_query"]._party_repo.get(party.id)
    assert reloaded.party_name == "Before Audit Fail"
    assert calls == []


def test_create_party_commit_failure_leaves_no_partial_state_and_emits_nothing(services, monkeypatch):

    captured_uow = {}
    original_create = type(services["party_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(services["party_commands"]._uow_factory), "create", _spy_create)

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyPartyUnitOfWork, "commit", _fail_commit)
    calls = _spy_event(services, PartyCreated)

    code = _unique_code("COMMITFAIL")
    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        services["party_commands"].create_party(PartyCreateCommand(party_code=code, party_name="Commit Fail"))

    uow = captured_uow["uow"]
    assert uow._committed is False, "commit() failing must never mark the UoW committed"
    assert uow._closed is True, "the UoW's own __exit__ must still roll back and close"
    assert calls == []


def test_update_party_commit_failure_leaves_no_partial_state_and_emits_nothing(services, monkeypatch):
    party = services["party_commands"].create_party(PartyCreateCommand(party_code=_unique_code("COMMITFAIL-UPDATE"), party_name="Before Commit Fail"))

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyPartyUnitOfWork, "commit", _fail_commit)
    calls = _spy_event(services, PartyProfileUpdated)

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        services["party_commands"].update_party(PartyUpdateCommand(party_id=party.id, party_name="Should Not Apply", expected_version=party.version))

    reloaded = services["party_query"]._party_repo.get(party.id)
    assert reloaded.party_name == "Before Commit Fail"
    assert calls == []


def test_no_global_mutation_session_touch_during_migrated_create(services):
    legacy_session = services["session"]
    legacy_session.commit()

    services["party_commands"].create_party(PartyCreateCommand(party_code=_unique_code("ISOLATED"), party_name="Isolated Party"))

    assert len(legacy_session.new) == 0
    assert len(legacy_session.dirty) == 0


def test_update_party_uses_a_fresh_uow_distinct_from_the_legacy_session(services, monkeypatch):
    party = services["party_commands"].create_party(PartyCreateCommand(party_code=_unique_code("FRESH-UPDATE"), party_name="Before Update"))

    seen = {}
    original_create = type(services["party_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        return uow

    monkeypatch.setattr(type(services["party_commands"]._uow_factory), "create", _spy_create)

    updated = services["party_commands"].update_party(PartyUpdateCommand(party_id=party.id, party_name="After Update", expected_version=party.version))

    assert updated.party_name == "After Update"
    assert seen["uow_session"] is not services["session"]


def test_canonical_party_uow_retained_no_raw_session_commit():
    import inspect

    import src.core.platform.application.master_data.party.commands.party_commands as party_service_module

    source = inspect.getsource(party_service_module.PartyCommandHandler.create_party) + inspect.getsource(
        party_service_module.PartyCommandHandler.update_party
    )
    assert "self._session.commit(" not in source
    assert "self._session.rollback(" not in source
    assert "uow.commit()" in source


def test_no_platform_to_business_module_concrete_infrastructure_import():
    import inspect

    import src.core.platform.infrastructure.persistence.uow.master_data.party_unit_of_work as infra_module

    source = inspect.getsource(infra_module)
    assert "core.modules" not in source
