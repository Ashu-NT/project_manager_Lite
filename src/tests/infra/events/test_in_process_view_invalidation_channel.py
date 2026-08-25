"""ADR-005 §12: `InProcessViewInvalidationChannel`.

Covers the implementation plan's TO-1..TO-9 and TO-13 matrix, plus subscription lifecycle and
failure-isolation tests. TO-10 through TO-12, TO-14 are P1-contract-level or P5/P6 obligations
(construction-time type safety; reading organization off a mutation, not session state;
review-time discipline) and are not re-tested here -- this file exercises the concrete
*channel's routing* specifically.
"""

from __future__ import annotations

import logging

import pytest

from src.core.shared.events.view_invalidation import (
    AllTenants,
    AnyOrganizationInTenant,
    ExactOrganization,
    OrganizationScope,
    PlatformScope,
    PlatformWide,
    TenantScope,
    TenantWide,
    ViewInvalidationHint,
)
from src.infra.events.in_process_view_invalidation_channel import InProcessViewInvalidationChannel


@pytest.fixture()
def channel() -> InProcessViewInvalidationChannel:
    return InProcessViewInvalidationChannel()


def _hint(scope, entity_id: str | None = None) -> ViewInvalidationHint:
    return ViewInvalidationHint(
        scope=scope, category="cat", scope_code="sc", entity_type="task", entity_id=entity_id
    )


# ---------------------------------------------------------------------------
# TO-1 .. TO-5: organization-scoped hint routing
# ---------------------------------------------------------------------------


def test_to1_organization_hint_reaches_exact_match_subscriber(channel) -> None:
    received: list[ViewInvalidationHint] = []
    channel.subscribe(ExactOrganization("A", "A1"), received.append)

    hint = _hint(OrganizationScope("A", "A1"))
    channel.notify(hint)

    assert received == [hint]


def test_to2_organization_hint_does_not_reach_a_different_organization_in_the_same_tenant(channel) -> None:
    received: list[ViewInvalidationHint] = []
    channel.subscribe(ExactOrganization("A", "A2"), received.append)

    channel.notify(_hint(OrganizationScope("A", "A1")))

    assert received == []


def test_to3_organization_hint_does_not_reach_a_different_tenant(channel) -> None:
    received: list[ViewInvalidationHint] = []
    channel.subscribe(ExactOrganization("B", "B1"), received.append)

    channel.notify(_hint(OrganizationScope("A", "A1")))

    assert received == []


def test_to4_organization_hint_reaches_any_organization_in_tenant_subscriber(channel) -> None:
    received: list[ViewInvalidationHint] = []
    channel.subscribe(AnyOrganizationInTenant("A"), received.append)

    hint = _hint(OrganizationScope("A", "A1"))
    channel.notify(hint)

    assert received == [hint]


def test_to5_organization_hint_does_not_reach_tenant_wide_only_subscriber(channel) -> None:
    received: list[ViewInvalidationHint] = []
    channel.subscribe(TenantWide("A"), received.append)

    channel.notify(_hint(OrganizationScope("A", "A1")))

    assert received == [], "an org-scoped hint must never reach a tenant-wide-only subscriber"


# ---------------------------------------------------------------------------
# TO-6 / TO-7: tenant-wide hint routing
# ---------------------------------------------------------------------------


def test_to6_tenant_wide_hint_reaches_tenant_wide_and_any_organization_in_tenant_subscribers(channel) -> None:
    tenant_wide_received: list[ViewInvalidationHint] = []
    any_org_received: list[ViewInvalidationHint] = []
    channel.subscribe(TenantWide("A"), tenant_wide_received.append)
    channel.subscribe(AnyOrganizationInTenant("A"), any_org_received.append)

    hint = _hint(TenantScope("A"))
    channel.notify(hint)

    assert tenant_wide_received == [hint]
    assert any_org_received == [hint]


def test_to7_tenant_wide_hint_never_reaches_an_exact_organization_subscriber(channel) -> None:
    received: list[ViewInvalidationHint] = []
    channel.subscribe(ExactOrganization("A", "A1"), received.append)

    channel.notify(_hint(TenantScope("A")))

    assert received == [], "a tenant-wide fact must not refresh one specific organization's view"


def test_tenant_wide_hint_does_not_reach_a_different_tenant(channel) -> None:
    received: list[ViewInvalidationHint] = []
    channel.subscribe(TenantWide("B"), received.append)

    channel.notify(_hint(TenantScope("A")))

    assert received == []


# ---------------------------------------------------------------------------
# TO-8 / TO-9: AllTenants / PlatformWide
# ---------------------------------------------------------------------------


def test_to8_platform_scope_hint_follows_explicit_platform_wide_semantics(channel) -> None:
    platform_received: list[ViewInvalidationHint] = []
    all_tenants_received: list[ViewInvalidationHint] = []
    channel.subscribe(PlatformWide(), platform_received.append)
    channel.subscribe(AllTenants(), all_tenants_received.append)

    hint = _hint(PlatformScope())
    channel.notify(hint)

    assert platform_received == [hint]
    assert all_tenants_received == [], "a platform-wide fact must never reach an AllTenants subscriber"


