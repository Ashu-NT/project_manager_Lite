from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.application.tenant.modules import ModuleCatalogService
from src.core.modules.inventory_procurement.application.common.support import (
    BUSINESS_PARTY_TYPES,
    normalize_inventory_code,
    normalize_optional_text,
)
from src.core.modules.inventory_procurement.application.inventory.service import InventoryService
from src.core.modules.inventory_procurement.application.inventory.stock_control_service import (
    StockControlService,
)
from src.core.modules.inventory_procurement.contracts.uow.inventory.inventory_foundation_unit_of_work import (
    InventoryFoundationUnitOfWorkFactory,
)
from src.core.modules.inventory_procurement.contracts.repositories.inventory import (
    CycleCountRepository,
    ReorderPolicyRepository,
    StorageLocationRepository,
)
from src.core.modules.inventory_procurement.domain.inventory.balance_events import (
    StockOnHandQuantityChanged,
    StockReservedQuantityChanged,
)
from src.core.modules.inventory_procurement.domain.inventory.cycle_count_events import (
    InventoryCycleCountCompleted,
    InventoryCycleCountScheduled,
)
from src.core.modules.inventory_procurement.domain.inventory.foundation import (
    CycleCount,
    CycleCountStatus,
    ReorderPolicy,
    StorageLocation,
    StorageLocationType,
)
from src.core.modules.inventory_procurement.domain.inventory.foundation_events import (
    InventoryReorderPolicyConfigured,
    LocationCreated,
    LocationProfileUpdated,
)
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.shared.activity.activity_recorder import record_activity
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.common.ids import generate_id
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.application.master_data.party.party_service import PartyService
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)
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
        module_catalog_service: ModuleCatalogService | None = None,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        activity_service=None,
        uow_factory: InventoryFoundationUnitOfWorkFactory | None = None,
    ) -> None:
        self._session = session
        self._location_repo = location_repo
        self._reorder_policy_repo = reorder_policy_repo
        self._cycle_count_repo = cycle_count_repo
        self._organization_repo = organization_repo
        self._tenant_context_service = require_tenant_context_service(
            tenant_context_service,
            consumer_label="InventoryFoundationService",
        )
        self._inventory_service = inventory_service
        self._item_service = item_service
        self._stock_service = stock_service
        self._party_service = party_service
        self._module_catalog_service = module_catalog_service
        self._user_session = user_session
        self._activity_service = activity_service
        self._uow_factory: InventoryFoundationUnitOfWorkFactory | None = uow_factory

    def _require_uow_factory(self) -> InventoryFoundationUnitOfWorkFactory:
        if self._uow_factory is None:
            raise RuntimeError("Inventory foundation unit of work is not configured.")
        return self._uow_factory

    def _new_context(self) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id())

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
            name=name,
            parent_location_id=normalized_parent_id,
            location_type=location_type,
            is_active=bool(is_active),
            is_quarantine=bool(is_quarantine),
            allows_issue=bool(allows_issue),
            allows_putaway=bool(allows_putaway),
            notes=notes,
        )
        with self._require_uow_factory().create(context=self._new_context()) as uow:
            if uow.locations.get_by_code(organization.id, storeroom.id, normalized_code) is not None:
                raise ValidationError(
                    "Storage location code already exists in the selected storeroom.",
                    code="INVENTORY_LOCATION_CODE_EXISTS",
                )
            try:
                uow.locations.add(location)
            except IntegrityError as exc:
                raise ValidationError(
                    "Storage location code already exists in the selected storeroom.",
                    code="INVENTORY_LOCATION_CODE_EXISTS",
                ) from exc
            record_activity(
                uow,
                action="inventory_storage_location.create",
                entity_type="inventory_storage_location",
                entity_id=location.id,
                module="inventory",
                details={
                    "storeroom_id": location.storeroom_id,
                    "location_code": location.location_code,
                    "location_type": location.location_type.value,
                },
                commit=False,
            )
            record_audit_entry(
                uow,
                operation="create",
                entity_type="inventory_storage_location",
                entity_id=location.id,
                module="inventory",
                severity="low",
                metadata={
                    "storeroom_id": location.storeroom_id,
                    "location_code": location.location_code,
                    "location_type": location.location_type.value,
                },
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                LocationCreated(
                    tenant_id=organization.tenant_id,
                    organization_id=organization.id,
                    location_id=location.id,
                    occurred_at=datetime.now(timezone.utc),
                )
            )
            uow.commit()
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
        next_location_code = location.location_code
        if location_code is not None:
            next_location_code = normalize_inventory_code(location_code, label="Location code")
            existing = self._location_repo.get_by_code(
                organization.id,
                location.storeroom_id,
                next_location_code,
            )
            if existing is not None and existing.id != location.id:
                raise ValidationError(
                    "Storage location code already exists in the selected storeroom.",
                    code="INVENTORY_LOCATION_CODE_EXISTS",
                )
        next_parent_location_id = location.parent_location_id
        if parent_location_id is not None:
            next_parent_location_id = self._validate_parent_location(
                organization_id=organization.id,
                storeroom_id=location.storeroom_id,
                location_id=location.id,
                parent_location_id=parent_location_id,
            )
        candidate = replace(
            location,
            location_code=next_location_code,
            name=location.name if name is None else name,
            parent_location_id=next_parent_location_id,
            location_type=location.location_type if location_type is None else location_type,
            is_active=location.is_active if is_active is None else bool(is_active),
            is_quarantine=location.is_quarantine if is_quarantine is None else bool(is_quarantine),
            allows_issue=location.allows_issue if allows_issue is None else bool(allows_issue),
            allows_putaway=(
                location.allows_putaway if allows_putaway is None else bool(allows_putaway)
            ),
            notes=location.notes if notes is None else notes,
        )
        if candidate == location:
            # True no-op (P20 §6): zero repository write, zero audit, zero typed event, no
            # synthetic version/updated_at bump.
            return location
        now = datetime.now(timezone.utc)
        candidate = replace(candidate, updated_at=now)
        with self._require_uow_factory().create(context=self._new_context()) as uow:
            try:
                uow.locations.update(candidate)
            except IntegrityError as exc:
                raise ValidationError(
                    "Storage location code already exists in the selected storeroom.",
                    code="INVENTORY_LOCATION_CODE_EXISTS",
                ) from exc
            record_activity(
                uow,
                action="inventory_storage_location.update",
                entity_type="inventory_storage_location",
                entity_id=candidate.id,
                module="inventory",
                details={
                    "storeroom_id": candidate.storeroom_id,
                    "location_code": candidate.location_code,
                    "location_type": candidate.location_type.value,
                },
                commit=False,
            )
            record_audit_entry(
                uow,
                operation="update",
                entity_type="inventory_storage_location",
                entity_id=candidate.id,
                module="inventory",
                severity="low",
                metadata={
                    "storeroom_id": candidate.storeroom_id,
                    "location_code": candidate.location_code,
                    "location_type": candidate.location_type.value,
                },
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                LocationProfileUpdated(
                    tenant_id=organization.tenant_id,
                    organization_id=organization.id,
                    location_id=candidate.id,
                    occurred_at=now,
                )
            )
            uow.commit()
        return candidate

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
        if policy is None:
            candidate = ReorderPolicy.create(
                organization_id=organization.id,
                stock_item_id=item.id,
                storeroom_id=storeroom.id,
                location_id=normalized_location_id,
                policy_name=policy_name,
                is_active=bool(is_active),
                min_qty=min_qty,
                max_qty=max_qty,
                reorder_point=reorder_point,
                reorder_qty=reorder_qty,
                economic_order_qty=economic_order_qty,
                lead_time_days=lead_time_days,
                review_period_days=review_period_days,
                preferred_supplier_party_id=normalized_supplier_id
                or item.preferred_party_id,
            )
            is_create = True
        else:
            candidate = replace(
                policy,
                stock_item_id=item.id,
                storeroom_id=storeroom.id,
                location_id=normalized_location_id,
                policy_name=policy_name,
                is_active=bool(is_active),
                min_qty=min_qty,
                max_qty=max_qty,
                reorder_point=reorder_point,
                reorder_qty=reorder_qty,
                economic_order_qty=economic_order_qty,
                lead_time_days=lead_time_days,
                review_period_days=review_period_days,
                preferred_supplier_party_id=normalized_supplier_id or item.preferred_party_id,
            )
            if candidate == policy:
                # True no-op (P25 §7): zero repository write, zero audit, zero typed event, no
                # synthetic version/updated_at bump.
                return policy
            is_create = False
        now = datetime.now(timezone.utc)
        if not is_create:
            candidate = replace(candidate, updated_at=now)
        action = (
            "inventory_reorder_policy.create" if is_create else "inventory_reorder_policy.update"
        )
        with self._require_uow_factory().create(context=self._new_context()) as uow:
            try:
                if is_create:
                    uow.reorder_policies.add(candidate)
                else:
                    uow.reorder_policies.update(candidate)
            except IntegrityError as exc:
                raise ValidationError(
                    "A reorder policy already exists for the selected stock scope.",
                    code="INVENTORY_REORDER_POLICY_EXISTS",
                ) from exc
            record_activity(
                uow,
                action=action,
                entity_type="inventory_reorder_policy",
                entity_id=candidate.id,
                module="inventory",
                details={
                    "stock_item_id": candidate.stock_item_id,
                    "storeroom_id": candidate.storeroom_id,
                    "location_id": candidate.location_id or "",
                    "reorder_point": str(candidate.reorder_point),
                    "reorder_qty": str(candidate.reorder_qty),
                },
                commit=False,
            )
            record_audit_entry(
                uow,
                operation="create" if is_create else "update",
                entity_type="inventory_reorder_policy",
                entity_id=candidate.id,
                module="inventory",
                severity="low",
                metadata={
                    "stock_item_id": candidate.stock_item_id,
                    "storeroom_id": candidate.storeroom_id,
                    "location_id": candidate.location_id or "",
                    "reorder_point": str(candidate.reorder_point),
                    "reorder_qty": str(candidate.reorder_qty),
                },
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                InventoryReorderPolicyConfigured(
                    tenant_id=organization.tenant_id,
                    organization_id=organization.id,
                    policy_id=candidate.id,
                    stock_item_id=candidate.stock_item_id,
                    storeroom_id=candidate.storeroom_id,
                    location_id=candidate.location_id,
                    occurred_at=now,
                )
            )
            uow.commit()
        return candidate

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
            scheduled_count_date=scheduled_count_date,
            expected_qty=float(getattr(balance, "on_hand_qty", 0.0) or 0.0),
            notes=notes,
        )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="schedule cycle count"
        )
        occurred_at = datetime.now(timezone.utc)
        try:
            with self._require_uow_factory().create(context=self._new_context()) as uow:
                uow.cycle_counts.add(cycle_count)
                record_activity(
                    uow,
                    action="inventory_cycle_count.schedule",
                    entity_type="inventory_cycle_count",
                    entity_id=cycle_count.id,
                    module="inventory",
                    details={
                        "cycle_count_number": cycle_count.cycle_count_number,
                        "stock_item_id": cycle_count.stock_item_id,
                        "storeroom_id": cycle_count.storeroom_id,
                        "location_id": cycle_count.location_id or "",
                        "expected_qty": str(cycle_count.expected_qty),
                    },
                    commit=False,
                )
                record_audit_entry(
                    uow,
                    operation="create",
                    entity_type="inventory_cycle_count",
                    entity_id=cycle_count.id,
                    module="inventory",
                    severity="low",
                    metadata={
                        "cycle_count_number": cycle_count.cycle_count_number,
                        "stock_item_id": cycle_count.stock_item_id,
                        "storeroom_id": cycle_count.storeroom_id,
                        "expected_qty": str(cycle_count.expected_qty),
                    },
                    commit=False,
                    fail_closed=True,
                )
                uow.record_event(
                    InventoryCycleCountScheduled(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        cycle_count_id=cycle_count.id,
                        storeroom_id=cycle_count.storeroom_id,
                        occurred_at=occurred_at,
                    )
                )
                uow.commit()
        except IntegrityError as exc:
            raise ValidationError(
                "Cycle count number already exists.",
                code="INVENTORY_CYCLE_COUNT_EXISTS",
            ) from exc
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
        principal = self._user_session.principal if self._user_session is not None else None
        resolved_notes = normalize_optional_text(notes) or cycle_count.notes
        completed_cycle_count = replace(
            cycle_count,
            status=CycleCountStatus.COMPLETED,
            counted_qty=counted_qty,
            counted_by_user_id=getattr(principal, "user_id", None),
            counted_by_username=str(getattr(principal, "username", "") or ""),
            completed_at=datetime.now(timezone.utc),
            notes=resolved_notes,
        )
        variance = float(completed_cycle_count.variance_qty or 0.0)
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="complete cycle count"
        )
        with self._require_uow_factory().create(context=self._new_context()) as uow:
            adjustment_transaction = None
            if abs(variance) > 1e-9:
                previous_balance = uow.balances.get_for_stock_position(
                    organization.id,
                    completed_cycle_count.stock_item_id,
                    completed_cycle_count.storeroom_id,
                )
                previous_on_hand = float(previous_balance.on_hand_qty) if previous_balance else 0.0
                adjustment_transaction = uow.stock_service.post_adjustment(
                    stock_item_id=completed_cycle_count.stock_item_id,
                    storeroom_id=completed_cycle_count.storeroom_id,
                    quantity=abs(variance),
                    direction="INCREASE" if variance > 0 else "DECREASE",
                    reference_type="cycle_count",
                    reference_id=completed_cycle_count.id,
                    notes=completed_cycle_count.notes,
                    commit=False,
                )
                balance = uow.balances.get_for_stock_position(
                    organization.id,
                    completed_cycle_count.stock_item_id,
                    completed_cycle_count.storeroom_id,
                )
                if balance is not None:
                    uow.record_event(
                        StockOnHandQuantityChanged(
                            tenant_id=tenant_id,
                            organization_id=organization.id,
                            balance_id=balance.id,
                            stock_item_id=balance.stock_item_id,
                            storeroom_id=balance.storeroom_id,
                            quantity_delta=float(balance.on_hand_qty) - previous_on_hand,
                            resulting_quantity=balance.on_hand_qty,
                            occurred_at=completed_cycle_count.completed_at,
                        )
                    )
            uow.cycle_counts.update(completed_cycle_count)
            if adjustment_transaction is not None:
                record_activity(
                    uow,
                    action="inventory_stock_transaction.post",
                    entity_type="inventory_stock_transaction",
                    entity_id=adjustment_transaction.id,
                    module="inventory",
                    details={
                        "transaction_number": adjustment_transaction.transaction_number,
                        "stock_item_id": adjustment_transaction.stock_item_id,
                        "storeroom_id": adjustment_transaction.storeroom_id,
                        "transaction_type": adjustment_transaction.transaction_type.value,
                        "quantity": str(adjustment_transaction.quantity),
                        "reference_id": adjustment_transaction.reference_id,
                    },
                    commit=False,
                )
            record_activity(
                uow,
                action="inventory_cycle_count.complete",
                entity_type="inventory_cycle_count",
                entity_id=completed_cycle_count.id,
                module="inventory",
                details={
                    "cycle_count_number": completed_cycle_count.cycle_count_number,
                    "counted_qty": str(completed_cycle_count.counted_qty),
                    "variance_qty": str(completed_cycle_count.variance_qty),
                },
                commit=False,
            )

            record_audit_entry(
                uow,
                operation="update",
                entity_type="inventory_cycle_count",
                entity_id=completed_cycle_count.id,
                module="inventory",
                severity="medium",
                metadata={
                    "cycle_count_number": completed_cycle_count.cycle_count_number,
                    "action": "complete",
                    "counted_qty": str(completed_cycle_count.counted_qty),
                    "variance_qty": str(completed_cycle_count.variance_qty),
                },
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                InventoryCycleCountCompleted(
                    tenant_id=tenant_id,
                    organization_id=organization.id,
                    cycle_count_id=completed_cycle_count.id,
                    storeroom_id=completed_cycle_count.storeroom_id,
                    variance_qty=variance,
                    occurred_at=completed_cycle_count.completed_at,
                )
            )
            uow.commit()
        cycle_count = completed_cycle_count
        return cycle_count


    def post_opening_balance(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        quantity: float,
        uom: str | None = None,
        unit_cost: float = 0.0,
        transaction_at: datetime | None = None,
        notes: str = "",
    ):
        organization = self._active_organization()
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="post opening balance"
        )
        with self._require_uow_factory().create(context=self._new_context()) as uow:
            previous_on_hand = self._previous_on_hand(uow, organization.id, stock_item_id, storeroom_id)
            transaction = uow.stock_service.post_opening_balance(
                stock_item_id=stock_item_id,
                storeroom_id=storeroom_id,
                quantity=quantity,
                uom=uom,
                unit_cost=unit_cost,
                transaction_at=transaction_at,
                notes=notes,
                commit=False,
            )
            self._record_movement_transaction_activity(uow, transaction)
            self._record_movement_audit(uow, action="opening_balance", transaction=transaction, notes=notes)
            self._record_on_hand_event(
                uow,
                tenant_id=tenant_id,
                organization_id=organization.id,
                stock_item_id=stock_item_id,
                storeroom_id=storeroom_id,
                previous_on_hand=previous_on_hand,
                occurred_at=transaction.transaction_at,
            )
            uow.commit()
        return transaction

    def post_adjustment(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        quantity: float,
        direction: str,
        uom: str | None = None,
        unit_cost: float = 0.0,
        transaction_at: datetime | None = None,
        reference_type: str = "adjustment",
        reference_id: str = "",
        notes: str = "",
    ):
        organization = self._active_organization()
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="post stock adjustment"
        )
        with self._require_uow_factory().create(context=self._new_context()) as uow:
            previous_on_hand = self._previous_on_hand(uow, organization.id, stock_item_id, storeroom_id)
            transaction = uow.stock_service.post_adjustment(
                stock_item_id=stock_item_id,
                storeroom_id=storeroom_id,
                quantity=quantity,
                direction=direction,
                uom=uom,
                unit_cost=unit_cost,
                transaction_at=transaction_at,
                reference_type=reference_type,
                reference_id=reference_id,
                notes=notes,
                commit=False,
            )
            self._record_movement_transaction_activity(uow, transaction)
            self._record_movement_audit(uow, action="adjustment", transaction=transaction, notes=notes)
            self._record_on_hand_event(
                uow,
                tenant_id=tenant_id,
                organization_id=organization.id,
                stock_item_id=stock_item_id,
                storeroom_id=storeroom_id,
                previous_on_hand=previous_on_hand,
                occurred_at=transaction.transaction_at,
            )
            uow.commit()
        return transaction

    def issue_stock(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        quantity: float,
        uom: str | None = None,
        unit_cost: float | None = None,
        transaction_at: datetime | None = None,
        release_reserved_qty: float = 0.0,
        reference_type: str = "issue",
        reference_id: str = "",
        notes: str = "",
        lot_number: str = "",
        serial_number: str = "",
    ):
        organization = self._active_organization()
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="issue stock"
        )
        with self._require_uow_factory().create(context=self._new_context()) as uow:
            previous_balance = uow.balances.get_for_stock_position(organization.id, stock_item_id, storeroom_id)
            previous_on_hand = float(previous_balance.on_hand_qty) if previous_balance else 0.0
            previous_reserved = float(previous_balance.reserved_qty) if previous_balance else 0.0
            transaction = uow.stock_service.issue_stock(
                stock_item_id=stock_item_id,
                storeroom_id=storeroom_id,
                quantity=quantity,
                uom=uom,
                unit_cost=unit_cost,
                transaction_at=transaction_at,
                release_reserved_qty=release_reserved_qty,
                reference_type=reference_type,
                reference_id=reference_id,
                notes=notes,
                lot_number=lot_number,
                serial_number=serial_number,
                commit=False,
            )
            self._record_movement_transaction_activity(uow, transaction)
            self._record_movement_audit(uow, action="issue", transaction=transaction, notes=notes)
            balance = uow.balances.get_for_stock_position(organization.id, stock_item_id, storeroom_id)
            if balance is not None:
                self._record_balance_event(
                    uow,
                    event_type=StockOnHandQuantityChanged,
                    tenant_id=tenant_id,
                    organization_id=organization.id,
                    balance=balance,
                    quantity_delta=float(balance.on_hand_qty) - previous_on_hand,
                    occurred_at=transaction.transaction_at,
                )
                self._record_balance_event(
                    uow,
                    event_type=StockReservedQuantityChanged,
                    tenant_id=tenant_id,
                    organization_id=organization.id,
                    balance=balance,
                    quantity_delta=float(balance.reserved_qty) - previous_reserved,
                    occurred_at=transaction.transaction_at,
                )
            uow.commit()
        return transaction

    def return_stock(
        self,
        *,
        stock_item_id: str,
        storeroom_id: str,
        quantity: float,
        uom: str | None = None,
        unit_cost: float | None = None,
        transaction_at: datetime | None = None,
        reference_type: str = "return",
        reference_id: str = "",
        notes: str = "",
        lot_number: str = "",
        serial_number: str = "",
    ):
        organization = self._active_organization()
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="return stock"
        )
        with self._require_uow_factory().create(context=self._new_context()) as uow:
            previous_on_hand = self._previous_on_hand(uow, organization.id, stock_item_id, storeroom_id)
            transaction = uow.stock_service.return_stock(
                stock_item_id=stock_item_id,
                storeroom_id=storeroom_id,
                quantity=quantity,
                uom=uom,
                unit_cost=unit_cost,
                transaction_at=transaction_at,
                reference_type=reference_type,
                reference_id=reference_id,
                notes=notes,
                lot_number=lot_number,
                serial_number=serial_number,
                commit=False,
            )
            self._record_movement_transaction_activity(uow, transaction)
            self._record_movement_audit(uow, action="return", transaction=transaction, notes=notes)
            self._record_on_hand_event(
                uow,
                tenant_id=tenant_id,
                organization_id=organization.id,
                stock_item_id=stock_item_id,
                storeroom_id=storeroom_id,
                previous_on_hand=previous_on_hand,
                occurred_at=transaction.transaction_at,
            )
            uow.commit()
        return transaction

    def transfer_stock(
        self,
        *,
        stock_item_id: str,
        source_storeroom_id: str,
        destination_storeroom_id: str,
        quantity: float,
        uom: str | None = None,
        transaction_at: datetime | None = None,
        notes: str = "",
    ):
        organization = self._active_organization()
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="transfer stock"
        )
        with self._require_uow_factory().create(context=self._new_context()) as uow:
            previous_source_on_hand = self._previous_on_hand(
                uow, organization.id, stock_item_id, source_storeroom_id
            )
            previous_destination_on_hand = self._previous_on_hand(
                uow, organization.id, stock_item_id, destination_storeroom_id
            )
            outbound, inbound = uow.stock_service.transfer_stock(
                stock_item_id=stock_item_id,
                source_storeroom_id=source_storeroom_id,
                destination_storeroom_id=destination_storeroom_id,
                quantity=quantity,
                uom=uom,
                transaction_at=transaction_at,
                commit=False,
            )
            self._record_movement_transaction_activity(uow, outbound)
            self._record_movement_transaction_activity(uow, inbound)
            self._record_movement_audit(uow, action="transfer_out", transaction=outbound, notes=notes)
            self._record_movement_audit(uow, action="transfer_in", transaction=inbound, notes=notes)
            self._record_on_hand_event(
                uow,
                tenant_id=tenant_id,
                organization_id=organization.id,
                stock_item_id=stock_item_id,
                storeroom_id=source_storeroom_id,
                previous_on_hand=previous_source_on_hand,
                occurred_at=outbound.transaction_at,
            )
            self._record_on_hand_event(
                uow,
                tenant_id=tenant_id,
                organization_id=organization.id,
                stock_item_id=stock_item_id,
                storeroom_id=destination_storeroom_id,
                previous_on_hand=previous_destination_on_hand,
                occurred_at=inbound.transaction_at,
            )
            uow.commit()
        return outbound, inbound

    def _previous_on_hand(self, uow, organization_id: str, stock_item_id: str, storeroom_id: str) -> float:
        balance = uow.balances.get_for_stock_position(organization_id, stock_item_id, storeroom_id)
        return float(balance.on_hand_qty) if balance is not None else 0.0

    def _record_on_hand_event(
        self,
        uow,
        *,
        tenant_id: str,
        organization_id: str,
        stock_item_id: str,
        storeroom_id: str,
        previous_on_hand: float,
        occurred_at: datetime | None,
    ) -> None:
        balance = uow.balances.get_for_stock_position(organization_id, stock_item_id, storeroom_id)
        if balance is None:
            return
        self._record_balance_event(
            uow,
            event_type=StockOnHandQuantityChanged,
            tenant_id=tenant_id,
            organization_id=organization_id,
            balance=balance,
            quantity_delta=float(balance.on_hand_qty) - previous_on_hand,
            occurred_at=occurred_at,
        )

    @staticmethod
    def _record_balance_event(
        uow,
        *,
        event_type,
        tenant_id: str,
        organization_id: str,
        balance,
        quantity_delta: float,
        occurred_at: datetime | None,
    ) -> None:
        if quantity_delta == 0:
            return
        resulting_quantity = (
            balance.reserved_qty if event_type is StockReservedQuantityChanged else balance.on_hand_qty
        )
        uow.record_event(
            event_type(
                tenant_id=tenant_id,
                organization_id=organization_id,
                balance_id=balance.id,
                stock_item_id=balance.stock_item_id,
                storeroom_id=balance.storeroom_id,
                quantity_delta=quantity_delta,
                resulting_quantity=resulting_quantity,
                occurred_at=occurred_at or datetime.now(timezone.utc),
            )
        )

    @staticmethod
    def _record_movement_transaction_activity(uow, transaction) -> None:
        record_activity(
            uow,
            action="inventory_stock_transaction.post",
            entity_type="inventory_stock_transaction",
            entity_id=transaction.id,
            module="inventory",
            details={
                "transaction_number": transaction.transaction_number,
                "stock_item_id": transaction.stock_item_id,
                "storeroom_id": transaction.storeroom_id,
                "transaction_type": transaction.transaction_type.value,
                "quantity": str(transaction.quantity),
                "uom": transaction.uom,
                "resulting_on_hand_qty": str(transaction.resulting_on_hand_qty),
                "resulting_available_qty": str(transaction.resulting_available_qty),
            },
            commit=False,
        )

    @staticmethod
    def _record_movement_audit(uow, *, action: str, transaction, notes: str) -> None:
        record_audit_entry(
            uow,
            operation=action,
            entity_type="inventory_stock_transaction",
            entity_id=transaction.id,
            module="inventory",
            severity="low",
            metadata={
                "transaction_number": transaction.transaction_number,
                "stock_item_id": transaction.stock_item_id,
                "storeroom_id": transaction.storeroom_id,
                "quantity": str(transaction.quantity),
                "notes": normalize_optional_text(notes),
            },
            commit=False,
            fail_closed=True,
        )

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
