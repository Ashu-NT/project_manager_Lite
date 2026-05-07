from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.core.modules.inventory_procurement.application.catalog import ItemMasterService
from src.core.modules.inventory_procurement.application.common.reference_service import (
    InventoryReferenceService,
)
from src.core.modules.inventory_procurement.application.common.support import (
    STOREROOM_STATUS_TRANSITIONS,
)
from src.core.modules.inventory_procurement.application.inventory import (
    InventoryService,
    StockControlService,
)
from src.core.modules.inventory_procurement.api.desktop._support import (
    clean_text,
    format_amount,
    format_bool_label,
    format_date,
    format_datetime,
    format_enum_label,
    format_quantity,
)
from src.core.modules.inventory_procurement.domain.inventory.stock import StockTransactionType


@dataclass(frozen=True)
class InventorySiteOptionDescriptor:
    value: str
    label: str
    currency_code: str
    is_active: bool


@dataclass(frozen=True)
class InventoryCatalogItemOptionDescriptor:
    value: str
    label: str
    stock_uom: str
    category_code: str
    is_active: bool


@dataclass(frozen=True)
class InventoryStoreroomOptionDescriptor:
    value: str
    label: str
    site_id: str
    site_label: str
    is_active: bool


@dataclass(frozen=True)
class InventoryStoreroomStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class InventoryTransactionTypeDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class InventoryStoreroomDesktopDto:
    id: str
    storeroom_code: str
    name: str
    description: str
    site_id: str
    site_label: str
    status: str
    status_label: str
    storeroom_type: str
    is_active: bool
    active_label: str
    is_internal_supplier: bool
    allows_issue: bool
    allows_transfer: bool
    allows_receiving: bool
    requires_reservation_for_issue: bool
    requires_supplier_reference_for_receipt: bool
    default_currency_code: str
    manager_party_id: str | None
    manager_party_label: str
    notes: str
    version: int


@dataclass(frozen=True)
class InventoryStockBalanceDesktopDto:
    id: str
    stock_item_id: str
    stock_item_label: str
    storeroom_id: str
    storeroom_label: str
    uom: str
    on_hand_qty: float
    on_hand_qty_label: str
    reserved_qty: float
    reserved_qty_label: str
    available_qty: float
    available_qty_label: str
    on_order_qty: float
    on_order_qty_label: str
    committed_qty: float
    committed_qty_label: str
    average_cost: float
    average_cost_label: str
    last_receipt_at_label: str
    last_issue_at_label: str
    reorder_required: bool
    version: int


@dataclass(frozen=True)
class InventoryStockTransactionDesktopDto:
    id: str
    transaction_number: str
    stock_item_id: str
    stock_item_label: str
    storeroom_id: str
    storeroom_label: str
    transaction_type: str
    transaction_type_label: str
    quantity: float
    quantity_label: str
    uom: str
    unit_cost: float
    unit_cost_label: str
    transaction_at_label: str
    reference_type: str
    reference_id: str
    performed_by_username: str
    resulting_on_hand_qty_label: str
    resulting_available_qty_label: str
    notes: str


@dataclass(frozen=True)
class InventoryStoreroomCreateCommand:
    storeroom_code: str
    name: str
    site_id: str
    description: str = ""
    status: str = "DRAFT"
    storeroom_type: str = ""
    is_internal_supplier: bool = False
    allows_issue: bool = True
    allows_transfer: bool = True
    allows_receiving: bool = True
    requires_reservation_for_issue: bool = False
    requires_supplier_reference_for_receipt: bool = False
    default_currency_code: str | None = None
    manager_party_id: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class InventoryStoreroomUpdateCommand:
    storeroom_id: str
    storeroom_code: str
    name: str
    site_id: str
    description: str = ""
    status: str = "DRAFT"
    storeroom_type: str = ""
    is_internal_supplier: bool = False
    allows_issue: bool = True
    allows_transfer: bool = True
    allows_receiving: bool = True
    requires_reservation_for_issue: bool = False
    requires_supplier_reference_for_receipt: bool = False
    default_currency_code: str | None = None
    manager_party_id: str | None = None
    notes: str = ""
    expected_version: int | None = None


