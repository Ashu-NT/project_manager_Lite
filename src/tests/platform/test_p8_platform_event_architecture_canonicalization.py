from __future__ import annotations

import dataclasses
import glob
import inspect

from src.core.shared.events.domain_events import domain_events

# ---------------------------------------------------------------------------
# §26.5 / §6 / §19 / §20: the frozen legacy Signal allowlist
# ---------------------------------------------------------------------------

FROZEN_LEGACY_SIGNAL_ALLOWLIST = frozenset(
    {
        "project_changed",
        "tasks_changed",
        "timesheet_periods_changed",
        "resources_changed",
        "baseline_changed",
        "budgets_changed",
        "billing_preparations_changed",
        "planned_costs_changed",
        "register_changed",
        "auth_changed",
        "employees_changed",
        "organizations_changed",
        "sites_changed",
        "departments_changed",
        "documents_changed",
        "parties_changed",
        "collaboration_changed",
        "portfolio_changed",
        "inventory_items_changed",
        "inventory_item_categories_changed",
        "inventory_storerooms_changed",
        "inventory_balances_changed",
        "inventory_reservations_changed",
        "inventory_requisitions_changed",
        "inventory_purchase_orders_changed",
        "inventory_receipts_changed",
        "inventory_locations_changed",
        "inventory_reorder_policies_changed",
        "inventory_cycle_counts_changed",
    }
)

_DELETED_BRIDGE_NAMES = (
    "_BRIDGE_SPECS",
    "_wire_bridges",
    "_build_bridge",
    "domain_changed",
    "DomainChangeEvent",
    "_subscribe_domain_change",
    "shared_master_changed",
    "costs_changed",
    "calendars_changed",
    "forecasts_changed",
    "financial_changes_changed",
    "commitments_changed",
    "cost_entries_changed",
    "budgets_changed",
    "billing_preparations_changed",
    "timesheet_periods_changed",
    "register_changed",
    "portfolio_changed",
    "project_changed",
    "collaboration_changed",
    "tasks_changed",
)

_KNOWN_FINANCE_SIGNAL_NAMES = frozenset(
    {
        "budgets_changed",
        "billing_preparations_changed",
        "cost_entries_changed",
        "commitments_changed",
        "financial_changes_changed",
        "forecasts_changed",
        "planned_costs_changed",
        "costs_changed",
    }
)


def _strip_strings_and_comments(source: str) -> str:
    import re

    no_docstrings = re.sub(r'"""[\s\S]*?"""', "", source)
    no_comments = re.sub(r"#.*", "", no_docstrings)
    return no_comments


def _production_source_files():
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        yield normalized


def _current_signal_names() -> set[str]:
    return {f.name for f in dataclasses.fields(domain_events)}


def test_current_signals_are_a_subset_of_the_frozen_allowlist_not_equal():
    """The core non-growth invariant: current ⊆ frozen, checked as a subset -- a future
    migration deleting an allowlisted signal must NOT need to edit this test."""
    current = _current_signal_names()
    assert current <= FROZEN_LEGACY_SIGNAL_ALLOWLIST, (
        current - FROZEN_LEGACY_SIGNAL_ALLOWLIST
    )


def test_a_hypothetical_new_signal_name_would_fail_the_subset_check():
    """Demonstrates the guard actually rejects growth: simulate current signals gaining one name
    not in the frozen set and confirm the subset relationship breaks."""
    hypothetical_current = _current_signal_names() | {"totally_new_thing_changed"}
    assert not (hypothetical_current <= FROZEN_LEGACY_SIGNAL_ALLOWLIST)


def test_tasks_changed_deletion_still_passes_the_subset_check():
    """No longer hypothetical as of P45B: `tasks_changed` is genuinely deleted (Task
    modernization's own producers/consumers both reached zero first) -- the subset
    relationship holds with it gone, proving field deletion never needs a frozen-allowlist edit."""
    assert "tasks_changed" not in _current_signal_names()
    assert _current_signal_names() <= FROZEN_LEGACY_SIGNAL_ALLOWLIST


