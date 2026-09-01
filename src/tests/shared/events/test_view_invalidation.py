"""ADR-005 §12: EventScope / ScopeFilter / ViewInvalidationHint / ViewInvalidationChannel.

P1 is contracts only -- there is no concrete channel to exercise the full tenant/organization
*routing* matrix (TO-1 through TO-9, TO-13) against yet; that is P2's job, against
InProcessViewInvalidationChannel. What P1 *can* and must prove is TO-10 (structural
impossibility of an organization-scoped fact with no organization, and of a tenant-scoped fact
with one) plus the `ScopeFilter.matches()` routing *logic* itself, since that logic is defined
here, in the contract, not only in a future concrete channel.
"""

from __future__ import annotations

import dataclasses

import pytest

from src.core.shared.events.view_invalidation import (
    AllTenants,
    AnyOrganizationInTenant,
    EventScope,
    ExactOrganization,
    ExactResource,
    OrganizationScope,
    PlatformScope,
    PlatformWide,
    ResourceScope,
    ScopeFilter,
    TenantScope,
    TenantWide,
    ViewInvalidationChannel,
    ViewInvalidationHandler,
    ViewInvalidationHint,
)

# ---------------------------------------------------------------------------
# EventScope: PlatformScope / TenantScope / OrganizationScope
# ---------------------------------------------------------------------------


def test_platform_scope_carries_no_tenant_or_organization_fields() -> None:
    scope = PlatformScope()
    assert dataclasses.fields(PlatformScope) == ()
    assert scope == PlatformScope()


def test_tenant_scope_requires_tenant_id() -> None:
    with pytest.raises(TypeError):
        TenantScope()  # type: ignore[call-arg]

    scope = TenantScope(tenant_id="A")
    assert scope.tenant_id == "A"


def test_tenant_scope_has_no_organization_id_field_at_all() -> None:
    """TO-10 (ADR-005 §12): a genuinely tenant-wide fact cannot be constructed with an
    organization_id -- not rejected at runtime, but structurally absent from the type."""
    field_names = {f.name for f in dataclasses.fields(TenantScope)}
    assert field_names == {"tenant_id"}

    with pytest.raises(TypeError):
        TenantScope(tenant_id="A", organization_id="A1")  # type: ignore[call-arg]


def test_organization_scope_requires_both_tenant_id_and_organization_id() -> None:
    """TO-10 (ADR-005 §12): an organization-scoped fact cannot omit organization_id -- this
    is a construction-time TypeError from the dataclass's own required-argument signature,
    never a runtime validation check discovered later during dispatch."""
    with pytest.raises(TypeError):
        OrganizationScope(tenant_id="A")  # type: ignore[call-arg]

    with pytest.raises(TypeError):
        OrganizationScope(organization_id="A1")  # type: ignore[call-arg]

    with pytest.raises(TypeError):
        OrganizationScope()  # type: ignore[call-arg]

    scope = OrganizationScope(tenant_id="A", organization_id="A1")
    assert scope.tenant_id == "A"
    assert scope.organization_id == "A1"