@dataclass(frozen=True)
class InventoryOpeningBalanceCommand:
    stock_item_id: str
    storeroom_id: str
    quantity: float
    uom: str | None = None
    unit_cost: float = 0.0
    transaction_at: datetime | None = None
    notes: str = ""


@dataclass(frozen=True)
class InventoryAdjustmentCommand:
    stock_item_id: str
    storeroom_id: str
    quantity: float
    direction: str
    uom: str | None = None
    unit_cost: float = 0.0
    transaction_at: datetime | None = None
    reference_type: str = "adjustment"
    reference_id: str = ""
    notes: str = ""


@dataclass(frozen=True)
class InventoryIssueCommand:
    stock_item_id: str
    storeroom_id: str
    quantity: float
    uom: str | None = None
    unit_cost: float | None = None
    transaction_at: datetime | None = None
    release_reserved_qty: float = 0.0
    reference_type: str = "issue"
    reference_id: str = ""
    notes: str = ""


@dataclass(frozen=True)
class InventoryReturnCommand:
    stock_item_id: str
    storeroom_id: str
    quantity: float
    uom: str | None = None
    unit_cost: float | None = None
    transaction_at: datetime | None = None
    reference_type: str = "return"
    reference_id: str = ""
    notes: str = ""


@dataclass(frozen=True)
class InventoryTransferCommand:
    stock_item_id: str
    source_storeroom_id: str
    destination_storeroom_id: str
    quantity: float
    uom: str | None = None
    transaction_at: datetime | None = None
    notes: str = ""


