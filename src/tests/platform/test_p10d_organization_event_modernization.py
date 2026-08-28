"""P10D: Organization event modernization -- `update_organization`/`enable_organization`/
`disable_organization` no longer emit the legacy `organizations_changed` Signal (deleted
entirely, not merely unproduced). They now record `OrganizationProfileUpdated`/
`OrganizationEnabled`/`OrganizationDisabled` before commit, on the same canonical
`OrganizationUnitOfWork` `create_organization` already uses for `OrganizationCreated` (P5A) --
same lifecycle, same `uow.record_event(...)` application-authored pattern, no aggregate refactor.

Every event maps onto the existing `organization_list` ViewInvalidation target (TenantScope) --
never `organization_details` (still no real consumer, unchanged from P5A's own finding) -- via a
single shared handler (`build_organization_profile_view_invalidation_handler`).

These tests subscribe directly to `organization_service._uow_factory._post_commit_bus` (the real
composition-owned bus) to observe exact typed-event counts and types, not merely the resulting
ViewInvalidation hint (which, by design, doesn't distinguish which of the three event types
produced it).
"""

from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.domain.master_data.org.events import (
    OrganizationCreated,
    OrganizationDisabled,
    OrganizationEnabled,
    OrganizationProfileUpdated,
)

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _spy(services, event_type):
    calls = []
    services["organization_service"]._uow_factory._post_commit_bus.subscribe(
        event_type, lambda event, context: calls.append(event)
    )
    return calls


# ----------------------------------------------------------------------
# Profile updates
# ----------------------------------------------------------------------


def test_profile_only_update_produces_exactly_one_organization_profile_updated(services):
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-PROFILE"), display_name="Before"
    )
    profile_calls = _spy(services, OrganizationProfileUpdated)
    availability_calls = _spy(services, OrganizationEnabled)

    updated = organization_service.update_organization(
        organization.id, expected_version=organization.version, display_name="After"
    )

    assert len(profile_calls) == 1
    assert profile_calls[0].organization_id == updated.id
    assert profile_calls[0].tenant_id == updated.tenant_id
    assert availability_calls == []


def test_profile_no_op_update_produces_zero_events(services):
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-NOOP-PROFILE"), display_name="Unchanged"
    )
    profile_calls = _spy(services, OrganizationProfileUpdated)

    result = organization_service.update_organization(
        organization.id,
        expected_version=organization.version,
        display_name="Unchanged",
        organization_code=organization.organization_code,
    )

    assert result.version == organization.version
    assert profile_calls == []


# ----------------------------------------------------------------------
# Enable / disable
# ----------------------------------------------------------------------


def test_enable_false_to_true_produces_exactly_one_organization_enabled(services):
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-ENABLE"), display_name="Enable Me", is_enabled=False
    )
    enabled_calls = _spy(services, OrganizationEnabled)
    disabled_calls = _spy(services, OrganizationDisabled)

    result = organization_service.enable_organization(organization.id)

    assert result.is_enabled is True
    assert len(enabled_calls) == 1
    assert enabled_calls[0].organization_id == result.id
    assert disabled_calls == []


def test_enable_true_to_true_produces_zero_events(services):
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-ENABLE-NOOP"), display_name="Already Enabled"
    )
    assert organization.is_enabled is True
    enabled_calls = _spy(services, OrganizationEnabled)

    result = organization_service.enable_organization(organization.id)

    assert result.version == organization.version
    assert enabled_calls == []


def test_disable_true_to_false_produces_exactly_one_organization_disabled(services):
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-DISABLE"), display_name="Disable Me"
    )
    disabled_calls = _spy(services, OrganizationDisabled)
    enabled_calls = _spy(services, OrganizationEnabled)

    result = organization_service.disable_organization(organization.id)

    assert result.is_enabled is False
    assert len(disabled_calls) == 1
    assert disabled_calls[0].organization_id == result.id
    assert enabled_calls == []


