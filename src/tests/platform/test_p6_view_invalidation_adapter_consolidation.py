from __future__ import annotations

import ast
import inspect

import pytest

from src.core.shared.events.view_invalidation import (
    ExactOrganization,
    TenantWide,
    ViewInvalidationHint,
)
from src.ui_qml.platform.adapters.scoped_view_invalidation_subscription import (
    ScopedViewInvalidationSubscription,
)

_ADAPTER_MODULES = (
    "src.ui_qml.platform.adapters.organization_view_invalidation_adapter",
    "src.ui_qml.platform.adapters.module_entitlement_view_invalidation_adapter",
    "src.ui_qml.platform.adapters.role_binding_view_invalidation_adapter",
    "src.ui_qml.platform.adapters.tenant_membership_view_invalidation_adapter",
    "src.ui_qml.platform.adapters.approval_view_invalidation_adapter",
)


# ---------------------------------------------------------------------------
# Shared helper: pure-Python unit tests, no QApplication/Qt involved at all
# ---------------------------------------------------------------------------


class _FakeSubscription:
    def __init__(self, channel, filter, handler):
        self.channel = channel
        self.filter = filter
        self.handler = handler
        self.disposed = False

    def dispose(self):
        self.disposed = True


class _FakeChannel:
    def __init__(self):
        self.subscribe_calls = []

    def subscribe(self, filter, handler):
        subscription = _FakeSubscription(self, filter, handler)
        self.subscribe_calls.append(subscription)
        return subscription

    def notify(self, hint):
        pass


def test_no_channel_never_subscribes():
    hints_received = []
    helper = ScopedViewInvalidationSubscription(channel=None, on_hint=hints_received.append)
    helper.replace_filter(TenantWide("t-1"))
    assert helper._subscription is None


def test_none_filter_goes_inert():
    channel = _FakeChannel()
    helper = ScopedViewInvalidationSubscription(channel=channel, on_hint=lambda hint: None)
    helper.replace_filter(None)
    assert helper._subscription is None
    assert channel.subscribe_calls == []


def test_replace_filter_subscribes_via_the_channel_with_the_given_filter():
    channel = _FakeChannel()
    helper = ScopedViewInvalidationSubscription(channel=channel, on_hint=lambda hint: None)
    filt = TenantWide("t-1")
    helper.replace_filter(filt)
    assert len(channel.subscribe_calls) == 1
    assert channel.subscribe_calls[0].filter is filt
    assert helper._subscription is channel.subscribe_calls[0]


def test_replace_filter_disposes_the_previous_subscription_before_creating_the_new_one():
    channel = _FakeChannel()
    helper = ScopedViewInvalidationSubscription(channel=channel, on_hint=lambda hint: None)
    helper.replace_filter(TenantWide("t-1"))
    first = channel.subscribe_calls[0]
    assert not first.disposed

    helper.replace_filter(TenantWide("t-2"))
    assert first.disposed, "the old subscription must be disposed before the new one is created"
    assert len(channel.subscribe_calls) == 2
    assert not channel.subscribe_calls[1].disposed


def test_replace_filter_with_the_same_filter_still_unconditionally_resubscribes():
    """No idempotence was added -- every pre-P6 adapter's own bespoke implementation always
    disposed and resubscribed on every rescope call, even for an unchanged filter. Preserving
    that exactly (rather than adding an equality short-circuit) avoids an unrequested behavior
    change in a consolidation-only phase."""
    channel = _FakeChannel()
    helper = ScopedViewInvalidationSubscription(channel=channel, on_hint=lambda hint: None)
    filt = TenantWide("t-1")
    helper.replace_filter(filt)
    first = channel.subscribe_calls[0]

    helper.replace_filter(TenantWide("t-1"))  # equal filter, new instance
    assert first.disposed
    assert len(channel.subscribe_calls) == 2
    assert helper._subscription is channel.subscribe_calls[1]


def test_replace_filter_none_after_a_live_subscription_disposes_without_resubscribing():
    channel = _FakeChannel()
    helper = ScopedViewInvalidationSubscription(channel=channel, on_hint=lambda hint: None)
    helper.replace_filter(TenantWide("t-1"))
    first = channel.subscribe_calls[0]

    helper.replace_filter(None)
    assert first.disposed
    assert helper._subscription is None
    assert len(channel.subscribe_calls) == 1, "going inert must not create a new subscription"