# ---------------------------------------------------------------------------
# §34/P39: Finance module event modernization is complete -- permanent zero-legacy guard
# ---------------------------------------------------------------------------


def test_zero_finance_legacy_signal_fields_remain():
    current = _current_signal_names()
    reintroduced = current & _KNOWN_FINANCE_SIGNAL_NAMES
    assert reintroduced == set(), (
        f"Finance-owned legacy Signal field(s) reintroduced: {reintroduced}"
    )


def test_a_hypothetical_finance_signal_reintroduction_would_fail_the_zero_legacy_guard():
    """Demonstrates the guard actually rejects Finance-owned reintroduction, mirroring the
    subset-check's own hypothetical-growth proof above."""
    hypothetical_current = _current_signal_names() | {"budgets_changed"}
    reintroduced = hypothetical_current & _KNOWN_FINANCE_SIGNAL_NAMES
    assert reintroduced == {"budgets_changed"}


# ---------------------------------------------------------------------------
# P45B: Project Management module event modernization is complete -- permanent
# zero-legacy guard, independent of Auth's own AUDITED/DEFERRED status.
# ---------------------------------------------------------------------------

_KNOWN_PM_SIGNAL_NAMES = frozenset(
    {
        "tasks_changed",
        "project_changed",
        "timesheet_periods_changed",
        "collaboration_changed",
        "portfolio_changed",
        "register_changed",
    }
)


def test_zero_pm_legacy_signal_fields_remain():
    """Task was the last PM capability to reach zero legacy Signal involvement (P45B) --
    project_changed/timesheet_periods_changed/collaboration_changed/portfolio_changed/
    register_changed/tasks_changed were each already or are now confirmed absent. This guard
    is independent of Auth, which remains AUDITED/DEFERRED and is explicitly out of scope."""
    current = _current_signal_names()
    reintroduced = current & _KNOWN_PM_SIGNAL_NAMES
    assert reintroduced == set(), (
        f"PM-owned legacy Signal field(s) reintroduced: {reintroduced}"
    )
    assert current == {"auth_changed"}, (
        f"expected only auth_changed to remain, found: {current}"
    )


def test_a_hypothetical_pm_signal_reintroduction_would_fail_the_zero_legacy_guard():
    """Demonstrates the guard actually rejects PM-owned reintroduction, mirroring Finance's
    own hypothetical-growth proof above."""
    hypothetical_current = _current_signal_names() | {"tasks_changed"}
    reintroduced = hypothetical_current & _KNOWN_PM_SIGNAL_NAMES
    assert reintroduced == {"tasks_changed"}


# ---------------------------------------------------------------------------
# §7 / §20: no new legacy emitters -- every current producer site is pre-existing
# ---------------------------------------------------------------------------


def test_every_current_signal_is_in_the_frozen_allowlist_no_silent_field_addition():
    for name in _current_signal_names():
        assert name in FROZEN_LEGACY_SIGNAL_ALLOWLIST, (
            f"{name} is a new Signal field not in the frozen P8 allowlist"
        )


# ---------------------------------------------------------------------------
# §7 / §20: the deleted generic bridge stays deleted -- zero production references
# ---------------------------------------------------------------------------


def test_deleted_bridge_and_dead_signal_names_have_zero_production_references():
    import re

    pattern = re.compile(
        r"(?<![\w.])(" + "|".join(_DELETED_BRIDGE_NAMES) + r")\b"
    )
    hits = []
    for path in _production_source_files():
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = _strip_strings_and_comments(fh.read())
        if pattern.search(source):
            hits.append(path)
    assert hits == [], hits


def test_domain_events_module_has_no_bridge_machinery():
    import src.core.shared.events.domain_events as module

    assert not hasattr(module, "DomainChangeEvent")
    assert not hasattr(domain_events, "domain_changed")
    assert not hasattr(domain_events, "_BRIDGE_SPECS")
    assert not hasattr(domain_events, "_wire_bridges")
    assert not hasattr(domain_events, "_build_bridge")


