"""Domain event hub for shared masters, platform changes, and business-module notifications.

P7A: the generic legacy-compatibility bridge (`_BRIDGE_SPECS`/`_wire_bridges`/`domain_changed`/
`DomainChangeEvent`) has been fully removed -- pre-release, no compatibility scaffolding is kept
for it. Every still-unmodernized capability's own specific `Signal` field below is subscribed to
directly by its real consumer(s); none of them are routed through a generic entity_type/scope_code
dispatch table."""

from dataclasses import dataclass, field, fields

from src.core.shared.events.signal import Signal


@dataclass
class DomainEvents:
    project_changed: Signal[str] = field(default_factory=Signal)
    tasks_changed: Signal[str] = field(default_factory=Signal)
    timesheet_periods_changed: Signal[str] = field(default_factory=Signal)
    costs_changed: Signal[str] = field(default_factory=Signal)
    cost_entries_changed: Signal[str] = field(default_factory=Signal)
    commitments_changed: Signal[str] = field(default_factory=Signal)
    resources_changed: Signal[str] = field(default_factory=Signal)
    baseline_changed: Signal[str] = field(default_factory=Signal)
    budgets_changed: Signal[str] = field(default_factory=Signal)
    forecasts_changed: Signal[str] = field(default_factory=Signal)
    financial_changes_changed: Signal[str] = field(default_factory=Signal)
    billing_preparations_changed: Signal[str] = field(default_factory=Signal)
    planned_costs_changed: Signal[str] = field(default_factory=Signal)
    register_changed: Signal[str] = field(default_factory=Signal)
    auth_changed: Signal[str] = field(default_factory=Signal)
    employees_changed: Signal[str] = field(default_factory=Signal)
    organizations_changed: Signal[str] = field(default_factory=Signal)
    sites_changed: Signal[str] = field(default_factory=Signal)
    departments_changed: Signal[str] = field(default_factory=Signal)
    calendars_changed: Signal[str] = field(default_factory=Signal)
    documents_changed: Signal[str] = field(default_factory=Signal)
    parties_changed: Signal[str] = field(default_factory=Signal)
    collaboration_changed: Signal[str] = field(default_factory=Signal)
    portfolio_changed: Signal[str] = field(default_factory=Signal)
    inventory_items_changed: Signal[str] = field(default_factory=Signal)
    inventory_item_categories_changed: Signal[str] = field(default_factory=Signal)
    inventory_storerooms_changed: Signal[str] = field(default_factory=Signal)
    inventory_balances_changed: Signal[str] = field(default_factory=Signal)
    inventory_reservations_changed: Signal[str] = field(default_factory=Signal)
    inventory_requisitions_changed: Signal[str] = field(default_factory=Signal)
    inventory_purchase_orders_changed: Signal[str] = field(default_factory=Signal)
    inventory_receipts_changed: Signal[str] = field(default_factory=Signal)
    inventory_locations_changed: Signal[str] = field(default_factory=Signal)
    inventory_reorder_policies_changed: Signal[str] = field(default_factory=Signal)
    inventory_cycle_counts_changed: Signal[str] = field(default_factory=Signal)

    def reset(self) -> None:
        for signal_field in fields(self):
            signal = getattr(self, signal_field.name)
            if isinstance(signal, Signal):
                signal.clear()


domain_events = DomainEvents()


__all__ = [
    "DomainEvents",
    "domain_events",
]