def test_to9_all_tenants_subscriber_receives_hints_from_every_tenant_but_not_platform_scope(channel) -> None:
    received: list[ViewInvalidationHint] = []
    channel.subscribe(AllTenants(), received.append)

    hint_a = _hint(OrganizationScope("A", "A1"))
    hint_b = _hint(TenantScope("B"))
    platform_hint = _hint(PlatformScope())

    channel.notify(hint_a)
    channel.notify(hint_b)
    channel.notify(platform_hint)

    assert received == [hint_a, hint_b]


# ---------------------------------------------------------------------------
# Entity/view targeting (category/scope_code/entity_type/entity_id) -- binder-level
# convenience filtering, applied by the subscriber's own callback, not the channel.
# ---------------------------------------------------------------------------


def test_entity_targeting_is_the_subscribers_own_responsibility_not_the_channels() -> None:
    """Only tenant/organization are structural boundaries the channel enforces (ADR-005
    Sec12); category/scope_code/entity_type/entity_id filtering is left to the subscriber's
    own callback, exactly as ADR-005 describes for binder-level convenience filters."""
    channel = InProcessViewInvalidationChannel()
    matched: list[ViewInvalidationHint] = []

    def only_tasks(hint: ViewInvalidationHint) -> None:
        if hint.entity_type == "task":
            matched.append(hint)

    channel.subscribe(ExactOrganization("A", "A1"), only_tasks)

    task_hint = ViewInvalidationHint(
        scope=OrganizationScope("A", "A1"), category="c", scope_code="sc", entity_type="task"
    )
    other_hint = ViewInvalidationHint(
        scope=OrganizationScope("A", "A1"), category="c", scope_code="sc", entity_type="document"
    )

    channel.notify(task_hint)
    channel.notify(other_hint)

    assert matched == [task_hint]


# ---------------------------------------------------------------------------
# TO-13: multi-organization effect as two targeted notifications
# ---------------------------------------------------------------------------


def test_to13_two_organization_effect_is_two_targeted_notifications_not_tenant_wide(channel) -> None:
    a1_received: list[ViewInvalidationHint] = []
    a2_received: list[ViewInvalidationHint] = []
    a3_received: list[ViewInvalidationHint] = []
    channel.subscribe(ExactOrganization("A", "A1"), a1_received.append)
    channel.subscribe(ExactOrganization("A", "A2"), a2_received.append)
    channel.subscribe(ExactOrganization("A", "A3"), a3_received.append)

    for organization_id in ("A1", "A2"):
        channel.notify(_hint(OrganizationScope("A", organization_id)))

    assert len(a1_received) == 1
    assert len(a2_received) == 1
    assert a3_received == [], "the unaffected third organization must receive nothing"


# ---------------------------------------------------------------------------
# Subscription lifecycle
# ---------------------------------------------------------------------------


def test_dispose_removes_the_subscriber(channel) -> None:
    received: list[ViewInvalidationHint] = []
    subscription = channel.subscribe(ExactOrganization("A", "A1"), received.append)

    subscription.dispose()
    channel.notify(_hint(OrganizationScope("A", "A1")))

    assert received == []


def test_dispose_is_idempotent(channel) -> None:
    subscription = channel.subscribe(PlatformWide(), lambda h: None)
    subscription.dispose()
    subscription.dispose()  # must not raise


def test_disposing_one_subscription_does_not_affect_an_independent_identical_subscription(channel) -> None:
    received: list[ViewInvalidationHint] = []

    def handler(hint: ViewInvalidationHint) -> None:
        received.append(hint)

    first_subscription = channel.subscribe(ExactOrganization("A", "A1"), handler)
    channel.subscribe(ExactOrganization("A", "A1"), handler)

    first_subscription.dispose()
    channel.notify(_hint(OrganizationScope("A", "A1")))

    assert len(received) == 1


def test_registration_and_subscription_are_isolated_between_independently_created_channels() -> None:
    channel_one = InProcessViewInvalidationChannel()
    channel_two = InProcessViewInvalidationChannel()

    received_on_one: list[ViewInvalidationHint] = []
    channel_one.subscribe(ExactOrganization("A", "A1"), received_on_one.append)

    channel_two.notify(_hint(OrganizationScope("A", "A1")))

    assert received_on_one == [], "a hint published on one channel instance must never reach a subscriber on another"


# ---------------------------------------------------------------------------
# Failure isolation
# ---------------------------------------------------------------------------


def test_one_failing_subscriber_does_not_block_a_sibling_subscriber(channel, caplog) -> None:
    calls: list[str] = []

    def failing(hint: ViewInvalidationHint) -> None:
        calls.append("failing")
        raise RuntimeError("Qt widget already deleted, or similar UI-adapter bug")

    def healthy(hint: ViewInvalidationHint) -> None:
        calls.append("healthy")

    channel.subscribe(ExactOrganization("A", "A1"), failing)
    channel.subscribe(ExactOrganization("A", "A1"), healthy)

    with caplog.at_level(logging.ERROR):
        channel.notify(_hint(OrganizationScope("A", "A1")))  # must not raise

    assert calls == ["failing", "healthy"]
    assert any("View invalidation subscriber failed" in r.message for r in caplog.records)


def test_notify_never_propagates_a_subscriber_exception(channel) -> None:
    def failing(hint: ViewInvalidationHint) -> None:
        raise ValueError("boom")

    channel.subscribe(PlatformWide(), failing)

    channel.notify(_hint(PlatformScope()))  # no pytest.raises -- must complete normally
