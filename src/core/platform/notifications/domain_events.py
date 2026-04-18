"""Domain event hub for shared masters, platform changes, and business-module notifications."""

from dataclasses import dataclass, field, fields
from typing import Callable

from src.core.platform.notifications.signal import Signal


@dataclass(frozen=True)
class DomainChangeEvent:
    category: str
    scope_code: str
    entity_type: str
    entity_id: str
    source_event: str


@dataclass
class DomainEvents:
    _BRIDGE_SPECS = (
        ("project_changed", "module", "project_management", "project", "project_changed"),
        ("tasks_changed", "module", "project_management", "project_tasks", "tasks_changed"),
        (
            "timesheet_periods_changed",
            "module",
            "project_management",
            "timesheet_period",
            "timesheet_periods_changed",
        ),
        ("costs_changed", "module", "project_management", "project_costs", "costs_changed"),
        ("resources_changed", "module", "project_management", "resource", "resources_changed"),
        ("baseline_changed", "module", "project_management", "project_baseline", "baseline_changed"),
        ("approvals_changed", "platform", "platform", "approval_request", "approvals_changed"),
        ("register_changed", "module", "project_management", "register_scope", "register_changed"),
        ("auth_changed", "platform", "platform", "user_account", "auth_changed"),
        ("employees_changed", "platform", "platform", "employee", "employees_changed"),
        ("organizations_changed", "shared_master", "platform", "organization", "organizations_changed"),
        ("sites_changed", "shared_master", "platform", "site", "sites_changed"),
        ("departments_changed", "shared_master", "platform", "department", "departments_changed"),
        ("documents_changed", "shared_master", "platform", "document", "documents_changed"),
        ("parties_changed", "shared_master", "platform", "party", "parties_changed"),
        ("access_changed", "platform", "platform", "project_access", "access_changed"),
        (
            "collaboration_changed",
            "module",
            "project_management",
            "task_collaboration",
            "collaboration_changed",
        ),
        ("portfolio_changed", "module", "project_management", "portfolio_entity", "portfolio_changed"),
        ("inventory_items_changed", "module", "inventory_procurement", "stock_item", "inventory_items_changed"),
        (
            "inventory_item_categories_changed",
            "module",
            "inventory_procurement",
            "inventory_item_category",
            "inventory_item_categories_changed",
        ),
        (
            "inventory_storerooms_changed",
            "module",
            "inventory_procurement",
            "storeroom",
            "inventory_storerooms_changed",
        ),
        (
            "inventory_balances_changed",
            "module",
            "inventory_procurement",
            "stock_balance",
            "inventory_balances_changed",
        ),
        (
            "inventory_reservations_changed",
            "module",
            "inventory_procurement",
            "stock_reservation",
            "inventory_reservations_changed",
        ),
        (
            "inventory_requisitions_changed",
            "module",
            "inventory_procurement",
            "purchase_requisition",
            "inventory_requisitions_changed",
        ),
        (
            "inventory_purchase_orders_changed",
            "module",
            "inventory_procurement",
            "purchase_order",
            "inventory_purchase_orders_changed",
        ),
        (
            "inventory_receipts_changed",
            "module",
            "inventory_procurement",
            "receipt_header",
            "inventory_receipts_changed",
        ),
        (
            "inventory_maintenance_materials_changed",
            "module",
            "inventory_procurement",
            "maintenance_material_contract",
            "inventory_maintenance_materials_changed",
        ),
        ("modules_changed", "platform", "platform", "module_runtime", "modules_changed"),
    )

    project_changed: Signal[str] = field(default_factory=Signal)
    tasks_changed: Signal[str] = field(default_factory=Signal)
    timesheet_periods_changed: Signal[str] = field(default_factory=Signal)
    costs_changed: Signal[str] = field(default_factory=Signal)
    resources_changed: Signal[str] = field(default_factory=Signal)
    baseline_changed: Signal[str] = field(default_factory=Signal)
    approvals_changed: Signal[str] = field(default_factory=Signal)
    register_changed: Signal[str] = field(default_factory=Signal)
    auth_changed: Signal[str] = field(default_factory=Signal)
    employees_changed: Signal[str] = field(default_factory=Signal)
    organizations_changed: Signal[str] = field(default_factory=Signal)
    sites_changed: Signal[str] = field(default_factory=Signal)
    departments_changed: Signal[str] = field(default_factory=Signal)
    documents_changed: Signal[str] = field(default_factory=Signal)
    parties_changed: Signal[str] = field(default_factory=Signal)
    access_changed: Signal[str] = field(default_factory=Signal)
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
    inventory_maintenance_materials_changed: Signal[str] = field(default_factory=Signal)
    modules_changed: Signal[str] = field(default_factory=Signal)
    shared_master_changed: Signal[DomainChangeEvent] = field(default_factory=Signal)
    domain_changed: Signal[DomainChangeEvent] = field(default_factory=Signal)

    def __post_init__(self) -> None:
        self._wire_bridges()

    def reset(self) -> None:
        for signal_field in fields(self):
            signal = getattr(self, signal_field.name)
            if isinstance(signal, Signal):
                signal.clear()
        self._wire_bridges()

    def _wire_bridges(self) -> None:
        for signal_name, category, scope_code, entity_type, source_event in self._BRIDGE_SPECS:
            signal: Signal[str] = getattr(self, signal_name)
            signal.connect(
                self._build_bridge(
                    category=category,
                    scope_code=scope_code,
                    entity_type=entity_type,
                    source_event=source_event,
                )
            )

    def _build_bridge(
        self,
        *,
        category: str,
        scope_code: str,
        entity_type: str,
        source_event: str,
    ) -> Callable[[str], None]:
        def _bridge(entity_id: str) -> None:
            event = DomainChangeEvent(
                category=category,
                scope_code=scope_code,
                entity_type=entity_type,
                entity_id=entity_id,
                source_event=source_event,
            )
            if category == "shared_master":
                self.shared_master_changed.emit(event)
            self.domain_changed.emit(event)

        return _bridge


domain_events = DomainEvents()


__all__ = [
    "DomainChangeEvent",
    "DomainEvents",
    "domain_events",
]