def test_all_three_scope_kinds_are_frozen() -> None:
    tenant_scope = TenantScope(tenant_id="A")
    with pytest.raises(dataclasses.FrozenInstanceError):
        tenant_scope.tenant_id = "B"  # type: ignore[misc]

    org_scope = OrganizationScope(tenant_id="A", organization_id="A1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        org_scope.organization_id = "A2"  # type: ignore[misc]


def test_scope_equality_and_hash_distinguish_by_value() -> None:
    """Equality/hash matter here because ScopeFilter.matches() and any future channel
    registry may key or compare scopes by value, not identity."""
    assert OrganizationScope("A", "A1") == OrganizationScope("A", "A1")
    assert hash(OrganizationScope("A", "A1")) == hash(OrganizationScope("A", "A1"))

    assert OrganizationScope("A", "A1") != OrganizationScope("A", "A2")
    assert OrganizationScope("A", "A1") != OrganizationScope("B", "A1")
    assert TenantScope("A") != OrganizationScope("A", "A1")
    assert PlatformScope() == PlatformScope()


def test_tenant_wide_scope_must_be_explicitly_constructed_as_tenant_scope() -> None:
    """There is no helper, default, or fallback path anywhere in this contract that turns
    'organization unknown' into TenantScope -- the only way to get a TenantScope is to
    construct one directly, naming the tenant explicitly (ADR-005 §3/§12's invariant)."""
    scope = TenantScope(tenant_id="A")
    assert isinstance(scope, TenantScope)
    assert not isinstance(scope, OrganizationScope)


def test_platform_wide_scope_must_be_explicitly_constructed() -> None:
    scope = PlatformScope()
    assert isinstance(scope, PlatformScope)
    assert not isinstance(scope, (TenantScope, OrganizationScope))


# ---------------------------------------------------------------------------
# ViewInvalidationHint
# ---------------------------------------------------------------------------


def test_view_invalidation_hint_requires_a_scope() -> None:
    with pytest.raises(TypeError):
        ViewInvalidationHint(  # type: ignore[call-arg]
            category="cat", scope_code="sc", entity_type="task"
        )


def test_view_invalidation_hint_preserves_the_exact_scope_it_was_given() -> None:
    scope = OrganizationScope(tenant_id="A", organization_id="A1")
    hint = ViewInvalidationHint(
        scope=scope, category="cat", scope_code="sc", entity_type="task", entity_id="t1"
    )

    assert hint.scope == scope
    assert hint.scope is scope


def test_view_invalidation_hint_entity_id_is_optional() -> None:
    hint = ViewInvalidationHint(
        scope=PlatformScope(), category="cat", scope_code="sc", entity_type="module_runtime"
    )
    assert hint.entity_id is None


def test_view_invalidation_hint_is_frozen_and_kw_only() -> None:
    hint = ViewInvalidationHint(
        scope=TenantScope("A"), category="cat", scope_code="sc", entity_type="policy"
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        hint.category = "other"  # type: ignore[misc]

    with pytest.raises(TypeError):
        ViewInvalidationHint(TenantScope("A"), "cat", "sc", "policy")  # type: ignore[misc, call-arg]


def test_an_organization_scoped_hint_never_implicitly_widens_to_tenant_scope() -> None:
    """No constructor path, default, or coercion anywhere in this contract turns an
    OrganizationScope hint into a TenantScope one -- widening never happens implicitly."""
    org_scope = OrganizationScope(tenant_id="A", organization_id="A1")
    hint = ViewInvalidationHint(scope=org_scope, category="cat", scope_code="sc", entity_type="task")

    assert isinstance(hint.scope, OrganizationScope)
    assert not isinstance(hint.scope, TenantScope) or isinstance(hint.scope, OrganizationScope)
    # OrganizationScope and TenantScope are siblings under EventScope, not a subtype
    # relationship -- an OrganizationScope must never satisfy isinstance(..., TenantScope).
    assert not isinstance(org_scope, TenantScope)


# ---------------------------------------------------------------------------
# Multi-organization effect rule (ADR-005 §3a) -- representable, not collapsible
# ---------------------------------------------------------------------------


def test_a_two_organization_effect_is_representable_as_two_hints_never_one_tenant_wide_hint() -> None:
    """ADR-005 §3a: a mutation affecting exactly {A1, A2} within Tenant A, not A3, is
    represented as two OrganizationScope-scoped hints -- this contract must permit that
    representation and must not offer any shortcut that collapses it into TenantScope."""
    affected_organization_ids = ("A1", "A2")

    hints = [
        ViewInvalidationHint(
            scope=OrganizationScope(tenant_id="A", organization_id=organization_id),
            category="cat",
            scope_code="sc",
            entity_type="shared_resource",
            entity_id="res-1",
        )
        for organization_id in affected_organization_ids
    ]

    assert len(hints) == 2
    assert {hint.scope.organization_id for hint in hints} == {"A1", "A2"}
    assert all(isinstance(hint.scope, OrganizationScope) for hint in hints)
    assert not any(isinstance(hint.scope, TenantScope) for hint in hints)


def test_exact_organization_filter_for_the_unaffected_third_organization_matches_neither_hint() -> None:
    a1_hint_scope = OrganizationScope(tenant_id="A", organization_id="A1")
    a2_hint_scope = OrganizationScope(tenant_id="A", organization_id="A2")
    unaffected_org_filter = ExactOrganization(tenant_id="A", organization_id="A3")

    assert unaffected_org_filter.matches(a1_hint_scope) is False
    assert unaffected_org_filter.matches(a2_hint_scope) is False


# ---------------------------------------------------------------------------
# ScopeFilter routing logic (defined in the contract itself, testable without a channel)
# ---------------------------------------------------------------------------


@pytest.fixture()
def scopes() -> dict[str, EventScope]:
    return {
        "platform": PlatformScope(),
        "tenant_a": TenantScope(tenant_id="A"),
        "tenant_b": TenantScope(tenant_id="B"),
        "org_a1": OrganizationScope(tenant_id="A", organization_id="A1"),
        "org_a2": OrganizationScope(tenant_id="A", organization_id="A2"),
        "org_b1": OrganizationScope(tenant_id="B", organization_id="B1"),
    }


def test_exact_organization_matches_only_its_own_tenant_and_organization(scopes) -> None:
    filt = ExactOrganization(tenant_id="A", organization_id="A1")

    assert filt.matches(scopes["org_a1"]) is True
    assert filt.matches(scopes["org_a2"]) is False
    assert filt.matches(scopes["org_b1"]) is False
    assert filt.matches(scopes["tenant_a"]) is False
    assert filt.matches(scopes["platform"]) is False


def test_tenant_wide_matches_only_genuinely_tenant_wide_facts_for_its_tenant(scopes) -> None:
    filt = TenantWide(tenant_id="A")

    assert filt.matches(scopes["tenant_a"]) is True
    assert filt.matches(scopes["tenant_b"]) is False
    assert filt.matches(scopes["org_a1"]) is False, "an org-scoped hint must never reach a tenant-wide-only subscriber"
    assert filt.matches(scopes["platform"]) is False


def test_any_organization_in_tenant_matches_tenant_wide_and_every_organization_of_its_tenant(scopes) -> None:
    filt = AnyOrganizationInTenant(tenant_id="A")

    assert filt.matches(scopes["tenant_a"]) is True
    assert filt.matches(scopes["org_a1"]) is True
    assert filt.matches(scopes["org_a2"]) is True
    assert filt.matches(scopes["tenant_b"]) is False
    assert filt.matches(scopes["org_b1"]) is False
    assert filt.matches(scopes["platform"]) is False


def test_all_tenants_matches_every_tenant_scoped_fact_but_never_platform_scope(scopes) -> None:
    filt = AllTenants()

    assert filt.matches(scopes["tenant_a"]) is True
    assert filt.matches(scopes["tenant_b"]) is True
    assert filt.matches(scopes["org_a1"]) is True
    assert filt.matches(scopes["org_b1"]) is True
    assert filt.matches(scopes["platform"]) is False


def test_platform_wide_matches_only_platform_scope(scopes) -> None:
    filt = PlatformWide()

    assert filt.matches(scopes["platform"]) is True
    assert filt.matches(scopes["tenant_a"]) is False
    assert filt.matches(scopes["org_a1"]) is False


def test_all_tenants_and_any_organization_in_tenant_are_not_the_same_filter() -> None:
    """ADR-005 §12's explicit warning: AllTenants must not be conflated with
    AnyOrganizationInTenant, which is still scoped to one tenant."""
    all_tenants = AllTenants()
    one_tenant_breadth = AnyOrganizationInTenant(tenant_id="A")

    other_tenant_scope = OrganizationScope(tenant_id="B", organization_id="B1")

    assert all_tenants.matches(other_tenant_scope) is True
    assert one_tenant_breadth.matches(other_tenant_scope) is False


# ---------------------------------------------------------------------------
# ViewInvalidationChannel / ViewInvalidationHandler: structural contract shape only
# ---------------------------------------------------------------------------


def test_view_invalidation_channel_exposes_exactly_notify_and_subscribe() -> None:
    """ADR-005 §12: one notify, one subscribe -- not five separately-named subscribe_*
    methods (the rejected, superseded design)."""
    assert hasattr(ViewInvalidationChannel, "notify")
    assert hasattr(ViewInvalidationChannel, "subscribe")

    for rejected_method in (
        "notify_platform_wide",
        "subscribe_tenant_wide",
        "subscribe_across_organizations",
        "subscribe_across_tenants",
        "subscribe_to_platform_wide",
    ):
        assert not hasattr(ViewInvalidationChannel, rejected_method), (
            f"{rejected_method} is part of the rejected/superseded five-method API and must "
            "not reappear on ViewInvalidationChannel"
        )


def test_view_invalidation_handler_and_scope_filter_are_distinct_protocols() -> None:
    assert ViewInvalidationHandler is not ScopeFilter


# ---------------------------------------------------------------------------
# ResourceScope (P16D-FIX): generic 4th EventScope kind, one resource within one organization
# ---------------------------------------------------------------------------


def test_resource_scope_requires_all_five_identity_fields() -> None:
    with pytest.raises(TypeError):
        ResourceScope(tenant_id="A", organization_id="A1", module_code="qhse", entity_type="inspection")  # type: ignore[call-arg]

    scope = ResourceScope(
        tenant_id="A", organization_id="A1", module_code="qhse", entity_type="inspection", entity_id="i1"
    )
    assert (scope.tenant_id, scope.organization_id, scope.module_code, scope.entity_type, scope.entity_id) == (
        "A", "A1", "qhse", "inspection", "i1",
    )


def test_resource_scope_is_frozen_and_value_comparable() -> None:
    scope = ResourceScope("A", "A1", "qhse", "inspection", "i1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        scope.entity_id = "i2"  # type: ignore[misc]

    assert ResourceScope("A", "A1", "qhse", "inspection", "i1") == ResourceScope("A", "A1", "qhse", "inspection", "i1")
    assert ResourceScope("A", "A1", "qhse", "inspection", "i1") != ResourceScope("A", "A1", "qhse", "inspection", "i2")
    assert not isinstance(scope, OrganizationScope)
    assert not isinstance(OrganizationScope("A", "A1"), ResourceScope)


def test_view_invalidation_hint_has_no_module_code_field() -> None:
    """P16D-FIX: capability-specific targeting identity (e.g. Document's module_code) lives in
    a typed EventScope variant (ResourceScope), never as an accumulating optional field directly
    on the shared hint."""
    hint_fields = {f.name for f in dataclasses.fields(ViewInvalidationHint)}
    assert hint_fields == {"scope", "category", "scope_code", "entity_type", "entity_id"}


def test_exact_organization_matches_resource_scope_in_its_own_organization() -> None:
    """A resource is always inside exactly one organization -- 'this organization's views'
    must include hints for its resources too, exactly as it already includes plain
    OrganizationScope hints (existing scope matching is unchanged by this extension)."""
    filt = ExactOrganization(tenant_id="A", organization_id="A1")
    own_resource = ResourceScope("A", "A1", "qhse", "inspection", "i1")
    other_org_resource = ResourceScope("A", "A2", "qhse", "inspection", "i1")
    other_tenant_resource = ResourceScope("B", "A1", "qhse", "inspection", "i1")

    assert filt.matches(own_resource) is True
    assert filt.matches(other_org_resource) is False
    assert filt.matches(other_tenant_resource) is False


def test_tenant_wide_and_platform_wide_never_match_resource_scope() -> None:
    resource = ResourceScope("A", "A1", "qhse", "inspection", "i1")

    assert TenantWide(tenant_id="A").matches(resource) is False
    assert PlatformWide().matches(resource) is False


def test_any_organization_in_tenant_and_all_tenants_match_resource_scope(scopes) -> None:
    resource_a1 = ResourceScope("A", "A1", "qhse", "inspection", "i1")
    resource_b1 = ResourceScope("B", "B1", "qhse", "inspection", "i1")

    assert AnyOrganizationInTenant(tenant_id="A").matches(resource_a1) is True
    assert AnyOrganizationInTenant(tenant_id="A").matches(resource_b1) is False
    assert AllTenants().matches(resource_a1) is True
    assert AllTenants().matches(resource_b1) is True


def test_exact_resource_matches_only_the_one_named_resource() -> None:
    filt = ExactResource(
        tenant_id="A", organization_id="A1", module_code="qhse", entity_type="inspection", entity_id="i1"
    )
    same = ResourceScope("A", "A1", "qhse", "inspection", "i1")
    different_entity = ResourceScope("A", "A1", "qhse", "inspection", "i2")
    different_module = ResourceScope("A", "A1", "other_module", "inspection", "i1")
    owning_organization_as_a_whole = OrganizationScope("A", "A1")

    assert filt.matches(same) is True
    assert filt.matches(different_entity) is False
    assert filt.matches(different_module) is False
    assert filt.matches(owning_organization_as_a_whole) is False


def test_existing_organization_scope_matching_is_unaffected_by_resource_scope(scopes) -> None:
    """Regression: adding ResourceScope must not change how any filter matches the pre-existing
    three scope kinds."""
    assert ExactOrganization(tenant_id="A", organization_id="A1").matches(scopes["org_a1"]) is True
    assert ExactOrganization(tenant_id="A", organization_id="A1").matches(scopes["org_a2"]) is False
    assert TenantWide(tenant_id="A").matches(scopes["tenant_a"]) is True
    assert TenantWide(tenant_id="A").matches(scopes["org_a1"]) is False
    assert AnyOrganizationInTenant(tenant_id="A").matches(scopes["org_a1"]) is True
    assert AllTenants().matches(scopes["org_b1"]) is True
    assert PlatformWide().matches(scopes["platform"]) is True
