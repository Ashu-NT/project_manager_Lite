from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.application.runtime.entitlement_runtime import ModuleRuntimeService
from src.core.modules.inventory_procurement.application.common.support import (
    BUSINESS_PARTY_TYPES,
    normalize_inventory_code,
    normalize_inventory_name,
    normalize_nonnegative_days,
    normalize_nonnegative_quantity,
    normalize_optional_date,
    normalize_optional_text,
)
from src.core.modules.inventory_procurement.application.inventory.service import InventoryService
from src.core.modules.inventory_procurement.application.inventory.stock_control_service import (
    StockControlService,
)
from src.core.modules.inventory_procurement.contracts.repositories.inventory import (
    CycleCountRepository,
    ReorderPolicyRepository,
    StorageLocationRepository,
)
from src.core.modules.inventory_procurement.domain.inventory.foundation import (
    CycleCount,
    CycleCountStatus,
    ReorderPolicy,
    StorageLocation,
    StorageLocationType,
)
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.common.ids import generate_id
from src.core.shared.events.domain_events import domain_events
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.org.domain import Organization
from src.core.platform.party import PartyService
from src.core.platform.tenancy.tenant_context import TenantContextService
from src.core.modules.inventory_procurement.application.catalog import ItemMasterService


class InventoryFoundationService:
    def __init__(
        self,
        session: Session,
        location_repo: StorageLocationRepository,
        reorder_policy_repo: ReorderPolicyRepository,
        cycle_count_repo: CycleCountRepository,
        *,
        organization_repo: OrganizationRepository,
        inventory_service: InventoryService,
        item_service: ItemMasterService,
        stock_service: StockControlService,
        party_service: PartyService,
        module_runtime_service: ModuleRuntimeService | None = None,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._location_repo = location_repo
        self._reorder_policy_repo = reorder_policy_repo
        self._cycle_count_repo = cycle_count_repo
        self._organization_repo = organization_repo
        self._tenant_context_service = tenant_context_service or TenantContextService(
            organization_repo=organization_repo,
            user_session=user_session,
        )
        self._inventory_service = inventory_service
        self._item_service = item_service
        self._stock_service = stock_service
        self._party_service = party_service
        self._module_runtime_service = module_runtime_service
        self._user_session = user_session
        self._audit_service = audit_service

    def list_storage_locations(
        self,
        *,
        storeroom_id: str | None = None,
        parent_location_id: str | None = None,
        active_only: bool | None = None,
    ) -> list[StorageLocation]:
        self._require_read("list storage locations")
        organization = self._active_organization()
        normalized_storeroom_id = normalize_optional_text(storeroom_id) or None
        normalized_parent_id = normalize_optional_text(parent_location_id) or None
        if normalized_storeroom_id is not None:
            self._inventory_service.get_storeroom(normalized_storeroom_id)
        if normalized_parent_id is not None:
            self._get_location(normalized_parent_id, organization.id)
        rows = self._location_repo.list_for_organization(
            organization.id,
            storeroom_id=normalized_storeroom_id,
            parent_location_id=normalized_parent_id,
            active_only=active_only,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="storeroom",
            permission_code="inventory.read",
            scope_id_getter=lambda row: getattr(row, "storeroom_id", ""),
        )

    def create_storage_location(
        self,
        *,
        storeroom_id: str,
        location_code: str,
        name: str,
        parent_location_id: str | None = None,
        location_type: str = StorageLocationType.BIN.value,
        is_active: bool = True,
        is_quarantine: bool = False,
        allows_issue: bool = True,
        allows_putaway: bool = True,
        notes: str = "",
    ) -> StorageLocation:
        self._require_manage("create storage location")
        organization = self._active_organization()
        storeroom = self._inventory_service.get_storeroom(storeroom_id)
        require_scope_permission(
            self._user_session,
            "storeroom",
            storeroom.id,
            "inventory.manage",
            operation_label="create storage location",
        )
        normalized_code = normalize_inventory_code(location_code, label="Location code")
        if (
            self._location_repo.get_by_code(organization.id, storeroom.id, normalized_code)
            is not None
        ):
            raise ValidationError(
                "Storage location code already exists in the selected storeroom.",
                code="INVENTORY_LOCATION_CODE_EXISTS",
            )
        normalized_parent_id = self._validate_parent_location(
            organization_id=organization.id,
            storeroom_id=storeroom.id,
            location_id=None,
            parent_location_id=parent_location_id,
        )
        location = StorageLocation.create(
            organization_id=organization.id,
            storeroom_id=storeroom.id,
            location_code=normalized_code,
            name=normalize_inventory_name(name, label="Location name"),
            parent_location_id=normalized_parent_id,
            location_type=self._normalize_location_type(location_type),
            is_active=bool(is_active),
            is_quarantine=bool(is_quarantine),
            allows_issue=bool(allows_issue),
            allows_putaway=bool(allows_putaway),
            notes=normalize_optional_text(notes),
        )
        try:
            self._location_repo.add(location)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Storage location code already exists in the selected storeroom.",
                code="INVENTORY_LOCATION_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_storage_location.create",
            entity_type="inventory_storage_location",
            entity_id=location.id,
            details={
                "storeroom_id": location.storeroom_id,
                "location_code": location.location_code,
                "location_type": location.location_type.value,
            },
        )
        domain_events.inventory_locations_changed.emit(location.id)
        return location

    def update_storage_location(
        self,
        location_id: str,
        *,
        location_code: str | None = None,
        name: str | None = None,
        parent_location_id: str | None = None,
        location_type: str | None = None,
        is_active: bool | None = None,
        is_quarantine: bool | None = None,
        allows_issue: bool | None = None,
        allows_putaway: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> StorageLocation:
        self._require_manage("update storage location")
        organization = self._active_organization()
        location = self._get_location(location_id, organization.id)
        require_scope_permission(
            self._user_session,
            "storeroom",
            location.storeroom_id,
            "inventory.manage",
            operation_label="update storage location",
        )
        if expected_version is not None and location.version != expected_version:
            raise ConcurrencyError(
                "Storage location changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if location_code is not None:
            normalized_code = normalize_inventory_code(location_code, label="Location code")
            existing = self._location_repo.get_by_code(
                organization.id,
                location.storeroom_id,
                normalized_code,
            )
            if existing is not None and existing.id != location.id:
                raise ValidationError(
                    "Storage location code already exists in the selected storeroom.",
                    code="INVENTORY_LOCATION_CODE_EXISTS",
                )
            location.location_code = normalized_code
        if name is not None:
            location.name = normalize_inventory_name(name, label="Location name")
        if location_type is not None:
            location.location_type = self._normalize_location_type(location_type)
        if is_active is not None:
            location.is_active = bool(is_active)
        if is_quarantine is not None:
            location.is_quarantine = bool(is_quarantine)
        if allows_issue is not None:
            location.allows_issue = bool(allows_issue)
        if allows_putaway is not None:
            location.allows_putaway = bool(allows_putaway)
        if notes is not None:
            location.notes = normalize_optional_text(notes)
        if parent_location_id is not None:
            location.parent_location_id = self._validate_parent_location(
                organization_id=organization.id,
                storeroom_id=location.storeroom_id,
                location_id=location.id,
                parent_location_id=parent_location_id,
            )
        location.updated_at = datetime.now(timezone.utc)
        try:
            self._location_repo.update(location)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Storage location code already exists in the selected storeroom.",
                code="INVENTORY_LOCATION_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_storage_location.update",
            entity_type="inventory_storage_location",
            entity_id=location.id,
            details={
                "storeroom_id": location.storeroom_id,
                "location_code": location.location_code,
                "location_type": location.location_type.value,
            },
        )
        domain_events.inventory_locations_changed.emit(location.id)
        return location

    def list_reorder_policies(
        self,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
        location_id: str | None = None,
        active_only: bool | None = None,
    ) -> list[ReorderPolicy]:
        self._require_read("list reorder policies")
        organization = self._active_organization()
        normalized_item_id = normalize_optional_text(stock_item_id) or None
        normalized_storeroom_id = normalize_optional_text(storeroom_id) or None
        normalized_location_id = normalize_optional_text(location_id) or None
        if normalized_item_id is not None:
            self._item_service.get_item(normalized_item_id)
        if normalized_storeroom_id is not None:
            self._inventory_service.get_storeroom(normalized_storeroom_id)
        if normalized_location_id is not None:
            self._get_location(normalized_location_id, organization.id)
        rows = self._reorder_policy_repo.list_for_organization(
            organization.id,
            stock_item_id=normalized_item_id,
            storeroom_id=normalized_storeroom_id,
            location_id=normalized_location_id,
            active_only=active_only,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="storeroom",
            permission_code="inventory.read",
            scope_id_getter=lambda row: getattr(row, "storeroom_id", ""),
        )

    def upsert_reorder_policy(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        location_id: str | None = None,
        policy_name: str = "",
        is_active: bool = True,
        min_qty: float = 0.0,
        max_qty: float = 0.0,
        reorder_point: float = 0.0,
        reorder_qty: float = 0.0,
        economic_order_qty: float = 0.0,
        lead_time_days: int | None = None,
        review_period_days: int | None = None,
        preferred_supplier_party_id: str | None = None,
        policy_id: str | None = None,
        expected_version: int | None = None,
    ) -> ReorderPolicy:
        self._require_manage("save reorder policy")
        organization = self._active_organization()
        item = self._item_service.get_item(stock_item_id)
        storeroom = self._inventory_service.get_storeroom(storeroom_id)
        require_scope_permission(
            self._user_session,
            "storeroom",
            storeroom.id,
            "inventory.manage",
            operation_label="save reorder policy",
        )
        normalized_location_id = self._validate_optional_location(
            organization_id=organization.id,
            storeroom_id=storeroom.id,
            location_id=location_id,
        )
        normalized_min_qty = normalize_nonnegative_quantity(min_qty, label="Minimum quantity")
        normalized_max_qty = normalize_nonnegative_quantity(max_qty, label="Maximum quantity")
        normalized_reorder_point = normalize_nonnegative_quantity(
            reorder_point,
            label="Reorder point",
        )
        normalized_reorder_qty = normalize_nonnegative_quantity(
            reorder_qty,
            label="Reorder quantity",
        )
        normalized_eoq = normalize_nonnegative_quantity(
            economic_order_qty,
            label="Economic order quantity",
        )
        if normalized_max_qty and normalized_min_qty > normalized_max_qty:
            raise ValidationError(
                "Maximum quantity cannot be less than minimum quantity.",
                code="INVENTORY_REORDER_POLICY_MAX_INVALID",
            )
        if normalized_max_qty and normalized_reorder_point > normalized_max_qty:
            raise ValidationError(
                "Reorder point cannot exceed maximum quantity.",
                code="INVENTORY_REORDER_POLICY_POINT_INVALID",
            )
        normalized_supplier_id = self._validate_supplier_reference(
            preferred_supplier_party_id
        )
        policy = None
        normalized_policy_id = normalize_optional_text(policy_id) or None
        if normalized_policy_id is not None:
            policy = self._get_reorder_policy(normalized_policy_id, organization.id)
            require_scope_permission(
                self._user_session,
                "storeroom",
                policy.storeroom_id,
                "inventory.manage",
                operation_label="save reorder policy",
            )
            if expected_version is not None and policy.version != expected_version:
                raise ConcurrencyError(
                    "Reorder policy changed since you opened it. Refresh and try again.",
                    code="STALE_WRITE",
                )
        else:
            policy = self._reorder_policy_repo.get_for_scope(
                organization.id,
                item.id,
                storeroom.id,
                normalized_location_id,
            )
        now = datetime.now(timezone.utc)
        if policy is None:
            policy = ReorderPolicy.create(
                organization_id=organization.id,
                stock_item_id=item.id,
                storeroom_id=storeroom.id,
                location_id=normalized_location_id,
                policy_name=normalize_optional_text(policy_name),
                is_active=bool(is_active),
                min_qty=normalized_min_qty,
                max_qty=normalized_max_qty,
                reorder_point=normalized_reorder_point,
                reorder_qty=normalized_reorder_qty,
                economic_order_qty=normalized_eoq,
                lead_time_days=normalize_nonnegative_days(lead_time_days, label="Lead time"),
                review_period_days=normalize_nonnegative_days(
                    review_period_days,
                    label="Review period",
                ),
                preferred_supplier_party_id=normalized_supplier_id
                or item.preferred_party_id,
            )
            action = "inventory_reorder_policy.create"
            save_method = self._reorder_policy_repo.add
        else:
            policy.stock_item_id = item.id
            policy.storeroom_id = storeroom.id
            policy.location_id = normalized_location_id
            policy.policy_name = normalize_optional_text(policy_name)
            policy.is_active = bool(is_active)
            policy.min_qty = normalized_min_qty
            policy.max_qty = normalized_max_qty
            policy.reorder_point = normalized_reorder_point
            policy.reorder_qty = normalized_reorder_qty
            policy.economic_order_qty = normalized_eoq
            policy.lead_time_days = normalize_nonnegative_days(
                lead_time_days,
                label="Lead time",
            )
            policy.review_period_days = normalize_nonnegative_days(
                review_period_days,
                label="Review period",
            )
            policy.preferred_supplier_party_id = normalized_supplier_id or item.preferred_party_id
            policy.updated_at = now
            action = "inventory_reorder_policy.update"
            save_method = self._reorder_policy_repo.update
        try:
            save_method(policy)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "A reorder policy already exists for the selected stock scope.",
                code="INVENTORY_REORDER_POLICY_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action=action,
            entity_type="inventory_reorder_policy",
            entity_id=policy.id,
            details={
                "stock_item_id": policy.stock_item_id,
                "storeroom_id": policy.storeroom_id,
                "location_id": policy.location_id or "",
                "reorder_point": str(policy.reorder_point),
                "reorder_qty": str(policy.reorder_qty),
            },
        )
        domain_events.inventory_reorder_policies_changed.emit(policy.id)
        return policy

    def list_cycle_counts(
        self,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
        location_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[CycleCount]:
        self._require_read("list cycle counts")
        organization = self._active_organization()
        normalized_item_id = normalize_optional_text(stock_item_id) or None
        normalized_storeroom_id = normalize_optional_text(storeroom_id) or None
        normalized_location_id = normalize_optional_text(location_id) or None
        normalized_status = self._normalize_cycle_count_status(status) if status else None
        if normalized_item_id is not None:
            self._item_service.get_item(normalized_item_id)
        if normalized_storeroom_id is not None:
            self._inventory_service.get_storeroom(normalized_storeroom_id)
        if normalized_location_id is not None:
            self._get_location(normalized_location_id, organization.id)
        rows = self._cycle_count_repo.list_for_organization(
            organization.id,
            stock_item_id=normalized_item_id,
            storeroom_id=normalized_storeroom_id,
            location_id=normalized_location_id,
            status=normalized_status.value if normalized_status else None,
            limit=limit,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="storeroom",
            permission_code="inventory.read",
            scope_id_getter=lambda row: getattr(row, "storeroom_id", ""),
        )

    def schedule_cycle_count(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        location_id: str | None = None,
        scheduled_count_date: date | str | None = None,
        notes: str = "",
    ) -> CycleCount:
        self._require_manage("schedule cycle count")
        organization = self._active_organization()
        item = self._item_service.get_item(stock_item_id)
        storeroom = self._inventory_service.get_storeroom(storeroom_id)
        require_scope_permission(
            self._user_session,
            "storeroom",
            storeroom.id,
            "inventory.manage",
            operation_label="schedule cycle count",
        )
        normalized_location_id = self._validate_optional_location(
            organization_id=organization.id,
            storeroom_id=storeroom.id,
            location_id=location_id,
        )
        balance = self._stock_service.get_balance_for_stock_position(
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
        )
        cycle_count = CycleCount.create(
            organization_id=organization.id,
            cycle_count_number=self._build_cycle_count_number(),
            stock_item_id=item.id,
            storeroom_id=storeroom.id,
            location_id=normalized_location_id,
            scheduled_count_date=normalize_optional_date(
                scheduled_count_date,
                label="Scheduled count date",
            ),
            expected_qty=float(getattr(balance, "on_hand_qty", 0.0) or 0.0),
            notes=normalize_optional_text(notes),
        )
        try:
            self._cycle_count_repo.add(cycle_count)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Cycle count number already exists.",
                code="INVENTORY_CYCLE_COUNT_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="inventory_cycle_count.schedule",
            entity_type="inventory_cycle_count",
            entity_id=cycle_count.id,
            details={
                "cycle_count_number": cycle_count.cycle_count_number,
                "stock_item_id": cycle_count.stock_item_id,
                "storeroom_id": cycle_count.storeroom_id,
                "location_id": cycle_count.location_id or "",
                "expected_qty": str(cycle_count.expected_qty),
            },
        )
        domain_events.inventory_cycle_counts_changed.emit(cycle_count.id)
        return cycle_count

    def complete_cycle_count(
        self,
        cycle_count_id: str,
        *,
        counted_qty: float,
        notes: str = "",
        expected_version: int | None = None,
    ) -> CycleCount:
        self._require_manage("complete cycle count")
        organization = self._active_organization()
        cycle_count = self._get_cycle_count(cycle_count_id, organization.id)
        require_scope_permission(
            self._user_session,
            "storeroom",
            cycle_count.storeroom_id,
            "inventory.manage",
            operation_label="complete cycle count",
        )
        if expected_version is not None and cycle_count.version != expected_version:
            raise ConcurrencyError(
                "Cycle count changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if cycle_count.status in {CycleCountStatus.COMPLETED, CycleCountStatus.CANCELLED}:
            raise ValidationError(
                "Cycle count is already closed.",
                code="INVENTORY_CYCLE_COUNT_STATUS_INVALID",
            )
        effective_count = normalize_nonnegative_quantity(
            counted_qty,
            label="Counted quantity",
        )
        variance = round(effective_count - float(cycle_count.expected_qty or 0.0), 6)
        adjustment_transaction = None
        touched_balance_id = ""
        try:
            if abs(variance) > 1e-9:
                adjustment_transaction = self._stock_service.post_adjustment(
                    stock_item_id=cycle_count.stock_item_id,
                    storeroom_id=cycle_count.storeroom_id,
                    quantity=abs(variance),
                    direction="INCREASE" if variance > 0 else "DECREASE",
                    reference_type="cycle_count",
                    reference_id=cycle_count.id,
                    notes=normalize_optional_text(notes) or cycle_count.notes,
                    commit=False,
                )
                balance = self._stock_service.get_balance_for_stock_position(
                    stock_item_id=cycle_count.stock_item_id,
                    storeroom_id=cycle_count.storeroom_id,
                )
                if balance is not None:
                    touched_balance_id = balance.id
            principal = self._user_session.principal if self._user_session is not None else None
            cycle_count.status = CycleCountStatus.COMPLETED
            cycle_count.counted_qty = effective_count
            cycle_count.variance_qty = variance
            cycle_count.counted_by_user_id = getattr(principal, "user_id", None)
            cycle_count.counted_by_username = str(getattr(principal, "username", "") or "")
            cycle_count.completed_at = datetime.now(timezone.utc)
            cycle_count.notes = normalize_optional_text(notes) or cycle_count.notes
            self._cycle_count_repo.update(cycle_count)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        if adjustment_transaction is not None:
            record_audit(
                self,
                action="inventory_stock_transaction.post",
                entity_type="inventory_stock_transaction",
                entity_id=adjustment_transaction.id,
                details={
                    "transaction_number": adjustment_transaction.transaction_number,
                    "stock_item_id": adjustment_transaction.stock_item_id,
                    "storeroom_id": adjustment_transaction.storeroom_id,
                    "transaction_type": adjustment_transaction.transaction_type.value,
                    "quantity": str(adjustment_transaction.quantity),
                    "reference_id": adjustment_transaction.reference_id,
                },
            )
        record_audit(
            self,
            action="inventory_cycle_count.complete",
            entity_type="inventory_cycle_count",
            entity_id=cycle_count.id,
            details={
                "cycle_count_number": cycle_count.cycle_count_number,
                "counted_qty": str(cycle_count.counted_qty),
                "variance_qty": str(cycle_count.variance_qty),
            },
        )
        if touched_balance_id:
            domain_events.inventory_balances_changed.emit(touched_balance_id)
        domain_events.inventory_cycle_counts_changed.emit(cycle_count.id)
        return cycle_count

    def _active_organization(self) -> Organization:
        return self._tenant_context_service.require_context(
            operation_label="inventory foundation"
        ).organization

    def _get_location(self, location_id: str, organization_id: str) -> StorageLocation:
        location = self._location_repo.get(location_id)
        if location is None or location.organization_id != organization_id:
            raise NotFoundError(
                "Storage location not found in the active organization.",
                code="INVENTORY_LOCATION_NOT_FOUND",
            )
        return location

    def _get_reorder_policy(self, policy_id: str, organization_id: str) -> ReorderPolicy:
        policy = self._reorder_policy_repo.get(policy_id)
        if policy is None or policy.organization_id != organization_id:
            raise NotFoundError(
                "Reorder policy not found in the active organization.",
                code="INVENTORY_REORDER_POLICY_NOT_FOUND",
            )
        return policy

    def _get_cycle_count(self, cycle_count_id: str, organization_id: str) -> CycleCount:
        cycle_count = self._cycle_count_repo.get(cycle_count_id)
        if cycle_count is None or cycle_count.organization_id != organization_id:
            raise NotFoundError(
                "Cycle count not found in the active organization.",
                code="INVENTORY_CYCLE_COUNT_NOT_FOUND",
            )
        return cycle_count

    def _validate_optional_location(
        self,
        *,
        organization_id: str,
        storeroom_id: str,
        location_id: str | None,
    ) -> str | None:
        normalized = normalize_optional_text(location_id)
        if not normalized:
            return None
        location = self._get_location(normalized, organization_id)
        if location.storeroom_id != storeroom_id:
            raise ValidationError(
                "Storage location does not belong to the selected storeroom.",
                code="INVENTORY_LOCATION_SCOPE_INVALID",
            )
        return location.id

    def _validate_parent_location(
        self,
        *,
        organization_id: str,
        storeroom_id: str,
        location_id: str | None,
        parent_location_id: str | None,
    ) -> str | None:
        normalized_parent = normalize_optional_text(parent_location_id)
        if not normalized_parent:
            return None
        parent = self._get_location(normalized_parent, organization_id)
        if parent.storeroom_id != storeroom_id:
            raise ValidationError(
                "Parent location must belong to the same storeroom.",
                code="INVENTORY_LOCATION_PARENT_SCOPE_INVALID",
            )
        if location_id and normalized_parent == location_id:
            raise ValidationError(
                "Storage location cannot be its own parent.",
                code="INVENTORY_LOCATION_PARENT_INVALID",
            )
        current = parent
        while current.parent_location_id:
            if current.parent_location_id == location_id:
                raise ValidationError(
                    "Storage location parent would create a circular hierarchy.",
                    code="INVENTORY_LOCATION_PARENT_CYCLE",
                )
            current = self._get_location(current.parent_location_id, organization_id)
        return parent.id

    def _validate_supplier_reference(self, party_id: str | None) -> str | None:
        normalized = normalize_optional_text(party_id)
        if not normalized:
            return None
        party = self._party_service.get_party(normalized)
        if not party.is_active:
            raise ValidationError(
                "Preferred supplier must be active.",
                code="INVENTORY_PARTY_INACTIVE",
            )
        if party.party_type not in BUSINESS_PARTY_TYPES:
            raise ValidationError(
                "Preferred supplier must be a supported business party.",
                code="INVENTORY_PARTY_SCOPE_INVALID",
            )
        return party.id

    @staticmethod
    def _normalize_location_type(value: str | None) -> StorageLocationType:
        normalized = normalize_optional_text(value).upper() or StorageLocationType.BIN.value
        try:
            return StorageLocationType(normalized)
        except ValueError as exc:
            raise ValidationError(
                "Storage location type is invalid.",
                code="INVENTORY_LOCATION_TYPE_INVALID",
            ) from exc

    @staticmethod
    def _normalize_cycle_count_status(value: str | None) -> CycleCountStatus:
        normalized = normalize_optional_text(value).upper()
        try:
            return CycleCountStatus(normalized)
        except ValueError as exc:
            raise ValidationError(
                "Cycle count status is invalid.",
                code="INVENTORY_CYCLE_COUNT_STATUS_INVALID",
            ) from exc

    def _build_cycle_count_number(self) -> str:
        return f"CC-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{generate_id()[:6].upper()}"

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.manage", operation_label=operation_label)


__all__ = ["InventoryFoundationService"]