def test_no_controller_base_has_the_generic_subscribe_domain_change_method():
    import src.ui_qml.modules.inventory_procurement.controllers.common.workspace_controller_base as inv_base
    import src.ui_qml.modules.project_management.controllers.common.workspace_controller_base as pm_base
    import src.ui_qml.platform.controllers.common.workspace_controller_base as platform_base

    for module, cls_name in (
        (platform_base, "PlatformWorkspaceControllerBase"),
        (pm_base, "ProjectManagementWorkspaceControllerBase"),
        (inv_base, "InventoryProcurementWorkspaceControllerBase"),
    ):
        cls = getattr(module, cls_name)
        assert not hasattr(cls, "_subscribe_domain_change")


def test_no_replacement_generic_router_or_registry_introduced():
    """A signal-name-string -> registry -> generic callback under any name would just rename the
    deleted `_BRIDGE_SPECS` mechanism."""
    forbidden_names = (
        "LegacySignalRouter",
        "DomainSignalRegistry",
        "EntityChangeRouter",
        "SignalDispatchMap",
        "CapabilitySignalRegistry",
        "AdapterRegistry",
    )
    hits = []
    for path in _production_source_files():
        normalized = path.replace("\\", "/")
        if normalized.endswith("test_p8_platform_event_architecture_canonicalization.py"):
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = _strip_strings_and_comments(fh.read())
        if any(name in source for name in forbidden_names):
            hits.append(path)
    assert hits == [], hits


def test_no_service_locator_pattern_reintroduced_in_composition_roots():
    for module_name in (
        "src.ui_qml.platform.context",
        "src.ui_qml.modules.project_management.context",
        "src.infra.composition.platform_registry",
    ):
        import importlib

        module = importlib.import_module(module_name)
        source = _strip_strings_and_comments(inspect.getsource(module))
        for forbidden in ("adapter_for(", "resolve_adapter(", "container.get(", "repository_for("):
            assert forbidden not in source, (module_name, forbidden)


# ---------------------------------------------------------------------------
# §23 / §9: five fully-modernized capability slices cannot regress to a legacy signal
# ---------------------------------------------------------------------------


def test_organization_create_path_has_zero_legacy_signal_involvement():
    import src.core.platform.application.master_data.org.organization_service as module

    source = _strip_strings_and_comments(
        inspect.getsource(module.OrganizationService.create_organization)
    )
    assert "organizations_changed" not in source
    assert "domain_events" not in source


def test_organization_has_no_legacy_signal_at_all():
    """P10D: create/profile-update/enable/disable are all typed events now -- the last legacy
    Organization Signal field is gone, not merely unused."""
    assert not hasattr(domain_events, "organizations_changed")


def test_module_entitlement_has_no_legacy_signal_at_all():
    assert not hasattr(domain_events, "modules_changed")


def test_role_binding_has_no_legacy_signal_at_all():
    assert not hasattr(domain_events, "access_changed")
    assert not hasattr(domain_events, "role_binding_changed")


def test_tenant_membership_service_never_imports_domain_events():
    import src.core.platform.application.tenant.tenancy.tenant_membership_service as module

    source = _strip_strings_and_comments(inspect.getsource(module))
    assert "domain_events" not in source


def test_approval_has_no_legacy_signal_at_all():
    assert not hasattr(domain_events, "approvals_changed")


def test_employee_has_no_legacy_signal_at_all():
    assert not hasattr(domain_events, "employees_changed")


def test_department_has_no_legacy_signal_at_all():
    assert not hasattr(domain_events, "departments_changed")


def test_site_has_no_legacy_signal_at_all():
    assert not hasattr(domain_events, "sites_changed")


