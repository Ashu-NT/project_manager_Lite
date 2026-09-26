"""`update_organization`/`activate_organization`/`deactivate_organization`/`archive_organization`
record `OrganizationProfileUpdated`/`OrganizationActivated`/`OrganizationDeactivated`/
`OrganizationArchived` before commit, on the same `OrganizationUnitOfWork` `create_organization`
uses for `OrganizationCreated` -- same lifecycle, same `uow.record_event(...)`
application-authored pattern, no aggregate refactor.

`update_organization` is a pure profile-only mutation -- it no longer carries a lifecycle-status
field, so a "mixed profile + availability" update through it is not a real code path any more.
Lifecycle transitions (`activate_organization`/`deactivate_organization`/`archive_organization`)
are their own single-purpose, `BusinessRuleError`-guarded operations that reject a same-state
transition outright rather than silently no-op'ing.

Every event maps onto the existing `organization_list` ViewInvalidation target (TenantScope) --
never `organization_details`, which has no real consumer -- via a single shared handler
(`build_organization_profile_view_invalidation_handler`).

These tests subscribe directly to `organization_service._uow_factory._post_commit_bus` (the real
composition-owned bus) to observe exact typed-event counts and types, not merely the resulting
ViewInvalidation hint (which, by design, doesn't distinguish which of the event types produced it).
"""

from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.domain.master_data.org.events import (
    OrganizationActivated,
    OrganizationArchived,
    OrganizationCreated,
    OrganizationDeactivated,
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
    activated_calls = _spy(services, OrganizationActivated)

    updated = organization_service.update_organization(
        organization.id, expected_version=organization.version, display_name="After"
    )

    assert len(profile_calls) == 1
    assert profile_calls[0].organization_id == updated.id
    assert profile_calls[0].tenant_id == updated.tenant_id
    assert activated_calls == []


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
# Activate / deactivate / archive
# ----------------------------------------------------------------------


def test_deactivate_active_organization_produces_exactly_one_organization_deactivated(services):
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-DEACTIVATE"), display_name="Deactivate Me"
    )
    deactivated_calls = _spy(services, OrganizationDeactivated)
    activated_calls = _spy(services, OrganizationActivated)

    result = organization_service.deactivate_organization(organization.id)

    assert result.status == "inactive"
    assert len(deactivated_calls) == 1
    assert deactivated_calls[0].organization_id == result.id
    assert activated_calls == []


def test_activate_inactive_organization_produces_exactly_one_organization_activated(services):
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-ACTIVATE"), display_name="Activate Me"
    )
    organization_service.deactivate_organization(organization.id)
    activated_calls = _spy(services, OrganizationActivated)
    deactivated_calls = _spy(services, OrganizationDeactivated)

    result = organization_service.activate_organization(organization.id)

    assert result.status == "active"
    assert len(activated_calls) == 1
    assert activated_calls[0].organization_id == result.id
    assert deactivated_calls == []


def test_archive_organization_produces_exactly_one_organization_archived(services):
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-ARCHIVE"), display_name="Archive Me"
    )
    archived_calls = _spy(services, OrganizationArchived)

    result = organization_service.archive_organization(organization.id)

    assert result.status == "archived"
    assert len(archived_calls) == 1
    assert archived_calls[0].organization_id == result.id


def test_activate_an_already_active_organization_is_rejected_with_zero_observable_event(services):
    """Same-state lifecycle transitions are not a silent no-op -- they're explicitly rejected by
    `BusinessRuleError`, distinct from `update_organization`'s no-op-tolerant profile semantics."""
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-ACTIVATE-NOOP"), display_name="Already Active"
    )
    assert organization.status == "active"
    activated_calls = _spy(services, OrganizationActivated)

    with pytest.raises(BusinessRuleError, match="already active"):
        organization_service.activate_organization(organization.id)

    assert activated_calls == []


def test_deactivate_an_already_inactive_organization_is_rejected_with_zero_observable_event(services):
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-DEACTIVATE-NOOP"), display_name="Already Inactive"
    )
    organization_service.deactivate_organization(organization.id)
    deactivated_calls = _spy(services, OrganizationDeactivated)

    with pytest.raises(BusinessRuleError, match="already inactive"):
        organization_service.deactivate_organization(organization.id)

    assert deactivated_calls == []


def test_archived_organization_cannot_be_reactivated_or_deactivated(services):
    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-ARCHIVED-TERMINAL"), display_name="Archived Terminal"
    )
    organization_service.archive_organization(organization.id)
    activated_calls = _spy(services, OrganizationActivated)
    deactivated_calls = _spy(services, OrganizationDeactivated)

    with pytest.raises(BusinessRuleError, match="[Aa]rchived"):
        organization_service.activate_organization(organization.id)
    with pytest.raises(BusinessRuleError, match="[Aa]rchived"):
        organization_service.deactivate_organization(organization.id)

    assert activated_calls == []
    assert deactivated_calls == []


