"""Process-local mutation hints consumed by current desktop workspace controllers.

Finance mutation families use targeted project/organization payloads and have both production
producers and the Finance destination-cache consumer. These hints never replace domain truth;
they only mark authoritative read projections stale after a successful commit.
"""

from dataclasses import dataclass, field, fields

from src.core.shared.events.signal import Signal


@dataclass
class DomainEvents:
    project_changed: Signal[str] = field(default_factory=Signal)
    tasks_changed: Signal[str] = field(default_factory=Signal)
    timesheet_periods_changed: Signal[str] = field(default_factory=Signal)
    baseline_changed: Signal[str] = field(default_factory=Signal)
    budgets_changed: Signal[str] = field(default_factory=Signal)
    billing_preparations_changed: Signal[str] = field(default_factory=Signal)
    planned_costs_changed: Signal[str] = field(default_factory=Signal)
    forecasts_changed: Signal[object] = field(default_factory=Signal)
    cost_entries_changed: Signal[object] = field(default_factory=Signal)
    commitments_changed: Signal[object] = field(default_factory=Signal)
    rates_changed: Signal[object] = field(default_factory=Signal)
    financial_changes_changed: Signal[object] = field(default_factory=Signal)
    financial_setup_changed: Signal[object] = field(default_factory=Signal)
    register_changed: Signal[str] = field(default_factory=Signal)
    auth_changed: Signal[str] = field(default_factory=Signal)
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
