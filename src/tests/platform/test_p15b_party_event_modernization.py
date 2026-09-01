from __future__ import annotations

import inspect
import re

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.domain.master_data.party.events import PartyCreated, PartyProfileUpdated
from src.core.shared.events.domain_events import domain_events
from src.ui_qml.platform.context import PlatformWorkspaceCatalog

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _spy(services, event_type):
    calls = []
    services["party_service"]._uow_factory._post_commit_bus.subscribe(
        event_type, lambda event, context: calls.append(event)
    )
    return calls


def _platform_catalog(services) -> PlatformWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return PlatformWorkspaceCatalog(desktop_api_registry=registry)


def _spy_party_list_hints(services):
    from src.core.platform.application.master_data.party.event_handlers.view_invalidation import (
        PARTY_CATEGORY,
        PARTY_LIST_SCOPE_CODE,
    )
    from src.core.shared.events.view_invalidation import ExactOrganization

    organization = services["tenant_context_service"].get_active_organization()
    tenant_id = organization.tenant_id
    organization_id = organization.id

    hints = []

    def _on_hint(hint):
        if hint.category == PARTY_CATEGORY and hint.scope_code == PARTY_LIST_SCOPE_CODE:
            hints.append(hint)

    services["platform_view_invalidation_channel"].subscribe(
        ExactOrganization(tenant_id, organization_id), _on_hint
    )
    return hints


def test_create_produces_exactly_one_party_created(services):
    calls = _spy(services, PartyCreated)
    party = services["party_service"].create_party(
        party_code=_unique_code("P15B-CREATE"), party_name="Acme Supplier"
    )
    assert [e.party_id for e in calls] == [party.id]
    assert calls[0].organization_id == party.organization_id


def test_profile_update_produces_exactly_one_party_profile_updated(services):
    party_service = services["party_service"]
    party = party_service.create_party(party_code=_unique_code("P15B-PROFILE"), party_name="Before")
    calls = _spy(services, PartyProfileUpdated)

    party_service.update_party(party.id, party_name="After", expected_version=party.version)

    assert len(calls) == 1
    assert calls[0].party_id == party.id


def test_active_flag_toggle_is_a_profile_update_not_a_separate_event(services):
    party_service = services["party_service"]
    party = party_service.create_party(
        party_code=_unique_code("P15B-TOGGLE"), party_name="Active Party", is_active=True
    )
    calls = _spy(services, PartyProfileUpdated)

    updated = party_service.update_party(party.id, is_active=False, expected_version=party.version)

    assert [e.party_id for e in calls] == [party.id]
    assert updated.is_active is False


def test_no_op_update_produces_zero_events_zero_write_zero_audit_zero_updated_at_bump(services, monkeypatch):
    party_service = services["party_service"]
    party = party_service.create_party(party_code=_unique_code("P15B-NOOP"), party_name="Same Name")
    before = party_service._party_repo.get(party.id)
    profile_calls = _spy(services, PartyProfileUpdated)
    audit_calls = []
    monkeypatch.setattr(
        EnterpriseAuditService, "record", lambda self, **kwargs: audit_calls.append(kwargs)
    )

    result = party_service.update_party(
        party.id, party_name="Same Name", expected_version=party.version
    )

    assert result.version == party.version
    assert profile_calls == []
    assert audit_calls == []
    reloaded = party_service._party_repo.get(party.id)
    assert reloaded.version == before.version
    assert reloaded.updated_at == before.updated_at


def test_duplicate_code_create_produces_zero_event(services):
    party_service = services["party_service"]
    code = _unique_code("P15B-DUPE")
    party_service.create_party(party_code=code, party_name="First")
    calls = _spy(services, PartyCreated)

    from src.core.platform.common.exceptions import ValidationError

    with pytest.raises(ValidationError):
        party_service.create_party(party_code=code, party_name="Second")

    assert calls == []


