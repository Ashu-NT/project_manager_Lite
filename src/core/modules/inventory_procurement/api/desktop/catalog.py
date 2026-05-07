from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.inventory_procurement.application.catalog import (
    ItemCategoryService,
    ItemMasterService,
)
from src.core.modules.inventory_procurement.application.common.reference_service import (
    InventoryReferenceService,
)
from src.core.modules.inventory_procurement.application.common.support import (
    ITEM_CATEGORY_TYPES,
    ITEM_STATUS_TRANSITIONS,
)
from src.core.modules.inventory_procurement.api.desktop._support import (
    clean_text,
    format_bool_label,
    format_date,
    format_enum_label,
    format_quantity,
)
from src.core.modules.inventory_procurement.api.desktop.shared_options import (
    InventoryBusinessPartyOptionDescriptor,
    serialize_business_party_option,
)


@dataclass(frozen=True)
class InventoryCategoryTypeDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class InventoryItemStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class InventoryDocumentOptionDescriptor:
    value: str
    label: str
    document_type: str
    storage_kind: str
    effective_date_label: str
    is_active: bool


@dataclass(frozen=True)
class InventoryCategoryDesktopDto:
    id: str
    category_code: str
    name: str
    description: str
    category_type: str
    category_type_label: str
    is_equipment: bool
    supports_project_usage: bool
    supports_maintenance_usage: bool
    is_active: bool
    active_label: str
    version: int


@dataclass(frozen=True)
class InventoryItemDesktopDto:
    id: str
    item_code: str
    name: str
    description: str
    item_type: str
    status: str
    status_label: str
    stock_uom: str
    order_uom: str
    issue_uom: str
    order_uom_ratio: float
    order_uom_ratio_label: str
    issue_uom_ratio: float
    issue_uom_ratio_label: str
    category_code: str
    category_label: str
    commodity_code: str
    is_stocked: bool
    is_purchase_allowed: bool
    is_active: bool
    active_label: str
    default_reorder_policy: str
    min_qty: float
    min_qty_label: str
    max_qty: float
    max_qty_label: str
    reorder_point: float
    reorder_point_label: str
    reorder_qty: float
    reorder_qty_label: str
    lead_time_days: int | None
    shelf_life_days: int | None
    is_lot_tracked: bool
    is_serial_tracked: bool
    preferred_party_id: str | None
    preferred_party_label: str
    notes: str
    version: int


@dataclass(frozen=True)
class InventoryCategoryCreateCommand:
    category_code: str
    name: str
    description: str = ""
    category_type: str = "MATERIAL"
    is_equipment: bool = False
    supports_project_usage: bool = False
    supports_maintenance_usage: bool = False
    is_active: bool = True


@dataclass(frozen=True)
class InventoryCategoryUpdateCommand:
    category_id: str
    category_code: str
    name: str
    description: str = ""
    category_type: str = "MATERIAL"
    is_equipment: bool = False
    supports_project_usage: bool = False
    supports_maintenance_usage: bool = False
    is_active: bool = True
    expected_version: int | None = None


@dataclass(frozen=True)
class InventoryItemCreateCommand:
    item_code: str
    name: str
    description: str = ""
    item_type: str = ""
    status: str = "DRAFT"
    stock_uom: str = ""
    order_uom: str | None = None
    issue_uom: str | None = None
    order_uom_ratio: float | None = None
    issue_uom_ratio: float | None = None
    category_code: str = ""
    commodity_code: str = ""
    is_stocked: bool = True
    is_purchase_allowed: bool = True
    default_reorder_policy: str = ""
    min_qty: float = 0.0
    max_qty: float = 0.0
    reorder_point: float = 0.0
    reorder_qty: float = 0.0
    lead_time_days: int | None = None
    is_lot_tracked: bool = False
    is_serial_tracked: bool = False
    shelf_life_days: int | None = None
    preferred_party_id: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class InventoryItemUpdateCommand:
    item_id: str
    item_code: str
    name: str
    description: str = ""
    item_type: str = ""
    status: str = "DRAFT"
    stock_uom: str = ""
    order_uom: str | None = None
    issue_uom: str | None = None
    order_uom_ratio: float | None = None
    issue_uom_ratio: float | None = None
    category_code: str = ""
    commodity_code: str = ""
    is_stocked: bool = True
    is_purchase_allowed: bool = True
    default_reorder_policy: str = ""
    min_qty: float = 0.0
    max_qty: float = 0.0
    reorder_point: float = 0.0
    reorder_qty: float = 0.0
    lead_time_days: int | None = None
    is_lot_tracked: bool = False
    is_serial_tracked: bool = False
    shelf_life_days: int | None = None
    preferred_party_id: str | None = None
    notes: str = ""
    expected_version: int | None = None