# ----------------------------------------------------------------------
# update_organization no longer carries a lifecycle-status field
# ----------------------------------------------------------------------


def test_update_organization_has_no_lifecycle_status_parameter():
    """`update_organization` is a pure profile-only mutation -- lifecycle transitions are their
    own dedicated operations, never a side channel through the profile-update payload."""
    import inspect

    import src.core.platform.application.master_data.org.organization_service as org_service_module

    signature = inspect.signature(org_service_module.OrganizationService.update_organization)
    assert "is_enabled" not in signature.parameters
    assert "status" not in signature.parameters


# ----------------------------------------------------------------------
# Audit failure / commit failure -- fail-closed, zero observable postcommit event
# ----------------------------------------------------------------------


def test_update_organization_audit_failure_rolls_back_with_zero_observable_event(services, monkeypatch):
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

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


def test_deactivate_organization_audit_failure_rolls_back_with_zero_observable_event(services, monkeypatch):
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-DEACTIVATE-AUDIT-FAIL"), display_name="Deactivate Audit Fail"
    )
    deactivated_calls = _spy(services, OrganizationDeactivated)

    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated deactivate_organization audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)

    with pytest.raises(RuntimeError, match="simulated deactivate_organization audit failure"):
        organization_service.deactivate_organization(organization.id)

    monkeypatch.undo()
    reloaded = organization_service._organization_repo.get(organization.id)
    assert reloaded.status == "active"
    assert deactivated_calls == []


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


def test_organization_list_invalidation_fires_exactly_once_for_a_lifecycle_transition(services):
    from src.core.platform.application.master_data.org.event_handlers.view_invalidation import (
        ORGANIZATION_LIST_SCOPE_CODE,
    )

    organization_service = services["organization_service"]
    channel = services["platform_view_invalidation_channel"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("P10D-LIST-LIFECYCLE"), display_name="List Lifecycle"
    )
    hints = []
    from src.core.shared.events.view_invalidation import AllTenants

    channel.subscribe(AllTenants(), lambda hint: hints.append(hint))

    organization_service.deactivate_organization(organization.id)

    list_hints = [h for h in hints if h.scope_code == ORGANIZATION_LIST_SCOPE_CODE]
    assert len(list_hints) == 1


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
    activated_calls = _spy(services, OrganizationActivated)
    deactivated_calls = _spy(services, OrganizationDeactivated)
    created_calls = _spy(services, OrganizationCreated)

    tenant_context_service.set_active_organization(organization.id)

    assert tenant_context_service.get_active_organization_id() == organization.id
    assert profile_calls == []
    assert activated_calls == []
    assert deactivated_calls == []
    assert created_calls == []


# ----------------------------------------------------------------------
# organizations_changed: zero production refs (belt-and-suspenders)
# ----------------------------------------------------------------------


def test_organizations_changed_field_and_producers_are_fully_gone():
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
    blanket event, or any session-selection event -- OrganizationSelected/
    TenantActiveOrganizationChanged) were introduced, in the Organization events module or
    anywhere else in production source. `OrganizationActivated`/`OrganizationDeactivated` are
    legitimate lifecycle-status events (not session-selection events) and are intentionally
    excluded from this guard."""
    import glob
    import re

    forbidden = (
        "OrganizationChanged",
        "OrganizationUpdated",
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


def test_organization_events_module_exports_exactly_the_five_expected_events():
    import src.core.platform.domain.master_data.org.events as events_module

    assert set(events_module.__all__) == {
        "OrganizationCreated",
        "OrganizationProfileUpdated",
        "OrganizationActivated",
        "OrganizationDeactivated",
        "OrganizationArchived",
    }


def test_no_generic_compatibility_bridge_was_introduced():
    import inspect

    import src.core.platform.application.master_data.org.event_handlers.view_invalidation as vi_module
    import src.core.platform.application.master_data.org.organization_service as org_service_module
    import src.infra.composition.modules.platform_registry as registry_module

    for module in (org_service_module, vi_module, registry_module):
        source = inspect.getsource(module)
        for forbidden in ("_BRIDGE_SPECS", "_wire_bridges", "_build_bridge", "_subscribe_domain_change"):
            assert forbidden not in source, (module.__name__, forbidden)


def test_new_events_use_the_canonical_organization_uow_record_event_pattern():
    """Uses the SAME application-authored `uow.record_event(...)` mechanism
    `_create_organization_using` already established for `OrganizationCreated` -- Organization is
    not a `RecordsDomainEvents` aggregate."""
    import inspect

    import src.core.platform.application.master_data.org.organization_service as org_service_module

    update_source = inspect.getsource(org_service_module.OrganizationService.update_organization)
    # `_transition_organization_status` is the single unit of work shared by the
    # single-record and bulk activate/deactivate/archive paths -- that's where the
    # lifecycle event recording actually lives, not in each thin public wrapper.
    apply_status_source = inspect.getsource(org_service_module.OrganizationService._apply_organization_status)
    assert "uow.record_event(" in update_source
    assert "uow.record_event(" in apply_status_source
