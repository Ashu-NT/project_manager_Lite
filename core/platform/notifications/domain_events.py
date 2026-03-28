"""Domain event hub for shared masters, platform changes, and business-module notifications."""

from dataclasses import dataclass, field, fields
from typing import Callable
from .signal import Signal


@dataclass(frozen=True)
class DomainChangeEvent:
    category: str
    scope_code: str
    entity_type: str
    entity_id: str
    source_event: str


@dataclass
class DomainEvents:

    _BRIDGE_SPECS  = (
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
        (
            "approvals_changed",
            "platform",
            "platform",
            "approval_request",
            "approvals_changed",
        ),
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
        ("modules_changed", "platform", "platform", "module_runtime", "modules_changed"),
    )    
    
    project_changed: Signal[str] = field(default_factory=Signal)   # project_id
    tasks_changed: Signal[str] = field(default_factory=Signal)     # project_id
    timesheet_periods_changed: Signal[str] = field(default_factory=Signal)  # period_id
    costs_changed: Signal[str] = field(default_factory=Signal)     # project_id
    resources_changed: Signal[str] = field(default_factory=Signal)  # resource_id
    baseline_changed: Signal[str] = field(default_factory=Signal)  # project_id
    approvals_changed: Signal[str] = field(default_factory=Signal)  # approval_request_id
    register_changed: Signal[str] = field(default_factory=Signal)  # project_id
    auth_changed: Signal[str] = field(default_factory=Signal)  # user_id
    employees_changed: Signal[str] = field(default_factory=Signal)  # employee_id
    organizations_changed: Signal[str] = field(default_factory=Signal)  # organization_id
    sites_changed: Signal[str] = field(default_factory=Signal)  # site_id
    departments_changed: Signal[str] = field(default_factory=Signal)  # department_id
    documents_changed: Signal[str] = field(default_factory=Signal)  # document_id
    parties_changed: Signal[str] = field(default_factory=Signal)  # party_id
    access_changed: Signal[str] = field(default_factory=Signal)  # project_id
    collaboration_changed: Signal[str] = field(default_factory=Signal)  # task_id
    portfolio_changed: Signal[str] = field(default_factory=Signal)  # entity_id
    inventory_items_changed: Signal[str] = field(default_factory=Signal)  # item_id
    inventory_item_categories_changed: Signal[str] = field(default_factory=Signal)  # category_id
    inventory_storerooms_changed: Signal[str] = field(default_factory=Signal)  # storeroom_id
    inventory_balances_changed: Signal[str] = field(default_factory=Signal)  # balance_id
    inventory_reservations_changed: Signal[str] = field(default_factory=Signal)  # reservation_id
    inventory_requisitions_changed: Signal[str] = field(default_factory=Signal)  # requisition_id
    inventory_purchase_orders_changed: Signal[str] = field(default_factory=Signal)  # po_id
    inventory_receipts_changed: Signal[str] = field(default_factory=Signal)  # receipt_id
    modules_changed: Signal[str] = field(default_factory=Signal)  # module_code
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
            signal:Signal = getattr(self, signal_name)
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


# SINGLE global instance
domain_events = DomainEvents()