class InventoryProcurementCatalogDesktopApi:
    def __init__(
        self,
        *,
        category_service: ItemCategoryService | None = None,
        item_service: ItemMasterService | None = None,
        reference_service: InventoryReferenceService | None = None,
    ) -> None:
        self._category_service = category_service
        self._item_service = item_service
        self._reference_service = reference_service

    def list_category_types(self) -> tuple[InventoryCategoryTypeDescriptor, ...]:
        return tuple(
            InventoryCategoryTypeDescriptor(
                value=value,
                label=format_enum_label(value),
            )
            for value in sorted(ITEM_CATEGORY_TYPES)
        )

    def list_item_statuses(self) -> tuple[InventoryItemStatusDescriptor, ...]:
        return tuple(
            InventoryItemStatusDescriptor(
                value=value,
                label=format_enum_label(value),
            )
            for value in ITEM_STATUS_TRANSITIONS
        )

    def list_business_parties(
        self,
        *,
        active_only: bool | None = True,
    ) -> tuple[InventoryBusinessPartyOptionDescriptor, ...]:
        if self._reference_service is None:
            return ()
        parties = sorted(
            self._reference_service.list_business_parties(active_only=active_only),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "party_name", "") or "").casefold(),
                str(getattr(row, "party_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_business_party_option(row) for row in parties)

    def list_categories(
        self,
        *,
        active_only: bool | None = None,
        category_type: str | None = None,
        search_text: str = "",
        equipment_only: bool | None = None,
        project_usage_only: bool | None = None,
        maintenance_usage_only: bool | None = None,
    ) -> tuple[InventoryCategoryDesktopDto, ...]:
        if self._category_service is None:
            return ()
        if search_text or equipment_only is not None or project_usage_only is not None or maintenance_usage_only is not None:
            categories = self._category_service.search_categories(
                search_text=search_text,
                active_only=active_only,
                category_type=category_type,
                equipment_only=equipment_only,
                project_usage_only=project_usage_only,
                maintenance_usage_only=maintenance_usage_only,
            )
        else:
            categories = self._category_service.list_categories(
                active_only=active_only,
                category_type=category_type,
            )
        ordered = sorted(
            categories,
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "category_code", "") or "").casefold(),
            ),
        )
        return tuple(_serialize_category(row) for row in ordered)

    def list_items(
        self,
        *,
        active_only: bool | None = None,
        search_text: str = "",
        category_code: str | None = None,
        equipment_only: bool | None = None,
        project_usage_only: bool | None = None,
        maintenance_usage_only: bool | None = None,
    ) -> tuple[InventoryItemDesktopDto, ...]:
        if self._item_service is None:
            return ()
        category_lookup = {
            row.category_code: row.name
            for row in self.list_categories(active_only=None)
        }
        party_lookup = {
            row.value: row.label
            for row in self.list_business_parties(active_only=None)
        }
        if search_text or category_code or equipment_only is not None or project_usage_only is not None or maintenance_usage_only is not None:
            items = self._item_service.search_items(
                search_text=search_text,
                active_only=active_only,
                category_code=category_code,
                equipment_only=equipment_only,
                project_usage_only=project_usage_only,
                maintenance_usage_only=maintenance_usage_only,
            )
        else:
            items = self._item_service.list_items(active_only=active_only)
        ordered = sorted(
            items,
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "item_code", "") or "").casefold(),
            ),
        )
        return tuple(
            _serialize_item(
                row,
                category_lookup=category_lookup,
                party_lookup=party_lookup,
            )
            for row in ordered
        )

    def list_available_documents(
        self,
        *,
        active_only: bool | None = True,
    ) -> tuple[InventoryDocumentOptionDescriptor, ...]:
        if self._item_service is None:
            return ()
        documents = sorted(
            self._item_service.list_available_documents(active_only=active_only),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "document_code", "") or "").casefold(),
            ),
        )
        return tuple(_serialize_document(row) for row in documents)

    def list_linked_documents(
        self,
        item_id: str,
        *,
        active_only: bool | None = None,
    ) -> tuple[InventoryDocumentOptionDescriptor, ...]:
        if self._item_service is None:
            return ()
        documents = sorted(
            self._item_service.list_linked_documents(item_id, active_only=active_only),
            key=lambda row: str(getattr(row, "document_code", "") or "").casefold(),
        )
        return tuple(_serialize_document(row) for row in documents)

    def create_category(
        self,
        command: InventoryCategoryCreateCommand,
    ) -> InventoryCategoryDesktopDto:
        service = self._require_category_service()
        category = service.create_category(
            category_code=command.category_code,
            name=command.name,
            description=command.description,
            category_type=command.category_type,
            is_equipment=command.is_equipment,
            supports_project_usage=command.supports_project_usage,
            supports_maintenance_usage=command.supports_maintenance_usage,
            is_active=command.is_active,
        )
        return _serialize_category(category)

    def update_category(
        self,
        command: InventoryCategoryUpdateCommand,
    ) -> InventoryCategoryDesktopDto:
        service = self._require_category_service()
        category = service.update_category(
            command.category_id,
            category_code=command.category_code,
            name=command.name,
            description=command.description,
            category_type=command.category_type,
            is_equipment=command.is_equipment,
            supports_project_usage=command.supports_project_usage,
            supports_maintenance_usage=command.supports_maintenance_usage,
            is_active=command.is_active,
            expected_version=command.expected_version,
        )
        return _serialize_category(category)

    def toggle_category_active(
        self,
        category_id: str,
        *,
        expected_version: int | None = None,
    ) -> InventoryCategoryDesktopDto:
        service = self._require_category_service()
        category = service.get_category(category_id)
        updated = service.update_category(
            category_id,
            is_active=not bool(getattr(category, "is_active", True)),
            expected_version=expected_version,
        )
        return _serialize_category(updated)

    def create_item(self, command: InventoryItemCreateCommand) -> InventoryItemDesktopDto:
        service = self._require_item_service()
        item = service.create_item(
            item_code=command.item_code,
            name=command.name,
            description=command.description,
            item_type=command.item_type,
            status=command.status,
            stock_uom=command.stock_uom,
            order_uom=command.order_uom,
            issue_uom=command.issue_uom,
            order_uom_ratio=command.order_uom_ratio,
            issue_uom_ratio=command.issue_uom_ratio,
            category_code=command.category_code,
            commodity_code=command.commodity_code,
            is_stocked=command.is_stocked,
            is_purchase_allowed=command.is_purchase_allowed,
            default_reorder_policy=command.default_reorder_policy,
            min_qty=command.min_qty,
            max_qty=command.max_qty,
            reorder_point=command.reorder_point,
            reorder_qty=command.reorder_qty,
            lead_time_days=command.lead_time_days,
            is_lot_tracked=command.is_lot_tracked,
            is_serial_tracked=command.is_serial_tracked,
            shelf_life_days=command.shelf_life_days,
            preferred_party_id=command.preferred_party_id,
            notes=command.notes,
        )
        return self._serialize_item(item)

    def update_item(self, command: InventoryItemUpdateCommand) -> InventoryItemDesktopDto:
        service = self._require_item_service()
        item = service.update_item(
            command.item_id,
            item_code=command.item_code,
            name=command.name,
            description=command.description,
            item_type=command.item_type,
            status=command.status,
            stock_uom=command.stock_uom,
            order_uom=command.order_uom,
            issue_uom=command.issue_uom,
            order_uom_ratio=command.order_uom_ratio,
            issue_uom_ratio=command.issue_uom_ratio,
            category_code=command.category_code,
            commodity_code=command.commodity_code,
            is_stocked=command.is_stocked,
            is_purchase_allowed=command.is_purchase_allowed,
            default_reorder_policy=command.default_reorder_policy,
            min_qty=command.min_qty,
            max_qty=command.max_qty,
            reorder_point=command.reorder_point,
            reorder_qty=command.reorder_qty,
            lead_time_days=command.lead_time_days,
            is_lot_tracked=command.is_lot_tracked,
            is_serial_tracked=command.is_serial_tracked,
            shelf_life_days=command.shelf_life_days,
            preferred_party_id=command.preferred_party_id,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return self._serialize_item(item)

    def toggle_item_active(
        self,
        item_id: str,
        *,
        expected_version: int | None = None,
    ) -> InventoryItemDesktopDto:
        service = self._require_item_service()
        item = service.get_item(item_id)
        updated = service.update_item(
            item_id,
            is_active=not bool(getattr(item, "is_active", True)),
            expected_version=expected_version,
        )
        return self._serialize_item(updated)

    def link_document(
        self,
        item_id: str,
        *,
        document_id: str,
        link_role: str = "reference",
    ) -> tuple[InventoryDocumentOptionDescriptor, ...]:
        service = self._require_item_service()
        service.link_document(item_id, document_id=document_id, link_role=link_role)
        return self.list_linked_documents(item_id, active_only=None)

    def unlink_document(
        self,
        item_id: str,
        *,
        document_id: str,
        link_role: str = "reference",
    ) -> tuple[InventoryDocumentOptionDescriptor, ...]:
        service = self._require_item_service()
        service.unlink_document(item_id, document_id=document_id, link_role=link_role)
        return self.list_linked_documents(item_id, active_only=None)

    def _serialize_item(self, item) -> InventoryItemDesktopDto:
        category_lookup = {
            row.category_code: row.name
            for row in self.list_categories(active_only=None)
        }
        party_lookup = {
            row.value: row.label
            for row in self.list_business_parties(active_only=None)
        }
        return _serialize_item(
            item,
            category_lookup=category_lookup,
            party_lookup=party_lookup,
        )

    def _require_category_service(self) -> ItemCategoryService:
        if self._category_service is None:
            raise RuntimeError("Inventory catalog category desktop API is not connected.")
        return self._category_service

    def _require_item_service(self) -> ItemMasterService:
        if self._item_service is None:
            raise RuntimeError("Inventory catalog item desktop API is not connected.")
        return self._item_service


def build_inventory_procurement_catalog_desktop_api(
    *,
    category_service: ItemCategoryService | None = None,
    item_service: ItemMasterService | None = None,
    reference_service: InventoryReferenceService | None = None,
) -> InventoryProcurementCatalogDesktopApi:
    return InventoryProcurementCatalogDesktopApi(
        category_service=category_service,
        item_service=item_service,
        reference_service=reference_service,
    )

def _serialize_document(row) -> InventoryDocumentOptionDescriptor:
    document_type = getattr(getattr(row, "document_type", None), "value", getattr(row, "document_type", ""))
    storage_kind = getattr(getattr(row, "storage_kind", None), "value", getattr(row, "storage_kind", ""))
    label = " - ".join(
        part
        for part in (
            clean_text(getattr(row, "document_code", "")),
            clean_text(getattr(row, "title", "")),
        )
        if part
    )
    return InventoryDocumentOptionDescriptor(
        value=row.id,
        label=label or clean_text(getattr(row, "title", ""), default="-"),
        document_type=str(document_type or ""),
        storage_kind=str(storage_kind or ""),
        effective_date_label=format_date(getattr(row, "effective_date", None)),
        is_active=bool(getattr(row, "is_active", True)),
    )


def _serialize_category(row) -> InventoryCategoryDesktopDto:
    category_type = clean_text(getattr(row, "category_type", ""))
    is_active = bool(getattr(row, "is_active", True))
    return InventoryCategoryDesktopDto(
        id=row.id,
        category_code=clean_text(getattr(row, "category_code", "")),
        name=clean_text(getattr(row, "name", "")),
        description=clean_text(getattr(row, "description", "")),
        category_type=category_type,
        category_type_label=format_enum_label(category_type),
        is_equipment=bool(getattr(row, "is_equipment", False)),
        supports_project_usage=bool(getattr(row, "supports_project_usage", False)),
        supports_maintenance_usage=bool(getattr(row, "supports_maintenance_usage", False)),
        is_active=is_active,
        active_label=format_bool_label(is_active),
        version=int(getattr(row, "version", 1) or 1),
    )


def _serialize_item(
    row,
    *,
    category_lookup: dict[str, str],
    party_lookup: dict[str, str],
) -> InventoryItemDesktopDto:
    status = clean_text(getattr(row, "status", ""))
    category_code = clean_text(getattr(row, "category_code", ""))
    preferred_party_id = clean_text(getattr(row, "preferred_party_id", "")) or None
    is_active = bool(getattr(row, "is_active", False))
    return InventoryItemDesktopDto(
        id=row.id,
        item_code=clean_text(getattr(row, "item_code", "")),
        name=clean_text(getattr(row, "name", "")),
        description=clean_text(getattr(row, "description", "")),
        item_type=clean_text(getattr(row, "item_type", "")),
        status=status,
        status_label=format_enum_label(status),
        stock_uom=clean_text(getattr(row, "stock_uom", "")),
        order_uom=clean_text(getattr(row, "order_uom", "")),
        issue_uom=clean_text(getattr(row, "issue_uom", "")),
        order_uom_ratio=float(getattr(row, "order_uom_ratio", 1.0) or 1.0),
        order_uom_ratio_label=format_quantity(getattr(row, "order_uom_ratio", 1.0), decimals=3),
        issue_uom_ratio=float(getattr(row, "issue_uom_ratio", 1.0) or 1.0),
        issue_uom_ratio_label=format_quantity(getattr(row, "issue_uom_ratio", 1.0), decimals=3),
        category_code=category_code,
        category_label=category_lookup.get(category_code, "-"),
        commodity_code=clean_text(getattr(row, "commodity_code", "")),
        is_stocked=bool(getattr(row, "is_stocked", True)),
        is_purchase_allowed=bool(getattr(row, "is_purchase_allowed", True)),
        is_active=is_active,
        active_label=format_bool_label(is_active),
        default_reorder_policy=clean_text(getattr(row, "default_reorder_policy", "")),
        min_qty=float(getattr(row, "min_qty", 0.0) or 0.0),
        min_qty_label=format_quantity(getattr(row, "min_qty", 0.0)),
        max_qty=float(getattr(row, "max_qty", 0.0) or 0.0),
        max_qty_label=format_quantity(getattr(row, "max_qty", 0.0)),
        reorder_point=float(getattr(row, "reorder_point", 0.0) or 0.0),
        reorder_point_label=format_quantity(getattr(row, "reorder_point", 0.0)),
        reorder_qty=float(getattr(row, "reorder_qty", 0.0) or 0.0),
        reorder_qty_label=format_quantity(getattr(row, "reorder_qty", 0.0)),
        lead_time_days=getattr(row, "lead_time_days", None),
        shelf_life_days=getattr(row, "shelf_life_days", None),
        is_lot_tracked=bool(getattr(row, "is_lot_tracked", False)),
        is_serial_tracked=bool(getattr(row, "is_serial_tracked", False)),
        preferred_party_id=preferred_party_id,
        preferred_party_label=party_lookup.get(preferred_party_id or "", "-"),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 1) or 1),
    )


__all__ = [
    "InventoryBusinessPartyOptionDescriptor",
    "InventoryCategoryCreateCommand",
    "InventoryCategoryDesktopDto",
    "InventoryCategoryTypeDescriptor",
    "InventoryCategoryUpdateCommand",
    "InventoryDocumentOptionDescriptor",
    "InventoryItemCreateCommand",
    "InventoryItemDesktopDto",
    "InventoryItemStatusDescriptor",
    "InventoryItemUpdateCommand",
    "InventoryProcurementCatalogDesktopApi",
    "build_inventory_procurement_catalog_desktop_api",
]
