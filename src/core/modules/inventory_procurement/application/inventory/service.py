from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.inventory_procurement.application.common.support import (
    BUSINESS_PARTY_TYPES,
    STOREROOM_STATUS_TRANSITIONS,
    normalize_inventory_code,
    normalize_optional_text,
    normalize_status,
    resolve_status_from_active,
    validate_transition,
)
from src.core.modules.inventory_procurement.contracts.repositories.inventory import (
    StoreroomRepository,
)
from src.core.modules.inventory_procurement.domain.inventory.stock import Storeroom
from src.core.shared.activity.activity_recorder import record_activity
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.contract.master_data.org.contracts import OrganizationRepository
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.master_data.site import Site
from src.core.shared.events.domain_events import domain_events
from src.core.platform.application.master_data.site.site_service import SiteService
from src.core.platform.application.master_data.party.party_service import PartyService
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)


class InventoryService:
    def __init__(
        self,
        session: Session,
        storeroom_repo: StoreroomRepository,
        *,
        organization_repo: OrganizationRepository,
        site_service: SiteService,
        party_service: PartyService,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        activity_service=None,
    ) -> None:
        self._session: Session = session
        self._storeroom_repo: StoreroomRepository = storeroom_repo
        self._organization_repo: OrganizationRepository = organization_repo
        self._tenant_context_service: TenantContextService = require_tenant_context_service(
            tenant_context_service,
            consumer_label="InventoryService",
        )
        self._site_service: SiteService = site_service
        self._party_service: PartyService = party_service
        self._user_session = user_session
        self._activity_service = activity_service

    def list_storerooms(
        self,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> list[Storeroom]:
        self._require_read("list storerooms")
        organization = self._active_organization()
        normalized_site_id = normalize_optional_text(site_id) or None
        if normalized_site_id is not None:
            self._validate_site_reference(normalized_site_id)
        rows = self._storeroom_repo.list_for_organization(
            organization.id,
            active_only=active_only,
            site_id=normalized_site_id,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="storeroom",
            permission_code="inventory.read",
            scope_id_getter=lambda row: getattr(row, "id", ""),
        )

    def search_storerooms(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
        site_id: str | None = None,
    ) -> list[Storeroom]:
        self._require_read("search storerooms")
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self.list_storerooms(active_only=active_only, site_id=site_id)
        if not normalized_search:
            return rows
        return [
            row
            for row in rows
            if normalized_search in " ".join(
                filter(
                    None,
                    [
                        row.storeroom_code,
                        row.name,
                        row.description,
                        row.storeroom_type,
                        row.status,
                        row.default_currency_code,
                    ],
                )
            ).lower()
        ]

    def get_storeroom(self, storeroom_id: str) -> Storeroom:
        self._require_read("view storeroom")
        storeroom = self.get_storeroom_for_internal_use(storeroom_id)
        require_scope_permission(
            self._user_session,
            "storeroom",
            storeroom.id,
            "inventory.read",
            operation_label="view storeroom",
        )
        return storeroom

    def get_storeroom_for_internal_use(self, storeroom_id: str) -> Storeroom:
        organization = self._active_organization()
        storeroom = self._storeroom_repo.get(storeroom_id)
        if storeroom is None or storeroom.organization_id != organization.id:
            raise NotFoundError("Storeroom not found in the active organization.", code="INVENTORY_STOREROOM_NOT_FOUND")
        return storeroom

    def find_storeroom_by_code(self, storeroom_code: str) -> Storeroom | None:
        self._require_read("resolve storeroom")
        organization = self._active_organization()
        normalized_code = normalize_inventory_code(storeroom_code, label="Storeroom code")
        storeroom = self._storeroom_repo.get_by_code(organization.id, normalized_code)
        if storeroom is None:
            return None
        require_scope_permission(
            self._user_session,
            "storeroom",
            storeroom.id,
            "inventory.read",
            operation_label="resolve storeroom",
        )
        return storeroom

    def create_storeroom(
        self,
        *,
        storeroom_code: str,
        name: str,
        site_id: str,
        description: str = "",
        status: str | None = None,
        storeroom_type: str = "",
        is_internal_supplier: bool = False,
        allows_issue: bool = True,
        allows_transfer: bool = True,
        allows_receiving: bool = True,
        requires_reservation_for_issue: bool = False,
        requires_supplier_reference_for_receipt: bool = False,
        default_currency_code: str | None = None,
        manager_party_id: str | None = None,
        notes: str = "",
    ) -> Storeroom:
        self._require_manage("create storeroom")
        organization = self._active_organization()
        normalized_code = normalize_inventory_code(storeroom_code, label="Storeroom code")
        if self._storeroom_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError(
                "Storeroom code already exists in the active organization.",
                code="INVENTORY_STOREROOM_CODE_EXISTS",
            )
        site = self._validate_site_reference(site_id)
        resolved_status = normalize_status(
            status,
            default_status="DRAFT",
            allowed_statuses=set(STOREROOM_STATUS_TRANSITIONS.keys()),
            label="Storeroom status",
        )
        storeroom = Storeroom.create(
            organization_id=organization.id,
            storeroom_code=normalized_code,
            name=name,
            site_id=site.id,
            description=description,
            status=resolved_status,
            storeroom_type=storeroom_type,
            is_internal_supplier=bool(is_internal_supplier),
            allows_issue=bool(allows_issue),
            allows_transfer=bool(allows_transfer),
            allows_receiving=bool(allows_receiving),
            requires_reservation_for_issue=bool(requires_reservation_for_issue),
            requires_supplier_reference_for_receipt=bool(requires_supplier_reference_for_receipt),
            default_currency_code=default_currency_code or site.currency_code or "",
            manager_party_id=self._validate_party_reference(manager_party_id),
            notes=notes,
        )
        try:
            self._storeroom_repo.add(storeroom)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Storeroom code already exists in the active organization.",
                code="INVENTORY_STOREROOM_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        record_activity(
            self,
            action="inventory_storeroom.create",
            entity_type="inventory_storeroom",
            entity_id=storeroom.id,
            module="inventory",
            details={
                "organization_id": organization.id,
                "storeroom_code": storeroom.storeroom_code,
                "name": storeroom.name,
                "site_id": storeroom.site_id,
                "status": storeroom.status,
            },
        )
        domain_events.inventory_storerooms_changed.emit(storeroom.id)
        return storeroom

    def update_storeroom(
        self,
        storeroom_id: str,
        *,
        storeroom_code: str | None = None,
        name: str | None = None,
        site_id: str | None = None,
        description: str | None = None,
        status: str | None = None,
        storeroom_type: str | None = None,
        is_internal_supplier: bool | None = None,
        allows_issue: bool | None = None,
        allows_transfer: bool | None = None,
        allows_receiving: bool | None = None,
        requires_reservation_for_issue: bool | None = None,
        requires_supplier_reference_for_receipt: bool | None = None,
        default_currency_code: str | None = None,
        manager_party_id: str | None = None,
        is_active: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> Storeroom:
        self._require_manage("update storeroom")
        organization = self._active_organization()
        storeroom = self._storeroom_repo.get(storeroom_id)
        if storeroom is None or storeroom.organization_id != organization.id:
            raise NotFoundError("Storeroom not found in the active organization.", code="INVENTORY_STOREROOM_NOT_FOUND")
        require_scope_permission(
            self._user_session,
            "storeroom",
            storeroom.id,
            "inventory.manage",
            operation_label="update storeroom",
        )
        if expected_version is not None and storeroom.version != expected_version:
            raise ConcurrencyError(
                "Storeroom changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        next_storeroom_code = storeroom.storeroom_code
        if storeroom_code is not None:
            next_storeroom_code = normalize_inventory_code(storeroom_code, label="Storeroom code")
            existing = self._storeroom_repo.get_by_code(organization.id, next_storeroom_code)
            if existing is not None and existing.id != storeroom.id:
                raise ValidationError(
                    "Storeroom code already exists in the active organization.",
                    code="INVENTORY_STOREROOM_CODE_EXISTS",
                )
        next_site_id = storeroom.site_id
        if site_id is not None:
            next_site_id = self._validate_site_reference(site_id).id
        next_manager_party_id = storeroom.manager_party_id
        if manager_party_id is not None:
            next_manager_party_id = self._validate_party_reference(manager_party_id)
        next_status = storeroom.status
        if status is not None:
            next_status = normalize_status(
                status,
                default_status=storeroom.status,
                allowed_statuses=set(STOREROOM_STATUS_TRANSITIONS.keys()),
                label="Storeroom status",
            )
            validate_transition(
                current_status=storeroom.status,
                next_status=next_status,
                transitions=STOREROOM_STATUS_TRANSITIONS,
            )
        elif is_active is not None:
            next_status = resolve_status_from_active(
                current_status=storeroom.status,
                is_active=bool(is_active),
                transitions=STOREROOM_STATUS_TRANSITIONS,
            )
        storeroom = replace(
            storeroom,
            storeroom_code=next_storeroom_code,
            name=storeroom.name if name is None else name,
            site_id=next_site_id,
            description=storeroom.description if description is None else description,
            status=next_status,
            storeroom_type=storeroom.storeroom_type if storeroom_type is None else storeroom_type,
            is_internal_supplier=(
                storeroom.is_internal_supplier
                if is_internal_supplier is None
                else bool(is_internal_supplier)
            ),
            allows_issue=storeroom.allows_issue if allows_issue is None else bool(allows_issue),
            allows_transfer=(
                storeroom.allows_transfer
                if allows_transfer is None
                else bool(allows_transfer)
            ),
            allows_receiving=(
                storeroom.allows_receiving
                if allows_receiving is None
                else bool(allows_receiving)
            ),
            requires_reservation_for_issue=(
                storeroom.requires_reservation_for_issue
                if requires_reservation_for_issue is None
                else bool(requires_reservation_for_issue)
            ),
            requires_supplier_reference_for_receipt=(
                storeroom.requires_supplier_reference_for_receipt
                if requires_supplier_reference_for_receipt is None
                else bool(requires_supplier_reference_for_receipt)
            ),
            default_currency_code=(
                storeroom.default_currency_code
                if default_currency_code is None
                else default_currency_code
            ),
            manager_party_id=next_manager_party_id,
            notes=storeroom.notes if notes is None else notes,
            updated_at=datetime.now(timezone.utc),
        )
        try:
            self._storeroom_repo.update(storeroom)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Storeroom code already exists in the active organization.",
                code="INVENTORY_STOREROOM_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        record_activity(
            self,
            action="inventory_storeroom.update",
            entity_type="inventory_storeroom",
            entity_id=storeroom.id,
            module="inventory",
            details={
                "organization_id": organization.id,
                "storeroom_code": storeroom.storeroom_code,
                "name": storeroom.name,
                "site_id": storeroom.site_id,
                "status": storeroom.status,
            },
        )
        domain_events.inventory_storerooms_changed.emit(storeroom.id)
        return storeroom

    def _validate_site_reference(self, site_id: str) -> Site:
        normalized = normalize_optional_text(site_id)
        if not normalized:
            raise ValidationError("Site is required.", code="INVENTORY_SITE_REQUIRED")
        site = self._site_service.get_site(normalized)
        if not site.is_active:
            raise ValidationError("Storeroom site must be active.", code="INVENTORY_SITE_INACTIVE")
        return site

    def _validate_party_reference(self, party_id: str | None) -> str | None:
        normalized = normalize_optional_text(party_id)
        if not normalized:
            return None
        party = self._party_service.get_party(normalized)
        if not party.is_active:
            raise ValidationError("Storeroom manager party must be active.", code="INVENTORY_PARTY_INACTIVE")
        if party.party_type not in BUSINESS_PARTY_TYPES:
            raise ValidationError(
                "Storeroom manager party must be a supplier, vendor, contractor, or service provider.",
                code="INVENTORY_PARTY_SCOPE_INVALID",
            )
        return party.id

    def _active_organization(self) -> Organization:
        return self._tenant_context_service.require_context(
            operation_label="inventory storerooms"
        ).organization

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "inventory.manage", operation_label=operation_label)


__all__ = ["InventoryService"]