class InventoryProcurementInventoryDesktopApi:
    def __init__(
        self,
        *,
        inventory_service: InventoryService | None = None,
        stock_service: StockControlService | None = None,
        item_service: ItemMasterService | None = None,
        reference_service: InventoryReferenceService | None = None,
    ) -> None:
        self._inventory_service = inventory_service
        self._stock_service = stock_service
        self._item_service = item_service
        self._reference_service = reference_service

    def list_storeroom_statuses(self) -> tuple[InventoryStoreroomStatusDescriptor, ...]:
        return tuple(
            InventoryStoreroomStatusDescriptor(
                value=value,
                label=format_enum_label(value),
            )
            for value in STOREROOM_STATUS_TRANSITIONS
        )

    def list_transaction_types(self) -> tuple[InventoryTransactionTypeDescriptor, ...]:
        return tuple(
            InventoryTransactionTypeDescriptor(
                value=entry.value,
                label=format_enum_label(entry.value),
            )
            for entry in StockTransactionType
        )

    def list_sites(
        self,
        *,
        active_only: bool | None = True,
    ) -> tuple[InventorySiteOptionDescriptor, ...]:
        if self._reference_service is None:
            return ()
        sites = sorted(
            self._reference_service.list_sites(active_only=active_only),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "site_code", "") or "").casefold(),
            ),
        )
        return tuple(_serialize_site(row) for row in sites)

    def list_items(
        self,
        *,
        active_only: bool | None = True,
    ) -> tuple[InventoryCatalogItemOptionDescriptor, ...]:
        if self._item_service is None:
            return ()
        items = sorted(
            self._item_service.list_items(active_only=active_only),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "item_code", "") or "").casefold(),
            ),
        )
        return tuple(_serialize_item_option(row) for row in items)

    def list_storeroom_options(
        self,
        *,
        active_only: bool | None = True,
        site_id: str | None = None,
    ) -> tuple[InventoryStoreroomOptionDescriptor, ...]:
        if self._inventory_service is None:
            return ()
        site_lookup = {row.value: row.label for row in self.list_sites(active_only=None)}
        rows = self._inventory_service.list_storerooms(active_only=active_only, site_id=site_id)
        ordered = sorted(
            rows,
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "storeroom_code", "") or "").casefold(),
            ),
        )
        return tuple(_serialize_storeroom_option(row, site_lookup=site_lookup) for row in ordered)

    def list_storerooms(
        self,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        search_text: str = "",
    ) -> tuple[InventoryStoreroomDesktopDto, ...]:
        if self._inventory_service is None:
            return ()
        site_lookup = {row.value: row.label for row in self.list_sites(active_only=None)}
        party_lookup = self._party_lookup()
        if search_text:
            rows = self._inventory_service.search_storerooms(
                search_text=search_text,
                active_only=active_only,
                site_id=site_id,
            )
        else:
            rows = self._inventory_service.list_storerooms(
                active_only=active_only,
                site_id=site_id,
            )
        ordered = sorted(
            rows,
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "storeroom_code", "") or "").casefold(),
            ),
        )
        return tuple(
            _serialize_storeroom(
                row,
                site_lookup=site_lookup,
                party_lookup=party_lookup,
            )
            for row in ordered
        )

    def list_balances(
        self,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
    ) -> tuple[InventoryStockBalanceDesktopDto, ...]:
        if self._stock_service is None:
            return ()
        item_lookup = {row.value: row.label for row in self.list_items(active_only=None)}
        storeroom_lookup = {
            row.value: row.label
            for row in self.list_storeroom_options(active_only=None)
        }
        rows = sorted(
            self._stock_service.list_balances(
                stock_item_id=stock_item_id,
                storeroom_id=storeroom_id,
            ),
            key=lambda row: (
                not bool(getattr(row, "reorder_required", False)),
                str(getattr(row, "storeroom_id", "") or "").casefold(),
                str(getattr(row, "stock_item_id", "") or "").casefold(),
            ),
        )
        return tuple(
            _serialize_balance(
                row,
                item_lookup=item_lookup,
                storeroom_lookup=storeroom_lookup,
            )
            for row in rows
        )

    def list_transactions(
        self,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
        limit: int = 200,
    ) -> tuple[InventoryStockTransactionDesktopDto, ...]:
        if self._stock_service is None:
            return ()
        item_lookup = {row.value: row.label for row in self.list_items(active_only=None)}
        storeroom_lookup = {
            row.value: row.label
            for row in self.list_storeroom_options(active_only=None)
        }
        rows = self._stock_service.list_transactions(
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            limit=limit,
        )
        return tuple(
            _serialize_transaction(
                row,
                item_lookup=item_lookup,
                storeroom_lookup=storeroom_lookup,
            )
            for row in rows
        )

    def create_storeroom(
        self,
        command: InventoryStoreroomCreateCommand,
    ) -> InventoryStoreroomDesktopDto:
        service = self._require_inventory_service()
        storeroom = service.create_storeroom(
            storeroom_code=command.storeroom_code,
            name=command.name,
            site_id=command.site_id,
            description=command.description,
            status=command.status,
            storeroom_type=command.storeroom_type,
            is_internal_supplier=command.is_internal_supplier,
            allows_issue=command.allows_issue,
            allows_transfer=command.allows_transfer,
            allows_receiving=command.allows_receiving,
            requires_reservation_for_issue=command.requires_reservation_for_issue,
            requires_supplier_reference_for_receipt=command.requires_supplier_reference_for_receipt,
            default_currency_code=command.default_currency_code,
            manager_party_id=command.manager_party_id,
            notes=command.notes,
        )
        return self._serialize_storeroom(storeroom)

    def update_storeroom(
        self,
        command: InventoryStoreroomUpdateCommand,
    ) -> InventoryStoreroomDesktopDto:
        service = self._require_inventory_service()
        storeroom = service.update_storeroom(
            command.storeroom_id,
            storeroom_code=command.storeroom_code,
            name=command.name,
            site_id=command.site_id,
            description=command.description,
            status=command.status,
            storeroom_type=command.storeroom_type,
            is_internal_supplier=command.is_internal_supplier,
            allows_issue=command.allows_issue,
            allows_transfer=command.allows_transfer,
            allows_receiving=command.allows_receiving,
            requires_reservation_for_issue=command.requires_reservation_for_issue,
            requires_supplier_reference_for_receipt=command.requires_supplier_reference_for_receipt,
            default_currency_code=command.default_currency_code,
            manager_party_id=command.manager_party_id,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return self._serialize_storeroom(storeroom)

    def toggle_storeroom_active(
        self,
        storeroom_id: str,
        *,
        expected_version: int | None = None,
    ) -> InventoryStoreroomDesktopDto:
        service = self._require_inventory_service()
        storeroom = service.get_storeroom(storeroom_id)
        updated = service.update_storeroom(
            storeroom_id,
            is_active=not bool(getattr(storeroom, "is_active", True)),
            expected_version=expected_version,
        )
        return self._serialize_storeroom(updated)

    def post_opening_balance(
        self,
        command: InventoryOpeningBalanceCommand,
    ) -> InventoryStockTransactionDesktopDto:
        service = self._require_stock_service()
        transaction = service.post_opening_balance(
            stock_item_id=command.stock_item_id,
            storeroom_id=command.storeroom_id,
            quantity=command.quantity,
            uom=command.uom,
            unit_cost=command.unit_cost,
            transaction_at=command.transaction_at,
            notes=command.notes,
        )
        return self._serialize_transaction(transaction)

    def post_adjustment(
        self,
        command: InventoryAdjustmentCommand,
    ) -> InventoryStockTransactionDesktopDto:
        service = self._require_stock_service()
        transaction = service.post_adjustment(
            stock_item_id=command.stock_item_id,
            storeroom_id=command.storeroom_id,
            quantity=command.quantity,
            direction=command.direction,
            uom=command.uom,
            unit_cost=command.unit_cost,
            transaction_at=command.transaction_at,
            reference_type=command.reference_type,
            reference_id=command.reference_id,
            notes=command.notes,
        )
        return self._serialize_transaction(transaction)

    def issue_stock(
        self,
        command: InventoryIssueCommand,
    ) -> InventoryStockTransactionDesktopDto:
        service = self._require_stock_service()
        transaction = service.issue_stock(
            stock_item_id=command.stock_item_id,
            storeroom_id=command.storeroom_id,
            quantity=command.quantity,
            uom=command.uom,
            unit_cost=command.unit_cost,
            transaction_at=command.transaction_at,
            release_reserved_qty=command.release_reserved_qty,
            reference_type=command.reference_type,
            reference_id=command.reference_id,
            notes=command.notes,
        )
        return self._serialize_transaction(transaction)

    def return_stock(
        self,
        command: InventoryReturnCommand,
    ) -> InventoryStockTransactionDesktopDto:
        service = self._require_stock_service()
        transaction = service.return_stock(
            stock_item_id=command.stock_item_id,
            storeroom_id=command.storeroom_id,
            quantity=command.quantity,
            uom=command.uom,
            unit_cost=command.unit_cost,
            transaction_at=command.transaction_at,
            reference_type=command.reference_type,
            reference_id=command.reference_id,
            notes=command.notes,
        )
        return self._serialize_transaction(transaction)

    def transfer_stock(
        self,
        command: InventoryTransferCommand,
    ) -> tuple[InventoryStockTransactionDesktopDto, InventoryStockTransactionDesktopDto]:
        service = self._require_stock_service()
        outbound, inbound = service.transfer_stock(
            stock_item_id=command.stock_item_id,
            source_storeroom_id=command.source_storeroom_id,
            destination_storeroom_id=command.destination_storeroom_id,
            quantity=command.quantity,
            uom=command.uom,
            transaction_at=command.transaction_at,
            notes=command.notes,
        )
        return (
            self._serialize_transaction(outbound),
            self._serialize_transaction(inbound),
        )

    def _party_lookup(self) -> dict[str, str]:
        if self._reference_service is None:
            return {}
        return {
            row.id: " - ".join(
                part
                for part in (
                    clean_text(getattr(row, "party_code", "")),
                    clean_text(getattr(row, "party_name", "")),
                )
                if part
            )
            for row in self._reference_service.list_business_parties(active_only=None)
        }

    def _serialize_storeroom(self, row) -> InventoryStoreroomDesktopDto:
        site_lookup = {entry.value: entry.label for entry in self.list_sites(active_only=None)}
        return _serialize_storeroom(
            row,
            site_lookup=site_lookup,
            party_lookup=self._party_lookup(),
        )

    def _serialize_transaction(self, row) -> InventoryStockTransactionDesktopDto:
        item_lookup = {entry.value: entry.label for entry in self.list_items(active_only=None)}
        storeroom_lookup = {
            entry.value: entry.label
            for entry in self.list_storeroom_options(active_only=None)
        }
        return _serialize_transaction(
            row,
            item_lookup=item_lookup,
            storeroom_lookup=storeroom_lookup,
        )

    def _require_inventory_service(self) -> InventoryService:
        if self._inventory_service is None:
            raise RuntimeError("Inventory storeroom desktop API is not connected.")
        return self._inventory_service

    def _require_stock_service(self) -> StockControlService:
        if self._stock_service is None:
            raise RuntimeError("Inventory stock desktop API is not connected.")
        return self._stock_service


def build_inventory_procurement_inventory_desktop_api(
    *,
    inventory_service: InventoryService | None = None,
    stock_service: StockControlService | None = None,
    item_service: ItemMasterService | None = None,
    reference_service: InventoryReferenceService | None = None,
) -> InventoryProcurementInventoryDesktopApi:
    return InventoryProcurementInventoryDesktopApi(
        inventory_service=inventory_service,
        stock_service=stock_service,
        item_service=item_service,
        reference_service=reference_service,
    )


def _serialize_site(row) -> InventorySiteOptionDescriptor:
    code = clean_text(getattr(row, "site_code", ""))
    name = clean_text(getattr(row, "name", ""))
    return InventorySiteOptionDescriptor(
        value=row.id,
        label=f"{code} - {name}" if code else name,
        currency_code=clean_text(getattr(row, "currency_code", "")),
        is_active=bool(getattr(row, "is_active", True)),
    )


def _serialize_item_option(row) -> InventoryCatalogItemOptionDescriptor:
    code = clean_text(getattr(row, "item_code", ""))
    name = clean_text(getattr(row, "name", ""))
    return InventoryCatalogItemOptionDescriptor(
        value=row.id,
        label=f"{code} - {name}" if code else name,
        stock_uom=clean_text(getattr(row, "stock_uom", "")),
        category_code=clean_text(getattr(row, "category_code", "")),
        is_active=bool(getattr(row, "is_active", True)),
    )


def _serialize_storeroom_option(
    row,
    *,
    site_lookup: dict[str, str],
) -> InventoryStoreroomOptionDescriptor:
    code = clean_text(getattr(row, "storeroom_code", ""))
    name = clean_text(getattr(row, "name", ""))
    site_id = clean_text(getattr(row, "site_id", ""))
    return InventoryStoreroomOptionDescriptor(
        value=row.id,
        label=f"{code} - {name}" if code else name,
        site_id=site_id,
        site_label=site_lookup.get(site_id, "-"),
        is_active=bool(getattr(row, "is_active", True)),
    )


def _serialize_storeroom(
    row,
    *,
    site_lookup: dict[str, str],
    party_lookup: dict[str, str],
) -> InventoryStoreroomDesktopDto:
    status = clean_text(getattr(row, "status", ""))
    site_id = clean_text(getattr(row, "site_id", ""))
    manager_party_id = clean_text(getattr(row, "manager_party_id", "")) or None
    is_active = bool(getattr(row, "is_active", False))
    return InventoryStoreroomDesktopDto(
        id=row.id,
        storeroom_code=clean_text(getattr(row, "storeroom_code", "")),
        name=clean_text(getattr(row, "name", "")),
        description=clean_text(getattr(row, "description", "")),
        site_id=site_id,
        site_label=site_lookup.get(site_id, "-"),
        status=status,
        status_label=format_enum_label(status),
        storeroom_type=clean_text(getattr(row, "storeroom_type", "")),
        is_active=is_active,
        active_label=format_bool_label(is_active),
        is_internal_supplier=bool(getattr(row, "is_internal_supplier", False)),
        allows_issue=bool(getattr(row, "allows_issue", True)),
        allows_transfer=bool(getattr(row, "allows_transfer", True)),
        allows_receiving=bool(getattr(row, "allows_receiving", True)),
        requires_reservation_for_issue=bool(getattr(row, "requires_reservation_for_issue", False)),
        requires_supplier_reference_for_receipt=bool(
            getattr(row, "requires_supplier_reference_for_receipt", False)
        ),
        default_currency_code=clean_text(getattr(row, "default_currency_code", "")),
        manager_party_id=manager_party_id,
        manager_party_label=party_lookup.get(manager_party_id or "", "-"),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 1) or 1),
    )