def test_dispose_is_safe_and_idempotent():
    channel = _FakeChannel()
    helper = ScopedViewInvalidationSubscription(channel=channel, on_hint=lambda hint: None)
    helper.replace_filter(TenantWide("t-1"))
    first = channel.subscribe_calls[0]

    helper.dispose()
    assert first.disposed
    assert helper._subscription is None

    helper.dispose()  # must not raise, must not double-dispose
    assert first.disposed


def test_dispose_before_any_subscription_is_a_safe_no_op():
    helper = ScopedViewInvalidationSubscription(channel=_FakeChannel(), on_hint=lambda hint: None)
    helper.dispose()  # must not raise
    assert helper._subscription is None


def test_on_hint_callback_is_the_channels_handler():
    channel = _FakeChannel()
    received = []
    helper = ScopedViewInvalidationSubscription(channel=channel, on_hint=received.append)
    helper.replace_filter(TenantWide("t-1"))
    hint = ViewInvalidationHint(
        scope=TenantWide("t-1"), category="x", scope_code="y", entity_type="z", entity_id="1"
    )
    channel.subscribe_calls[0].handler(hint)
    assert received == [hint]


def test_at_most_one_live_subscription_across_many_rescopes():
    channel = _FakeChannel()
    helper = ScopedViewInvalidationSubscription(channel=channel, on_hint=lambda hint: None)
    for i in range(5):
        helper.replace_filter(ExactOrganization(f"t-{i}", f"o-{i}"))
    live = [s for s in channel.subscribe_calls if not s.disposed]
    assert len(live) == 1


# ---------------------------------------------------------------------------
# Architecture guards: the helper's own isolation
# ---------------------------------------------------------------------------


def _strip_strings_and_comments(source: str) -> str:
    """Drop triple-quoted docstrings, string literals, and `#` comments so a structural scan
    only sees actual code, not prose that happens to mention a forbidden call/name."""
    import re

    no_docstrings = re.sub(r'"""[\s\S]*?"""', "", source)
    no_comments = re.sub(r"#.*", "", no_docstrings)
    return no_comments


def _imported_module_names(module) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_shared_helper_has_no_qt_dependency():
    import src.ui_qml.platform.adapters.scoped_view_invalidation_subscription as helper_module

    imports = _imported_module_names(helper_module)
    for forbidden in ("PySide6", "QtCore", "QtQml"):
        assert not any(forbidden in name for name in imports), imports


def test_shared_helper_has_no_domain_event_or_capability_vocabulary_imports():
    import src.ui_qml.platform.adapters.scoped_view_invalidation_subscription as helper_module

    imports = _imported_module_names(helper_module)
    for forbidden in (
        "domain_events",
        "domain_event",
        "approval",
        "role_binding",
        "tenant.tenancy",
        "tenant.modules",
        "master_data.org",
    ):
        assert not any(forbidden in name for name in imports), imports


def test_shared_helper_has_no_repository_or_sqlalchemy_imports():
    import src.ui_qml.platform.adapters.scoped_view_invalidation_subscription as helper_module

    imports = _imported_module_names(helper_module)
    for forbidden in ("sqlalchemy", "repository", "repositories", "orm"):
        assert not any(forbidden in name for name in imports), imports


def test_shared_helper_never_sees_a_tenant_or_organization_id_string():
    """The helper's public API is `replace_filter(filter: ScopeFilter | None)`/`dispose()` --
    it takes an already-authoritative ScopeFilter, never tenant_id/organization_id parameters."""
    import src.ui_qml.platform.adapters.scoped_view_invalidation_subscription as helper_module

    params = inspect.signature(helper_module.ScopedViewInvalidationSubscription.replace_filter).parameters
    assert set(params) == {"self", "filter"}
    init_params = inspect.signature(helper_module.ScopedViewInvalidationSubscription.__init__).parameters
    assert set(init_params) == {"self", "channel", "on_hint"}