def test_cross_org_update_produces_zero_event(services):
    party_service = services["party_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    party = party_service.create_party(party_code=_unique_code("P15B-CROSSORG"), party_name="Home Org Party")

    other_organization = organization_service.create_organization(
        organization_code=_unique_code("P15B-CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    calls = _spy(services, PartyProfileUpdated)
    try:
        from src.core.platform.common.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            party_service.update_party(party.id, party_name="Hijacked")
    finally:
        tenant_context_service.set_active_organization(default_organization.id)

    assert calls == []


def test_stale_version_update_produces_zero_event(services):
    party_service = services["party_service"]
    party = party_service.create_party(party_code=_unique_code("P15B-STALE"), party_name="Stale Party")
    calls = _spy(services, PartyProfileUpdated)

    from src.core.platform.common.exceptions import ConcurrencyError

    with pytest.raises(ConcurrencyError):
        party_service.update_party(
            party.id, party_name="Should Not Apply", expected_version=party.version + 1
        )

    assert calls == []


def test_commit_failure_produces_zero_postcommit_event(services, monkeypatch):
    from src.core.platform.infrastructure.persistence.uow.party_unit_of_work import (
        SqlAlchemyPartyUnitOfWork,
    )

    party_service = services["party_service"]
    calls = _spy(services, PartyCreated)

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyPartyUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        party_service.create_party(party_code=_unique_code("P15B-COMMITFAIL"), party_name="Commit Fail")

    assert calls == []


def test_admin_console_sub_controller_refreshes_once_after_committed_create(services):
    catalog = _platform_catalog(services)
    catalog.adminWorkspace.parties

    refresh_calls = []
    catalog.adminWorkspace._party_controller.refresh = (
        lambda: refresh_calls.append("admin-parties") or None
    )

    services["party_service"].create_party(
        party_code=_unique_code("P15B-ADMIN-CREATE"), party_name="Admin Refresh Party"
    )

    assert refresh_calls == ["admin-parties"]


def test_admin_console_sub_controller_refreshes_once_after_update(services):
    party_service = services["party_service"]
    party = party_service.create_party(
        party_code=_unique_code("P15B-ADMIN-UPDATE"), party_name="Before"
    )

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.parties

    refresh_calls = []
    catalog.adminWorkspace._party_controller.refresh = (
        lambda: refresh_calls.append("admin-parties") or None
    )

    party_service.update_party(party.id, party_name="After", expected_version=party.version)

    assert refresh_calls == ["admin-parties"]


def test_admin_console_no_refresh_on_no_op_update(services):
    party_service = services["party_service"]
    party = party_service.create_party(party_code=_unique_code("P15B-ADMIN-NOOP"), party_name="Same")

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.parties

    refresh_calls = []
    catalog.adminWorkspace._party_controller.refresh = (
        lambda: refresh_calls.append("admin-parties") or None
    )

    party_service.update_party(party.id, party_name="Same", expected_version=party.version)

    assert refresh_calls == []


def test_admin_console_no_refresh_on_failed_transaction(services):
    party_service = services["party_service"]
    code = _unique_code("P15B-ADMIN-FAILED")
    party_service.create_party(party_code=code, party_name="Existing")

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.parties

    refresh_calls = []
    catalog.adminWorkspace._party_controller.refresh = (
        lambda: refresh_calls.append("admin-parties") or None
    )

    from src.core.platform.common.exceptions import ValidationError

    with pytest.raises(ValidationError):
        party_service.create_party(party_code=code, party_name="Duplicate")

    assert refresh_calls == []


def test_no_forbidden_party_changed_event_name_exists():
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if re.search(r"\bPartyChanged\b", source) or re.search(r"\bPartyUpdated\b", source):
            hits.append(normalized)
    assert hits == [], hits


def test_canonical_party_uow_retained_no_raw_session_commit():
    import src.core.platform.application.master_data.party.party_service as party_service_module

    source = inspect.getsource(party_service_module.PartyService.create_party) + inspect.getsource(
        party_service_module.PartyService.update_party
    )
    assert "self._session.commit(" not in source
    assert "self._session.rollback(" not in source
    assert "uow.commit()" in source


def test_no_platform_to_business_module_concrete_infrastructure_import():
    import src.core.platform.infrastructure.persistence.uow.party_unit_of_work as infra_module

    source = inspect.getsource(infra_module)
    assert "core.modules" not in source


def test_two_separate_party_commits_produce_exactly_two_party_list_hints(services):
    party_service = services["party_service"]
    hints = _spy_party_list_hints(services)

    party_service.create_party(party_code=_unique_code("P15B-SEP-A"), party_name="Separate A")
    party_service.create_party(party_code=_unique_code("P15B-SEP-B"), party_name="Separate B")

    assert len(hints) == 2


def test_failed_transaction_produces_zero_party_list_hints(services):
    party_service = services["party_service"]
    code = _unique_code("P15B-FAILED")
    party_service.create_party(party_code=code, party_name="Existing")
    hints = _spy_party_list_hints(services)

    from src.core.platform.common.exceptions import ValidationError

    with pytest.raises(ValidationError):
        party_service.create_party(party_code=code, party_name="Duplicate")

    assert hints == []