def _serialize_balance(
    row,
    *,
    item_lookup: dict[str, str],
    storeroom_lookup: dict[str, str],
) -> InventoryStockBalanceDesktopDto:
    average_cost = float(getattr(row, "average_cost", 0.0) or 0.0)
    return InventoryStockBalanceDesktopDto(
        id=row.id,
        stock_item_id=clean_text(getattr(row, "stock_item_id", "")),
        stock_item_label=item_lookup.get(clean_text(getattr(row, "stock_item_id", "")), "-"),
        storeroom_id=clean_text(getattr(row, "storeroom_id", "")),
        storeroom_label=storeroom_lookup.get(clean_text(getattr(row, "storeroom_id", "")), "-"),
        uom=clean_text(getattr(row, "uom", "")),
        on_hand_qty=float(getattr(row, "on_hand_qty", 0.0) or 0.0),
        on_hand_qty_label=format_quantity(getattr(row, "on_hand_qty", 0.0)),
        reserved_qty=float(getattr(row, "reserved_qty", 0.0) or 0.0),
        reserved_qty_label=format_quantity(getattr(row, "reserved_qty", 0.0)),
        available_qty=float(getattr(row, "available_qty", 0.0) or 0.0),
        available_qty_label=format_quantity(getattr(row, "available_qty", 0.0)),
        on_order_qty=float(getattr(row, "on_order_qty", 0.0) or 0.0),
        on_order_qty_label=format_quantity(getattr(row, "on_order_qty", 0.0)),
        committed_qty=float(getattr(row, "committed_qty", 0.0) or 0.0),
        committed_qty_label=format_quantity(getattr(row, "committed_qty", 0.0)),
        average_cost=average_cost,
        average_cost_label=format_amount(average_cost),
        last_receipt_at_label=format_datetime(getattr(row, "last_receipt_at", None)),
        last_issue_at_label=format_datetime(getattr(row, "last_issue_at", None)),
        reorder_required=bool(getattr(row, "reorder_required", False)),
        version=int(getattr(row, "version", 1) or 1),
    )