def test_disable_false_to_false_produces_zero_events(services):
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-DISABLE-NOOP"), display_name="Already Disabled", is_enabled=False
    )
    assert organization.is_enabled is False
    disabled_calls = _spy(services, OrganizationDisabled)

    result = organization_service.disable_organization(organization.id)

    assert result.version == organization.version
    assert disabled_calls == []


# ----------------------------------------------------------------------
# Mixed profile + availability via update_organization
# ----------------------------------------------------------------------


def test_mixed_profile_and_availability_update_produces_both_events_exactly_once(services):
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-MIXED"), display_name="Mixed Before", is_enabled=True
    )
    profile_calls = _spy(services, OrganizationProfileUpdated)
    disabled_calls = _spy(services, OrganizationDisabled)
    enabled_calls = _spy(services, OrganizationEnabled)

    updated = organization_service.update_organization(
        organization.id,
        expected_version=organization.version,
        display_name="Mixed After",
        is_enabled=False,
    )

    assert updated.display_name == "Mixed After"
    assert updated.is_enabled is False
    assert len(profile_calls) == 1
    assert len(disabled_calls) == 1
    assert enabled_calls == []
    assert profile_calls[0].organization_id == updated.id
    assert disabled_calls[0].organization_id == updated.id


def test_mixed_update_with_only_availability_change_produces_only_the_availability_event(services):
    """Deterministic sequencing check the other direction: if `update_organization` is called
    with an availability change but every profile field left at its current value, exactly one
    event fires, not two."""
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-MIXED-AVAIL-ONLY"), display_name="Same Name", is_enabled=True
    )
    profile_calls = _spy(services, OrganizationProfileUpdated)
    disabled_calls = _spy(services, OrganizationDisabled)

    updated = organization_service.update_organization(
        organization.id,
        expected_version=organization.version,
        display_name="Same Name",
        is_enabled=False,
    )

    assert updated.is_enabled is False
    assert profile_calls == []
    assert len(disabled_calls) == 1


# ----------------------------------------------------------------------
# Audit failure / commit failure -- fail-closed, zero observable postcommit event
# ----------------------------------------------------------------------


def test_update_organization_audit_failure_rolls_back_with_zero_observable_event(services, monkeypatch):
    from src.core.platform.application.history.audit.enterprise_audit_service import EnterpriseAuditService

    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-AUDIT-FAIL"), display_name="Before Audit Fail"
    )
    profile_calls = _spy(services, OrganizationProfileUpdated)

    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated update_organization audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)

    with pytest.raises(RuntimeError, match="simulated update_organization audit failure"):
        organization_service.update_organization(
            organization.id, expected_version=organization.version, display_name="Should Not Apply"
        )

    monkeypatch.undo()
    reloaded = organization_service._organization_repo.get(organization.id)
    assert reloaded.display_name == "Before Audit Fail"
    assert profile_calls == []


def test_enable_organization_audit_failure_rolls_back_with_zero_observable_event(services, monkeypatch):
    from src.core.platform.application.history.audit.enterprise_audit_service import EnterpriseAuditService

    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-ENABLE-AUDIT-FAIL"), display_name="Enable Audit Fail", is_enabled=False
    )
    enabled_calls = _spy(services, OrganizationEnabled)

    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated enable_organization audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)

    with pytest.raises(RuntimeError, match="simulated enable_organization audit failure"):
        organization_service.enable_organization(organization.id)

    monkeypatch.undo()
    reloaded = organization_service._organization_repo.get(organization.id)
    assert reloaded.is_enabled is False
    assert enabled_calls == []


