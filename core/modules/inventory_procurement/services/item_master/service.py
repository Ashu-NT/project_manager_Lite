from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.inventory_procurement.domain import StockItem
from core.modules.inventory_procurement.interfaces import StockItemRepository
from core.modules.inventory_procurement.support import (
    BUSINESS_PARTY_TYPES,
    ITEM_STATUS_TRANSITIONS,
    normalize_inventory_code,
    normalize_inventory_name,
    normalize_nonnegative_days,
    normalize_nonnegative_quantity,
    normalize_optional_text,
    normalize_status,
    normalize_uom,
    resolve_active_flag_from_status,
    resolve_status_from_active,
    validate_transition,
)
from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository
from core.platform.common.models import Organization
from core.platform.documents import DocumentIntegrationService, DocumentLink
from core.platform.documents.domain import Document
from core.platform.notifications.domain_events import domain_events
from core.platform.party import PartyService


class ItemMasterService:
    def __init__(
        self,
        session: Session,
        item_repo: StockItemRepository,
        *,
        organization_repo: OrganizationRepository,
        party_service: PartyService,
        document_integration_service: DocumentIntegrationService,
        user_session=None,
        audit_service=None,
    ):
        self._session = session
        self._item_repo = item_repo
        self._organization_repo = organization_repo
        self._party_service = party_service
        self._document_integration_service = document_integration_service
        self._user_session = user_session
        self._audit_service = audit_service

    def list_items(self, *, active_only: bool | None = None) -> list[StockItem]:
        self._require_read("list inventory items")
        organization = self._active_organization()
        return self._item_repo.list_for_organization(organization.id, active_only=active_only)

    def search_items(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
    ) -> list[StockItem]:
        self._require_read("search inventory items")
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self.list_items(active_only=active_only)
        if not normalized_search:
            return rows
        return [
            item
            for item in rows
            if normalized_search in " ".join(
                filter(
                    None,
                    [
                        item.item_code,
                        item.name,
                        item.description,
                        item.item_type,
                        item.category_code,
                        item.commodity_code,
                        item.status,
                        item.stock_uom,
                    ],
                )
            ).lower()
        ]

    def get_item(self, item_id: str) -> StockItem:
        self._require_read("view inventory item")
        organization = self._active_organization()
        item = self._item_repo.get(item_id)
        if item is None or item.organization_id != organization.id:
            raise NotFoundError("Inventory item not found in the active organization.", code="INVENTORY_ITEM_NOT_FOUND")
        return item

    def find_item_by_code(self, item_code: str) -> StockItem | None:
        self._require_read("resolve inventory item")
        organization = self._active_organization()
        normalized_code = normalize_inventory_code(item_code, label="Item code")
        return self._item_repo.get_by_code(organization.id, normalized_code)

    def create_item(
        self,
        *,
        item_code: str,
        name: str,
        description: str = "",
        item_type: str = "",
        status: str | None = None,
        stock_uom: str,
        order_uom: str | None = None,
        issue_uom: str | None = None,
        category_code: str = "",
        commodity_code: str = "",
        is_stocked: bool = True,
        is_purchase_allowed: bool = True,
        default_reorder_policy: str = "",
        min_qty: float = 0.0,
        max_qty: float = 0.0,
        reorder_point: float = 0.0,
        reorder_qty: float = 0.0,
        lead_time_days: int | None = None,
        is_lot_tracked: bool = False,
        is_serial_tracked: bool = False,
        shelf_life_days: int | None = None,
        preferred_party_id: str | None = None,
        notes: str = "",
    ) -> StockItem:
        self._require_manage("create inventory item")
        organization = self._active_organization()
        normalized_code = normalize_inventory_code(item_code, label="Item code")
        if self._item_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError("Item code already exists in the active organization.", code="INVENTORY_ITEM_CODE_EXISTS")
        resolved_status = normalize_status(
            status,
            default_status="DRAFT",
            allowed_statuses=set(ITEM_STATUS_TRANSITIONS.keys()),
            label="Inventory item status",
        )
        item = StockItem.create(
            organization_id=organization.id,
            item_code=normalized_code,
            name=normalize_inventory_name(name, label="Item name"),
            description=normalize_optional_text(description),
            item_type=normalize_optional_text(item_type).upper(),
            status=resolved_status,
            stock_uom=normalize_uom(stock_uom, label="Stock UOM"),
            order_uom=normalize_uom(order_uom or stock_uom, label="Order UOM"),
            issue_uom=normalize_uom(issue_uom or stock_uom, label="Issue UOM"),
            category_code=normalize_optional_text(category_code).upper(),
            commodity_code=normalize_optional_text(commodity_code).upper(),
            is_stocked=bool(is_stocked),
            is_purchase_allowed=bool(is_purchase_allowed),
            is_active=resolve_active_flag_from_status(resolved_status),
            default_reorder_policy=normalize_optional_text(default_reorder_policy).upper(),
            min_qty=normalize_nonnegative_quantity(min_qty, label="Minimum quantity"),
            max_qty=normalize_nonnegative_quantity(max_qty, label="Maximum quantity"),
            reorder_point=normalize_nonnegative_quantity(reorder_point, label="Reorder point"),
            reorder_qty=normalize_nonnegative_quantity(reorder_qty, label="Reorder quantity"),
            lead_time_days=normalize_nonnegative_days(lead_time_days, label="Lead time days"),
            is_lot_tracked=bool(is_lot_tracked),
            is_serial_tracked=bool(is_serial_tracked),
            shelf_life_days=normalize_nonnegative_days(shelf_life_days, label="Shelf life days"),
            preferred_party_id=self._validate_party_reference(preferred_party_id),
            notes=normalize_optional_text(notes),
        )
        self._validate_reorder_quantities(item)
        try:
            self._item_repo.add(item)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Item code already exists in the active organization.", code="INVENTORY_ITEM_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_item.create",
            entity_type="inventory_item",
            entity_id=item.id,
            details={
                "organization_id": organization.id,
                "item_code": item.item_code,
                "name": item.name,
                "status": item.status,
                "stock_uom": item.stock_uom,
                "preferred_party_id": item.preferred_party_id or "",
            },
        )
        domain_events.inventory_items_changed.emit(item.id)
        return item

    def update_item(
        self,
        item_id: str,
        *,
        item_code: str | None = None,
        name: str | None = None,
        description: str | None = None,
        item_type: str | None = None,
        status: str | None = None,
        is_stocked: bool | None = None,
        is_purchase_allowed: bool | None = None,
        stock_uom: str | None = None,
        order_uom: str | None = None,
        issue_uom: str | None = None,
        category_code: str | None = None,
        commodity_code: str | None = None,
        default_reorder_policy: str | None = None,
        min_qty: float | None = None,
        max_qty: float | None = None,
        reorder_point: float | None = None,
        reorder_qty: float | None = None,
        lead_time_days: int | None = None,
        is_lot_tracked: bool | None = None,
        is_serial_tracked: bool | None = None,
        shelf_life_days: int | None = None,
        preferred_party_id: str | None = None,
        is_active: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> StockItem:
        self._require_manage("update inventory item")
        organization = self._active_organization()
        item = self._item_repo.get(item_id)
        if item is None or item.organization_id != organization.id:
            raise NotFoundError("Inventory item not found in the active organization.", code="INVENTORY_ITEM_NOT_FOUND")
        if expected_version is not None and item.version != expected_version:
            raise ConcurrencyError(
                "Inventory item changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if item_code is not None:
            normalized_code = normalize_inventory_code(item_code, label="Item code")
            existing = self._item_repo.get_by_code(organization.id, normalized_code)
            if existing is not None and existing.id != item.id:
                raise ValidationError("Item code already exists in the active organization.", code="INVENTORY_ITEM_CODE_EXISTS")
            item.item_code = normalized_code
        if name is not None:
            item.name = normalize_inventory_name(name, label="Item name")
        if description is not None:
            item.description = normalize_optional_text(description)
        if item_type is not None:
            item.item_type = normalize_optional_text(item_type).upper()
        if stock_uom is not None:
            item.stock_uom = normalize_uom(stock_uom, label="Stock UOM")
        if order_uom is not None:
            item.order_uom = normalize_uom(order_uom, label="Order UOM")
        elif stock_uom is not None and not normalize_optional_text(item.order_uom):
            item.order_uom = item.stock_uom
        if issue_uom is not None:
            item.issue_uom = normalize_uom(issue_uom, label="Issue UOM")
        elif stock_uom is not None and not normalize_optional_text(item.issue_uom):
            item.issue_uom = item.stock_uom
        if category_code is not None:
            item.category_code = normalize_optional_text(category_code).upper()
        if commodity_code is not None:
            item.commodity_code = normalize_optional_text(commodity_code).upper()
        if is_stocked is not None:
            item.is_stocked = bool(is_stocked)
        if is_purchase_allowed is not None:
            item.is_purchase_allowed = bool(is_purchase_allowed)
        if default_reorder_policy is not None:
            item.default_reorder_policy = normalize_optional_text(default_reorder_policy).upper()
        if min_qty is not None:
            item.min_qty = normalize_nonnegative_quantity(min_qty, label="Minimum quantity")
        if max_qty is not None:
            item.max_qty = normalize_nonnegative_quantity(max_qty, label="Maximum quantity")
        if reorder_point is not None:
            item.reorder_point = normalize_nonnegative_quantity(reorder_point, label="Reorder point")
        if reorder_qty is not None:
            item.reorder_qty = normalize_nonnegative_quantity(reorder_qty, label="Reorder quantity")
        if lead_time_days is not None:
            item.lead_time_days = normalize_nonnegative_days(lead_time_days, label="Lead time days")
        if is_lot_tracked is not None:
            item.is_lot_tracked = bool(is_lot_tracked)
        if is_serial_tracked is not None:
            item.is_serial_tracked = bool(is_serial_tracked)
        if shelf_life_days is not None:
            item.shelf_life_days = normalize_nonnegative_days(shelf_life_days, label="Shelf life days")
        if preferred_party_id is not None:
            item.preferred_party_id = self._validate_party_reference(preferred_party_id)
        next_status = item.status
        if status is not None:
            next_status = normalize_status(
                status,
                default_status=item.status,
                allowed_statuses=set(ITEM_STATUS_TRANSITIONS.keys()),
                label="Inventory item status",
            )
            validate_transition(
                current_status=item.status,
                next_status=next_status,
                transitions=ITEM_STATUS_TRANSITIONS,
            )
        elif is_active is not None:
            next_status = resolve_status_from_active(
                current_status=item.status,
                is_active=bool(is_active),
                transitions=ITEM_STATUS_TRANSITIONS,
            )
        item.status = next_status
        item.is_active = resolve_active_flag_from_status(item.status)
        if notes is not None:
            item.notes = normalize_optional_text(notes)
        self._validate_reorder_quantities(item)
        item.updated_at = datetime.now(timezone.utc)
        try:
            self._item_repo.update(item)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Item code already exists in the active organization.", code="INVENTORY_ITEM_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_item.update",
            entity_type="inventory_item",
            entity_id=item.id,
            details={
                "organization_id": organization.id,
                "item_code": item.item_code,
                "name": item.name,
                "status": item.status,
                "stock_uom": item.stock_uom,
                "preferred_party_id": item.preferred_party_id or "",
            },
        )
        domain_events.inventory_items_changed.emit(item.id)
        return item

    def list_linked_documents(self, item_id: str, *, active_only: bool | None = None) -> list[Document]:
        item = self.get_item(item_id)
        return self._document_integration_service.list_documents_for_entity(
            required_permission="inventory.read",
            operation_label="list inventory item documents",
            module_code="inventory_procurement",
            entity_type="stock_item",
            entity_id=item.id,
            active_only=active_only,
        )

    def list_available_documents(self, *, active_only: bool | None = True) -> list[Document]:
        return self._document_integration_service.list_available_documents(
            required_permission="inventory.read",
            operation_label="list inventory document library",
            active_only=active_only,
        )

    def link_document(
        self,
        item_id: str,
        *,
        document_id: str,
        link_role: str = "reference",
    ) -> DocumentLink:
        item = self.get_item(item_id)
        link = self._document_integration_service.link_existing_document(
            required_permission="inventory.manage",
            operation_label="link inventory item document",
            module_code="inventory_procurement",
            entity_type="stock_item",
            entity_id=item.id,
            document_id=document_id,
            link_role=link_role,
        )
        record_audit(
            self,
            action="inventory_item.link_document",
            entity_type="inventory_item",
            entity_id=item.id,
            details={
                "document_id": document_id,
                "link_role": normalize_optional_text(link_role) or "reference",
            },
        )
        domain_events.inventory_items_changed.emit(item.id)
        return link

    def unlink_document(
        self,
        item_id: str,
        *,
        document_id: str,
        link_role: str = "reference",
    ) -> None:
        item = self.get_item(item_id)
        self._document_integration_service.unlink_existing_document(
            required_permission="inventory.manage",
            operation_label="unlink inventory item document",
            module_code="inventory_procurement",
            entity_type="stock_item",
            entity_id=item.id,
            document_id=document_id,
            link_role=link_role,
        )
        record_audit(
            self,
            action="inventory_item.unlink_document",
            entity_type="inventory_item",
            entity_id=item.id,
            details={
                "document_id": document_id,
                "link_role": normalize_optional_text(link_role) or "reference",
            },
        )
        domain_events.inventory_items_changed.emit(item.id)

    def _validate_party_reference(self, party_id: str | None) -> str | None:
        normalized = normalize_optional_text(party_id)
        if not normalized:
            return None
        party = self._party_service.get_party(normalized)
        if not party.is_active:
            raise ValidationError("Preferred party must be active.", code="INVENTORY_PARTY_INACTIVE")
        if party.party_type not in BUSINESS_PARTY_TYPES:
            raise ValidationError(
                "Preferred party must be a supplier, vendor, contractor, or service provider.",
                code="INVENTORY_PARTY_SCOPE_INVALID",
            )
        return party.id

    def _validate_reorder_quantities(self, item: StockItem) -> None:
        if item.max_qty and item.max_qty < item.min_qty:
            raise ValidationError(
                "Maximum quantity cannot be less than minimum quantity.",
                code="INVENTORY_REORDER_RANGE_INVALID",
            )
        if item.max_qty and item.reorder_point > item.max_qty:
            raise ValidationError(
                "Reorder point cannot exceed maximum quantity.",
                code="INVENTORY_REORDER_POINT_INVALID",
            )

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.manage", operation_label=operation_label)


__all__ = ["ItemMasterService"]