def _serialize_transaction(
    row,
    *,
    item_lookup: dict[str, str],
    storeroom_lookup: dict[str, str],
) -> InventoryStockTransactionDesktopDto:
    transaction_type = getattr(getattr(row, "transaction_type", None), "value", getattr(row, "transaction_type", ""))
    return InventoryStockTransactionDesktopDto(
        id=row.id,
        transaction_number=clean_text(getattr(row, "transaction_number", "")),
        stock_item_id=clean_text(getattr(row, "stock_item_id", "")),
        stock_item_label=item_lookup.get(clean_text(getattr(row, "stock_item_id", "")), "-"),
        storeroom_id=clean_text(getattr(row, "storeroom_id", "")),
        storeroom_label=storeroom_lookup.get(clean_text(getattr(row, "storeroom_id", "")), "-"),
        transaction_type=str(transaction_type or ""),
        transaction_type_label=format_enum_label(str(transaction_type or "")),
        quantity=float(getattr(row, "quantity", 0.0) or 0.0),
        quantity_label=format_quantity(getattr(row, "quantity", 0.0)),
        uom=clean_text(getattr(row, "uom", "")),
        unit_cost=float(getattr(row, "unit_cost", 0.0) or 0.0),
        unit_cost_label=format_amount(getattr(row, "unit_cost", 0.0)),
        transaction_at_label=format_datetime(getattr(row, "transaction_at", None)),
        reference_type=clean_text(getattr(row, "reference_type", "")),
        reference_id=clean_text(getattr(row, "reference_id", "")),
        performed_by_username=clean_text(getattr(row, "performed_by_username", ""), default="-"),
        resulting_on_hand_qty_label=format_quantity(getattr(row, "resulting_on_hand_qty", 0.0)),
        resulting_available_qty_label=format_quantity(getattr(row, "resulting_available_qty", 0.0)),
        notes=clean_text(getattr(row, "notes", "")),
    )


__all__ = [
    "InventoryAdjustmentCommand",
    "InventoryCatalogItemOptionDescriptor",
    "InventoryIssueCommand",
    "InventoryOpeningBalanceCommand",
    "InventoryProcurementInventoryDesktopApi",
    "InventoryReturnCommand",
    "InventorySiteOptionDescriptor",
    "InventoryStockBalanceDesktopDto",
    "InventoryStockTransactionDesktopDto",
    "InventoryStoreroomCreateCommand",
    "InventoryStoreroomDesktopDto",
    "InventoryStoreroomOptionDescriptor",
    "InventoryStoreroomStatusDescriptor",
    "InventoryStoreroomUpdateCommand",
    "InventoryTransactionTypeDescriptor",
    "InventoryTransferCommand",
    "build_inventory_procurement_inventory_desktop_api",
]