def test_five_capability_mappers_never_import_domain_events_or_qt():
    mapper_modules = (
        "src.core.platform.application.master_data.org.event_handlers.view_invalidation",
        "src.core.platform.application.tenant.modules.event_handlers.view_invalidation",
        "src.core.platform.application.security.authorization.roles.event_handlers.view_invalidation",
        "src.core.platform.application.tenant.tenancy.event_handlers.view_invalidation",
        "src.core.platform.application.approval.event_handlers.view_invalidation",
    )
    import ast
    import importlib

    for module_name in mapper_modules:
        module = importlib.import_module(module_name)
        tree = ast.parse(inspect.getsource(module))
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)
        for forbidden in ("domain_events", "PySide6", "QtCore"):
            assert not any(forbidden in name for name in names), (module_name, names)


def test_five_capability_adapters_never_import_domain_event_vocabulary():
    adapter_modules = (
        "src.ui_qml.platform.adapters.organization_view_invalidation_adapter",
        "src.ui_qml.platform.adapters.module_entitlement_view_invalidation_adapter",
        "src.ui_qml.platform.adapters.role_binding_view_invalidation_adapter",
        "src.ui_qml.platform.adapters.tenant_membership_view_invalidation_adapter",
        "src.ui_qml.platform.adapters.approval_view_invalidation_adapter",
    )
    import importlib

    for module_name in adapter_modules:
        module = importlib.import_module(module_name)
        source = _strip_strings_and_comments(inspect.getsource(module))
        for forbidden in ("domain_events", "DomainEvent"):
            assert forbidden not in source, (module_name, forbidden)


# ---------------------------------------------------------------------------
# §26.1 / §24: DomainEvent / ViewInvalidationHint / IntegrationEventEnvelope stay distinct
# ---------------------------------------------------------------------------


def test_domain_event_is_a_protocol_not_related_to_integration_event_envelope():
    import typing

    from pydantic import BaseModel

    from src.core.shared.events.domain_event import DomainEvent
    from src.core.platform.integration.events import IntegrationEventEnvelope

    assert typing.get_origin(DomainEvent) is None
    assert typing.Protocol in DomainEvent.__mro__
    assert issubclass(IntegrationEventEnvelope, BaseModel)
    assert DomainEvent not in IntegrationEventEnvelope.__mro__
    assert BaseModel not in DomainEvent.__mro__


def test_view_invalidation_hint_is_a_plain_dataclass_not_a_domain_event_or_integration_event():
    import dataclasses as dc

    from src.core.shared.events.view_invalidation import ViewInvalidationHint
    from pydantic import BaseModel

    assert dc.is_dataclass(ViewInvalidationHint)
    assert not issubclass(ViewInvalidationHint, BaseModel)
    hint_fields = {f.name for f in dc.fields(ViewInvalidationHint)}
    assert hint_fields == {"scope", "category", "scope_code", "entity_type", "entity_id"}


def test_no_universal_event_base_class_was_introduced():
    hits = []
    for path in _production_source_files():
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = _strip_strings_and_comments(fh.read())
        for forbidden in ("class UniversalEvent", "class BaseEvent(", "class AnyEvent("):
            if forbidden in source:
                hits.append((path, forbidden))
    assert hits == [], hits


def test_notification_and_platform_event_remain_distinct_from_domain_event():
    """`Notification` (persisted, user-facing communication) and `PlatformEvent` (persisted
    governance/audit record) are each their own class, neither inherits from `DomainEvent`'s
    Protocol, and they are not the same class as each other -- never merged into one universal
    "event" type."""
    from src.core.shared.events.domain_event import DomainEvent
    from src.core.platform.domain.events.notifications.notification import Notification
    from src.core.platform.domain.events.platform_events.platform_event import PlatformEvent

    assert Notification is not PlatformEvent
    assert DomainEvent not in Notification.__mro__
    assert DomainEvent not in PlatformEvent.__mro__


# ---------------------------------------------------------------------------
# §21 / §26.3: layering -- Platform domain/application stay free of Qt/business infra
# ---------------------------------------------------------------------------