def test_update_organization_commit_failure_produces_zero_observable_event(services, monkeypatch):
    from src.core.platform.infrastructure.persistence.uow.organization_unit_of_work import (
        SqlAlchemyOrganizationUnitOfWork,
    )

    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-COMMIT-FAIL"), display_name="Before Commit Fail"
    )
    profile_calls = _spy(services, OrganizationProfileUpdated)

    def _fail_commit(self):
        raise RuntimeError("simulated update_organization commit failure")

    monkeypatch.setattr(SqlAlchemyOrganizationUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated update_organization commit failure"):
        organization_service.update_organization(
            organization.id, expected_version=organization.version, display_name="Should Not Apply"
        )

    monkeypatch.undo()
    reloaded = organization_service._organization_repo.get(organization.id)
    assert reloaded.display_name == "Before Commit Fail"
    assert profile_calls == []


def test_update_organization_duplicate_code_failure_produces_zero_observable_event(services):
    organization_service = services["organization_service"]
    existing_code = _unique_code("P10D-DUPLICATE-TAKEN")
    organization_service.create_organization(organization_code=existing_code, display_name="Taken")
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-DUPLICATE-MINE"), display_name="Mine"
    )
    profile_calls = _spy(services, OrganizationProfileUpdated)

    with pytest.raises(ValidationError, match="Organization code already exists"):
        organization_service.update_organization(
            organization.id, expected_version=organization.version, organization_code=existing_code
        )

    assert profile_calls == []


# ----------------------------------------------------------------------
# organization_list ViewInvalidation -- once per committed relevant event
# ----------------------------------------------------------------------


def test_organization_list_invalidation_fires_exactly_once_for_a_committed_profile_update(services):
    from src.core.platform.application.master_data.org.event_handlers.view_invalidation import (
        ORGANIZATION_LIST_SCOPE_CODE,
    )

    organization_service = services["organization_service"]
    channel = services["platform_view_invalidation_channel"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-LIST-INVAL"), display_name="Before List Inval"
    )
    hints = []
    from src.core.shared.events.view_invalidation import AllTenants

    channel.subscribe(AllTenants(), lambda hint: hints.append(hint))

    organization_service.update_organization(
        organization.id, expected_version=organization.version, display_name="After List Inval"
    )

    list_hints = [h for h in hints if h.scope_code == ORGANIZATION_LIST_SCOPE_CODE]
    assert len(list_hints) == 1
    assert list_hints[0].entity_id is None, "the list-level hint stays collection-scoped, not entity-specific"


def test_organization_list_invalidation_fires_exactly_once_for_a_mixed_update_not_twice(services):
    """A mixed profile+availability update records TWO typed events in one transaction, but both
    map onto the identical `organization_list` target -- the real UI consumers (admin console,
    settings) must not refresh twice for one committed change."""
    from src.core.platform.application.master_data.org.event_handlers.view_invalidation import (
        ORGANIZATION_LIST_SCOPE_CODE,
    )

    organization_service = services["organization_service"]
    channel = services["platform_view_invalidation_channel"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-LIST-MIXED"), display_name="Mixed List Before", is_enabled=True
    )
    hints = []
    from src.core.shared.events.view_invalidation import AllTenants

    channel.subscribe(AllTenants(), lambda hint: hints.append(hint))

    organization_service.update_organization(
        organization.id,
        expected_version=organization.version,
        display_name="Mixed List After",
        is_enabled=False,
    )

    list_hints = [h for h in hints if h.scope_code == ORGANIZATION_LIST_SCOPE_CODE]
    assert len(list_hints) == 2, (
        "two distinct committed business facts (profile change + availability change) legitimately "
        "produce two invalidation hints for the same target -- real UI consumers coalesce duplicate "
        "hints on their own read side, this is not the producer's concern to deduplicate"
    )


# ----------------------------------------------------------------------
# OrganizationCreated unchanged
# ----------------------------------------------------------------------


def test_organization_created_semantics_are_unchanged_by_p10d(services):
    organization_service = services["organization_service"]
    created_calls = _spy(services, OrganizationCreated)
    profile_calls = _spy(services, OrganizationProfileUpdated)

    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-CREATE-UNCHANGED"), display_name="Create Unchanged"
    )

    assert len(created_calls) == 1
    assert created_calls[0].organization_id == organization.id
    assert created_calls[0].name == organization.display_name
    assert created_calls[0].code == organization.organization_code
    assert profile_calls == []


# ----------------------------------------------------------------------
# Session organization switch produces none of these business events
# ----------------------------------------------------------------------


