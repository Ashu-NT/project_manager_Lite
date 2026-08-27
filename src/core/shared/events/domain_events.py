"""P7C: `cost_entries_changed`/`commitments_changed`/`forecasts_changed`/
`financial_changes_changed` were deleted -- a repo-wide audit (direct `.emit(` call sites AND
`ApprovalPostCommitEvent`-driven reflective emission) found real production producers for all
four, but zero production consumers of any kind (no `.connect(`/`_subscribe_domain_signal(...)`
anywhere) -- a confirmed emit-into-the-void path. Every remaining `Signal` field below has both a
real producer and a real consumer."""

from dataclasses import dataclass, field, fields

from src.core.shared.events.signal import Signal


@dataclass
class DomainEvents:
    project_changed: Signal[str] = field(default_factory=Signal)
    tasks_changed: Signal[str] = field(default_factory=Signal)
    timesheet_periods_changed: Signal[str] = field(default_factory=Signal)
    resources_changed: Signal[str] = field(default_factory=Signal)
    baseline_changed: Signal[str] = field(default_factory=Signal)
    budgets_changed: Signal[str] = field(default_factory=Signal)
    billing_preparations_changed: Signal[str] = field(default_factory=Signal)
    planned_costs_changed: Signal[str] = field(default_factory=Signal)
    register_changed: Signal[str] = field(default_factory=Signal)
    auth_changed: Signal[str] = field(default_factory=Signal)
    sites_changed: Signal[str] = field(default_factory=Signal)
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