def test_platform_domain_event_modules_import_no_qt_or_sqlalchemy():
    event_domain_dirs = (
        "src/core/platform/domain/approval",
        "src/core/platform/domain/master_data/org",
        "src/core/platform/domain/security/authorization/roles",
        "src/core/platform/domain/tenant/modules",
        "src/core/platform/domain/tenant/tenancy",
    )
    hits = []
    for base in event_domain_dirs:
        for path in glob.glob(f"{base}/**/*.py", recursive=True):
            normalized = path.replace("\\", "/")
            if "__pycache__" in normalized:
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                source = _strip_strings_and_comments(fh.read())
            for forbidden in ("PySide6", "QtCore", "ui_qml", "sqlalchemy"):
                if forbidden in source:
                    hits.append((normalized, forbidden))
    assert hits == [], hits


def test_the_five_view_invalidation_mapper_modules_import_no_ui_qml():
    mapper_modules = (
        "src.core.platform.application.master_data.org.event_handlers.view_invalidation",
        "src.core.platform.application.tenant.modules.event_handlers.view_invalidation",
        "src.core.platform.application.security.authorization.roles.event_handlers.view_invalidation",
        "src.core.platform.application.tenant.tenancy.event_handlers.view_invalidation",
        "src.core.platform.application.approval.event_handlers.view_invalidation",
    )
    import importlib

    for module_name in mapper_modules:
        module = importlib.import_module(module_name)
        source = _strip_strings_and_comments(inspect.getsource(module))
        assert "ui_qml" not in source, module_name


# ---------------------------------------------------------------------------
# §16: no generic ViewInvalidation subscriber (wildcard replacement for the deleted bridge)
# ---------------------------------------------------------------------------


def test_no_adapter_subscribes_via_all_tenants_or_any_organization_in_tenant():
    adapter_modules = (
        "src.ui_qml.platform.adapters.organization_view_invalidation_adapter",
        "src.ui_qml.platform.adapters.module_entitlement_view_invalidation_adapter",
        "src.ui_qml.platform.adapters.role_binding_view_invalidation_adapter",
        "src.ui_qml.platform.adapters.tenant_membership_view_invalidation_adapter",
        "src.ui_qml.platform.adapters.approval_view_invalidation_adapter",
    )
    import importlib

    for module_name in adapter_modules:
        module = importlib.import_module(module_name)
        source = _strip_strings_and_comments(inspect.getsource(module))
        for forbidden in ("AllTenants", "AnyOrganizationInTenant"):
            assert forbidden not in source, (module_name, forbidden)


# ---------------------------------------------------------------------------
# §18: P6 helper unchanged in responsibility
# ---------------------------------------------------------------------------


def test_p6_helper_public_surface_unchanged():
    from src.ui_qml.shared.adapters.scoped_view_invalidation_subscription import (
        ScopedViewInvalidationSubscription,
    )

    replace_filter_params = set(
        inspect.signature(ScopedViewInvalidationSubscription.replace_filter).parameters
    )
    init_params = set(inspect.signature(ScopedViewInvalidationSubscription.__init__).parameters)
    dispose_params = set(inspect.signature(ScopedViewInvalidationSubscription.dispose).parameters)
    assert replace_filter_params == {"self", "filter"}
    assert init_params == {"self", "channel", "on_hint"}
    assert dispose_params == {"self"}


# ---------------------------------------------------------------------------
# §12: every remaining ApprovalPostCommitEvent resolves to an allowlisted, consumed signal
# ---------------------------------------------------------------------------


def test_zero_approval_post_commit_event_construction_sites_remain():
    """Superseded by P45B: Task was the last capability whose approval participant
    constructed `ApprovalPostCommitEvent(...)` -- zero production sites remain, so
    `ApprovalPostCommitEvent` itself is production-dead (retained only as an inert,
    unconstructed contract type pending a future cleanup pass)."""
    import ast

    signal_names_found = set()
    for path in _production_source_files():
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if "ApprovalPostCommitEvent(" not in source:
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "ApprovalPostCommitEvent"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                signal_names_found.add(node.args[0].value)

    assert signal_names_found == set()