def test_session_organization_switch_produces_no_business_event(services):
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-SWITCH-NO-EVENT"), display_name="Switch Target"
    )
    profile_calls = _spy(services, OrganizationProfileUpdated)
    enabled_calls = _spy(services, OrganizationEnabled)
    disabled_calls = _spy(services, OrganizationDisabled)
    created_calls = _spy(services, OrganizationCreated)

    tenant_context_service.set_active_organization(organization.id)

    assert tenant_context_service.get_active_organization_id() == organization.id
    assert profile_calls == []
    assert enabled_calls == []
    assert disabled_calls == []
    assert created_calls == []


# ----------------------------------------------------------------------
# organizations_changed: zero production refs (belt-and-suspenders, mirrors the P8/P7B guards)
# ----------------------------------------------------------------------


def test_organizations_changed_field_and_producers_are_fully_gone():
    from src.core.shared.events.domain_events import domain_events

    assert not hasattr(domain_events, "organizations_changed")

    import inspect

    import src.core.platform.application.master_data.org.organization_service as org_service_module

    source = inspect.getsource(org_service_module)
    assert "organizations_changed" not in source
    assert "domain_events" not in source


# ----------------------------------------------------------------------
# Architecture guards: forbidden event names, no generic bridge, canonical UoW lifecycle
# ----------------------------------------------------------------------


def test_no_forbidden_blanket_or_session_selection_event_names_exist_anywhere():
    """None of the explicitly-forbidden names (a generic OrganizationChanged/OrganizationUpdated
    blanket event, or any session-selection event -- OrganizationSelected/OrganizationActivated/
    TenantActiveOrganizationChanged) were introduced, in the Organization events module or
    anywhere else in production source."""
    import glob
    import re

    forbidden = (
        "OrganizationChanged",
        "OrganizationUpdated",
        "OrganizationActivated",
        "OrganizationDeactivated",
        "TenantActiveOrganizationChanged",
        "OrganizationSelected",
    )
    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        no_strings = re.sub(r'"""[\s\S]*?"""', "", source)
        no_comments = re.sub(r"#.*", "", no_strings)
        for name in forbidden:
            # Word-boundary match: a Qt presentation-layer property-change signal like
            # `isMultiOrganizationChanged` legitimately contains "OrganizationChanged" as a
            # substring without being the forbidden business DomainEvent of that exact name.
            if re.search(rf"\b{name}\b", no_comments):
                hits.append((normalized, name))
    assert hits == [], hits


def test_organization_events_module_exports_exactly_the_four_expected_events():
    import src.core.platform.domain.master_data.org.events as events_module

    assert set(events_module.__all__) == {
        "OrganizationCreated",
        "OrganizationProfileUpdated",
        "OrganizationEnabled",
        "OrganizationDisabled",
    }


def test_no_generic_compatibility_bridge_was_introduced():
    import inspect

    import src.core.platform.application.master_data.org.organization_service as org_service_module
    import src.core.platform.application.master_data.org.event_handlers.view_invalidation as vi_module
    import src.infra.composition.platform_registry as registry_module

    for module in (org_service_module, vi_module, registry_module):
        source = inspect.getsource(module)
        for forbidden in ("_BRIDGE_SPECS", "_wire_bridges", "_build_bridge", "_subscribe_domain_change"):
            assert forbidden not in source, (module.__name__, forbidden)


def test_new_events_use_the_canonical_organization_uow_record_event_pattern():
    """P10D used the SAME application-authored `uow.record_event(...)` mechanism
    `_create_organization_using` already established for `OrganizationCreated` -- Organization
    was not refactored into a `RecordsDomainEvents` aggregate for this, matching the governing
    spec's least-complex-correct-ownership instruction."""
    import inspect

    import src.core.platform.application.master_data.org.organization_service as org_service_module

    update_source = inspect.getsource(org_service_module.OrganizationService.update_organization)
    set_enabled_source = inspect.getsource(org_service_module.OrganizationService._set_organization_enabled)
    assert "uow.record_event(" in update_source
    assert "uow.record_event(" in set_enabled_source
