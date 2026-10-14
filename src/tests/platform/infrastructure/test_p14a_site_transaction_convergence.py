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
from src.core.platform.contract.use_cases.master_data.site.commands import (
    SiteCreateCommand,
    SiteUpdateCommand,
)
from src.core.platform.domain.master_data.site.events import (
    SiteCreated,
    SiteProfileUpdated,
)
from src.core.platform.infrastructure.persistence.uow.master_data.site_unit_of_work import (
    SqlAlchemySiteUnitOfWork,
)

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _spy(services, event_type):
    calls = []
    services["site_commands"]._uow_factory._post_commit_bus.subscribe(
        event_type, lambda event, context: calls.append(event)
    )
    return calls


def test_two_independent_create_site_calls_use_genuinely_different_sessions(services, monkeypatch):
    created_sessions = []
    original_create = type(services["site_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        created_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(services["site_commands"]._uow_factory), "create", _spy_create)

    services["site_commands"].create_site(SiteCreateCommand(site_code=_unique_code("FRESH-A"), name="Fresh A"))
    services["site_commands"].create_site(SiteCreateCommand(site_code=_unique_code("FRESH-B"), name="Fresh B"))

    assert len(created_sessions) == 2
    assert created_sessions[0] is not created_sessions[1]
    assert all(s is not services["session"] for s in created_sessions)


def test_create_site_repository_and_audit_share_the_uow_session(services, monkeypatch):
    seen = {}
    original_create = type(services["site_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["sites_repo_session"] = uow.sites.session
        seen["audit_session"] = uow._enterprise_audit_service._session
        return uow

    monkeypatch.setattr(type(services["site_commands"]._uow_factory), "create", _spy_create)

    services["site_commands"].create_site(SiteCreateCommand(site_code=_unique_code("SHARE"), name="Shared Session Site"))

    assert seen["uow_session"] is seen["sites_repo_session"]
    assert seen["uow_session"] is seen["audit_session"]


def test_create_site_success_commits_and_emits_only_after_commit(services):
    calls = _spy(services, SiteCreated)

    code = _unique_code("CREATE-OK")
    site = services["site_commands"].create_site(SiteCreateCommand(site_code=code, name="Create Ok"))

    assert site.site_code == code
    assert [e.site_id for e in calls] == [site.id]
    reloaded = services["site_query"]._site_repo.get(site.id)
    assert reloaded is not None
    assert reloaded.site_code == code


def test_update_site_success_commits_and_emits_only_after_commit(services):
    site = services["site_commands"].create_site(SiteCreateCommand(site_code=_unique_code("UPDATE-OK"), name="Before Update"))
    calls = _spy(services, SiteProfileUpdated)

    updated = services["site_commands"].update_site(SiteUpdateCommand(site_id=site.id, name="After Update", expected_version=site.version))

    assert updated.name == "After Update"
    assert [e.site_id for e in calls] == [updated.id]
    reloaded = services["site_query"]._site_repo.get(site.id)
    assert reloaded.name == "After Update"


def test_create_site_duplicate_code_validation_failure_rolls_back_and_emits_nothing(services, monkeypatch):
    code = _unique_code("DUPE")
    services["site_commands"].create_site(SiteCreateCommand(site_code=code, name="First"))

    captured_uow = {}
    original_create = type(services["site_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(services["site_commands"]._uow_factory), "create", _spy_create)
    calls = _spy(services, SiteCreated)

    with pytest.raises(ValidationError, match="Site code already exists"):
        services["site_commands"].create_site(SiteCreateCommand(site_code=code, name="Second"))

    uow = captured_uow["uow"]
    assert uow._committed is False
    assert uow._closed is True
    assert calls == []


def test_update_site_duplicate_code_validation_failure_rolls_back_and_emits_nothing(services):
    existing_code = _unique_code("DUPE-UPDATE-EXISTING")
    services["site_commands"].create_site(SiteCreateCommand(site_code=existing_code, name="Existing"))
    site = services["site_commands"].create_site(SiteCreateCommand(site_code=_unique_code("DUPE-UPDATE-TARGET"), name="Target"))
    calls = _spy(services, SiteProfileUpdated)

    with pytest.raises(ValidationError, match="Site code already exists"):
        services["site_commands"].update_site(SiteUpdateCommand(site_id=site.id, site_code=existing_code, expected_version=site.version))

    reloaded = services["site_query"]._site_repo.get(site.id)
    assert reloaded.site_code != existing_code
    assert calls == []


def test_update_site_cross_organization_denied_as_not_found_and_emits_nothing(services):
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    site = services["site_commands"].create_site(SiteCreateCommand(site_code=_unique_code("CROSSORG"), name="Home Org Site"))

    other_organization = services["organization_commands"].create_organization(
        organization_code=_unique_code("CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    calls = _spy(services, SiteProfileUpdated)
    try:
        with pytest.raises(NotFoundError):
            services["site_commands"].update_site(SiteUpdateCommand(site_id=site.id, name="Hijacked"))
    finally:
        tenant_context_service.set_active_organization(default_organization.id)

    assert calls == []
    reloaded = services["site_query"]._site_repo.get(site.id)
    assert reloaded.name == "Home Org Site"


def test_update_site_stale_version_raises_and_does_not_mutate(services):
    site = services["site_commands"].create_site(SiteCreateCommand(site_code=_unique_code("STALE"), name="Stale Site"))

    with pytest.raises(ConcurrencyError):
        services["site_commands"].update_site(SiteUpdateCommand(site_id=site.id, name="Should Not Apply", expected_version=site.version + 1))

    reloaded = services["site_query"]._site_repo.get(site.id)
    assert reloaded.name == "Stale Site"


def test_create_site_authorization_failure_opens_no_uow(services, monkeypatch):
    original_create = type(services["site_commands"]._uow_factory).create
    create_calls = []

    def _spy_create(self, *, context):
        create_calls.append(1)
        return original_create(self, context=context)

    monkeypatch.setattr(type(services["site_commands"]._uow_factory), "create", _spy_create)

    def _deny(*args, **kwargs):
        raise BusinessRuleError("Permission denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.site.commands.site_commands.require_permission",
        _deny,
    )

    with pytest.raises(BusinessRuleError):
        services["site_commands"].create_site(SiteCreateCommand(site_code=_unique_code("AUTHFAIL"), name="No Access"))

    assert create_calls == []


def test_update_site_authorization_failure_opens_no_uow(services, monkeypatch):
    site = services["site_commands"].create_site(SiteCreateCommand(site_code=_unique_code("AUTHFAIL-UPDATE"), name="Before Deny"))

    original_create = type(services["site_commands"]._uow_factory).create
    create_calls = []

    def _spy_create(self, *, context):
        create_calls.append(1)
        return original_create(self, context=context)

    monkeypatch.setattr(type(services["site_commands"]._uow_factory), "create", _spy_create)

    def _deny(*args, **kwargs):
        raise BusinessRuleError("Permission denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.site.commands.site_commands.require_permission",
        _deny,
    )

    with pytest.raises(BusinessRuleError):
        services["site_commands"].update_site(SiteUpdateCommand(site_id=site.id, name="Should Not Apply"))

    assert create_calls == []
    reloaded = services["site_query"]._site_repo.get(site.id)
    assert reloaded.name == "Before Deny"


def test_create_site_audit_failure_rolls_back_and_emits_nothing(services, monkeypatch):
    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated create_site audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    calls = _spy(services, SiteCreated)
    code = _unique_code("AUDITFAIL-CREATE")

    with pytest.raises(RuntimeError, match="simulated create_site audit failure"):
        services["site_commands"].create_site(SiteCreateCommand(site_code=code, name="Audit Fail"))

    monkeypatch.undo()
    organization = services["tenant_context_service"].get_active_organization()
    assert services["site_query"]._site_repo.get_by_code(organization.id, code) is None
    assert calls == []


def test_update_site_audit_failure_rolls_back_and_emits_nothing(services, monkeypatch):
    site = services["site_commands"].create_site(SiteCreateCommand(site_code=_unique_code("AUDITFAIL-UPDATE"), name="Before Audit Fail"))

    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated update_site audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    calls = _spy(services, SiteProfileUpdated)

    with pytest.raises(RuntimeError, match="simulated update_site audit failure"):
        services["site_commands"].update_site(SiteUpdateCommand(site_id=site.id, name="Should Not Apply", expected_version=site.version))

    monkeypatch.undo()
    reloaded = services["site_query"]._site_repo.get(site.id)
    assert reloaded.name == "Before Audit Fail"
    assert calls == []


def test_create_site_commit_failure_leaves_no_partial_state_and_emits_nothing(services, monkeypatch):

    captured_uow = {}
    original_create = type(services["site_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        captured_uow["uow"] = uow
        return uow

    monkeypatch.setattr(type(services["site_commands"]._uow_factory), "create", _spy_create)

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemySiteUnitOfWork, "commit", _fail_commit)
    calls = _spy(services, SiteCreated)

    code = _unique_code("COMMITFAIL")
    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        services["site_commands"].create_site(SiteCreateCommand(site_code=code, name="Commit Fail"))

    uow = captured_uow["uow"]
    assert uow._committed is False, "commit() failing must never mark the UoW committed"
    assert uow._closed is True, "the UoW's own __exit__ must still roll back and close"
    assert calls == []


def test_update_site_commit_failure_leaves_no_partial_state_and_emits_nothing(services, monkeypatch):
    site = services["site_commands"].create_site(SiteCreateCommand(site_code=_unique_code("COMMITFAIL-UPDATE"), name="Before Commit Fail"))

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemySiteUnitOfWork, "commit", _fail_commit)
    calls = _spy(services, SiteProfileUpdated)

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        services["site_commands"].update_site(SiteUpdateCommand(site_id=site.id, name="Should Not Apply", expected_version=site.version))

    reloaded = services["site_query"]._site_repo.get(site.id)
    assert reloaded.name == "Before Commit Fail"
    assert calls == []


def test_no_global_mutation_session_touch_during_migrated_create(services):
    legacy_session = services["session"]
    legacy_session.commit()

    services["site_commands"].create_site(SiteCreateCommand(site_code=_unique_code("ISOLATED"), name="Isolated Site"))

    assert len(legacy_session.new) == 0
    assert len(legacy_session.dirty) == 0


def test_update_site_uses_a_fresh_uow_distinct_from_the_legacy_session(services, monkeypatch):
    site = services["site_commands"].create_site(SiteCreateCommand(site_code=_unique_code("FRESH-UPDATE"), name="Before Update"))

    seen = {}
    original_create = type(services["site_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        return uow

    monkeypatch.setattr(type(services["site_commands"]._uow_factory), "create", _spy_create)

    updated = services["site_commands"].update_site(SiteUpdateCommand(site_id=site.id, name="After Update", expected_version=site.version))

    assert updated.name == "After Update"
    assert seen["uow_session"] is not services["session"]