def test_all_five_capability_adapters_use_the_shared_subscription_helper():
    import importlib

    for module_name in _ADAPTER_MODULES:
        module = importlib.import_module(module_name)
        imports = _imported_module_names(module)
        assert any("scoped_view_invalidation_subscription" in name for name in imports), (
            f"{module_name} does not delegate to the shared lifecycle helper"
        )


def test_no_adapter_module_references_all_tenants_or_any_organization_in_tenant():
    import importlib

    for module_name in _ADAPTER_MODULES:
        module = importlib.import_module(module_name)
        source = _strip_strings_and_comments(inspect.getsource(module))
        for forbidden in ("AllTenants", "AnyOrganizationInTenant"):
            assert forbidden not in source, f"{module_name} references {forbidden}"


def test_no_legacy_signal_reintroduced_in_any_adapter_or_the_shared_helper():
    import importlib

    modules = list(_ADAPTER_MODULES) + [
        "src.ui_qml.platform.adapters.scoped_view_invalidation_subscription"
    ]
    for module_name in modules:
        module = importlib.import_module(module_name)
        source = _strip_strings_and_comments(inspect.getsource(module))
        for forbidden in (
            "approvals_changed",
            "organizations_changed",
            "modules_changed",
            "access_changed",
            "auth_changed",
            "domain_changed",
        ):
            assert forbidden not in source, f"{module_name} references legacy signal {forbidden}"


def test_role_binding_adapter_retains_its_own_dual_subscription_specialization():
    """RoleBinding is the one capability that genuinely needs two simultaneous subscriptions
    (tenant-wide + exact-organization) -- the consolidation must not force it onto the generic
    single-subscription shape every other adapter uses."""
    import src.ui_qml.platform.adapters.role_binding_view_invalidation_adapter as mod

    module_source = inspect.getsource(mod)
    assert module_source.count("ScopedViewInvalidationSubscription(channel=") == 2, (
        "RoleBinding must construct exactly two helper instances -- tenant + organization"
    )


def test_other_four_adapters_construct_exactly_one_subscription_helper():
    import importlib

    single_subscription_modules = [
        m for m in _ADAPTER_MODULES if "role_binding" not in m
    ]
    for module_name in single_subscription_modules:
        module = importlib.import_module(module_name)
        source = inspect.getsource(module)
        assert source.count("ScopedViewInvalidationSubscription(channel=") == 1, module_name


def test_no_service_locator_or_generic_adapter_registry_introduced():
    from src.ui_qml.platform import context as platform_context_module
    from src.ui_qml.modules.project_management import context as pm_context_module

    for module in (platform_context_module, pm_context_module):
        source = _strip_strings_and_comments(inspect.getsource(module))
        for forbidden in ("adapter_for(", "resolve_adapter(", "container.get(", "AdapterRegistry"):
            assert forbidden not in source, f"{module.__name__} introduces {forbidden}"


def test_approval_event_contract_unchanged_by_p6():
    from src.core.platform.domain.approval import events as approval_events_module

    assert set(approval_events_module.__all__) == {
        "ApprovalRequested",
        "ApprovalApproved",
        "ApprovalRejected",
    }


def test_view_invalidation_hint_contract_unchanged_by_p6():
    from src.core.shared.events import view_invalidation as contract_module

    hint_fields = {f for f in ViewInvalidationHint.__dataclass_fields__}
    # P16D added `module_code` (optional, default None) -- see
    # test_p8_platform_event_architecture_canonicalization.py's own copy of this same contract
    # check for the full rationale.
    assert hint_fields == {"scope", "category", "scope_code", "entity_type", "entity_id", "module_code"}
    assert set(contract_module.__all__) == {
        "EventScope", "PlatformScope", "TenantScope", "OrganizationScope",
        "ViewInvalidationHint", "ViewInvalidationHandler", "ScopeFilter",
        "ExactOrganization", "TenantWide", "AnyOrganizationInTenant", "AllTenants",
        "PlatformWide", "ViewInvalidationChannel",
    }


def test_shared_helper_lives_outside_core_shared_and_platform_application():
    """§37: the helper is Qt/UI-boundary infrastructure, replaceable by a future web transport --
    it must never migrate into core/shared or Platform application code."""
    import src.ui_qml.platform.adapters.scoped_view_invalidation_subscription as helper_module

    assert helper_module.__name__.startswith("src.ui_qml.")
