from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.maintenance.domain._validation import normalize_maintenance_code
from src.core.modules.maintenance.domain import MaintenanceAssetComponent
from src.core.modules.maintenance.contracts.repositories import (
    MaintenanceAssetComponentRepository,
    MaintenanceAssetRepository,
)
from src.core.modules.maintenance.application.common.support import (
    normalize_optional_text,
)
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.shared.activity.activity_recorder import record_activity
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.contract.master_data.org.contracts import OrganizationRepository
from src.core.platform.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)
from src.core.shared.events.domain_events import DomainChangeEvent, domain_events
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.master_data.party import PartyType
from src.core.platform.contract.master_data.party.contracts import PartyRepository

_MANUFACTURER_PARTY_TYPES = {
    PartyType.MANUFACTURER,
    PartyType.SUPPLIER,
    PartyType.VENDOR,
    PartyType.SERVICE_PROVIDER,
}
_SUPPLIER_PARTY_TYPES = {
    PartyType.SUPPLIER,
    PartyType.VENDOR,
    PartyType.CONTRACTOR,
    PartyType.SERVICE_PROVIDER,
}


class MaintenanceAssetComponentService:
    def __init__(
        self,
        session: Session,
        component_repo: MaintenanceAssetComponentRepository,
        *,
        asset_repo: MaintenanceAssetRepository,
        organization_repo: OrganizationRepository,
        party_repo: PartyRepository,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        activity_service=None,
    ) -> None:
        self._session = session
        self._component_repo = component_repo
        self._asset_repo = asset_repo
        self._organization_repo = organization_repo
        self._tenant_context_service = require_tenant_context_service(
            tenant_context_service,
            consumer_label="MaintenanceAssetComponentService",
        )
        self._party_repo = party_repo
        self._user_session = user_session
        self._activity_service = activity_service

    def list_components(
        self,
        *,
        active_only: bool | None = None,
        asset_id: str | None = None,
        parent_component_id: str | None = None,
        component_type: str | None = None,
    ) -> list[MaintenanceAssetComponent]:
        self._require_read("list maintenance asset components")
        organization = self._active_organization()
        if asset_id is not None:
            self._get_asset(asset_id, organization=organization)
        if parent_component_id is not None:
            self._get_component(parent_component_id, organization=organization)
        rows = self._component_repo.list_for_organization(
            organization.id,
            active_only=active_only,
            asset_id=asset_id,
            parent_component_id=parent_component_id,
            component_type=normalize_optional_text(component_type).upper() or None,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=lambda row: getattr(row, "asset_id", "") or getattr(row, "id", ""),
        )


    def search_components(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
        asset_id: str | None = None,
        component_type: str | None = None,
    ) -> list[MaintenanceAssetComponent]:
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self.list_components(
            active_only=active_only,
            asset_id=asset_id,
            component_type=component_type,
        )
        if not normalized_search:
            return rows
        return [
            row
            for row in rows
            if normalized_search in " ".join(
                filter(
                    None,
                    [
                        row.component_code,
                        row.name,
                        row.description,
                        row.component_type,
                        row.status.value,
                        row.manufacturer_part_number,
                        row.supplier_part_number,
                        row.model_number,
                        row.serial_number,
                    ],
                )
            ).lower()
        ]

    def get_component(self, component_id: str) -> MaintenanceAssetComponent:
        self._require_read("view maintenance asset component")
        component = self._get_component(component_id, organization=self._active_organization())
        require_scope_permission(
            self._user_session,
            "maintenance",
            component.asset_id or component.id,
            "maintenance.read",
            operation_label="view maintenance asset component",
        )
        return component

    def find_component_by_code(
        self,
        component_code: str,
        *,
        active_only: bool | None = None,
    ) -> MaintenanceAssetComponent | None:
        self._require_read("resolve maintenance asset component")
        organization = self._active_organization()
        component = self._component_repo.get_by_code(
            organization.id,
            normalize_maintenance_code(component_code, label="Component code"),
        )
        if component is None:
            return None
        if active_only is not None and component.is_active != bool(active_only):
            return None
        return component

    def create_component(
        self,
        *,
        asset_id: str,
        component_code: str,
        name: str,
        description: str = "",
        parent_component_id: str | None = None,
        component_type: str = "",
        status=None,
        manufacturer_party_id: str | None = None,
        supplier_party_id: str | None = None,
        manufacturer_part_number: str = "",
        supplier_part_number: str = "",
        model_number: str = "",
        serial_number: str = "",
        install_date=None,
        warranty_end=None,
        expected_life_hours=None,
        expected_life_cycles=None,
        is_critical_component: bool = False,
        is_active: bool = True,
        notes: str = "",
    ) -> MaintenanceAssetComponent:
        self._require_manage("create maintenance asset component")
        organization = self._active_organization()
        asset = self._get_asset(asset_id, organization=organization)
        normalized_code = normalize_maintenance_code(component_code, label="Component code")
        if self._component_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError(
                "Component code already exists in the active organization.",
                code="MAINTENANCE_COMPONENT_CODE_EXISTS",
            )
        parent = self._resolve_parent(parent_component_id, asset_id=asset.id, organization=organization)
        manufacturer = self._resolve_party(
            manufacturer_party_id,
            organization=organization,
            allowed_types=_MANUFACTURER_PARTY_TYPES,
            not_found_code="MAINTENANCE_COMPONENT_MANUFACTURER_NOT_FOUND",
            invalid_code="MAINTENANCE_COMPONENT_MANUFACTURER_INVALID",
            label="Manufacturer",
        )
        supplier = self._resolve_party(
            supplier_party_id,
            organization=organization,
            allowed_types=_SUPPLIER_PARTY_TYPES,
            not_found_code="MAINTENANCE_COMPONENT_SUPPLIER_NOT_FOUND",
            invalid_code="MAINTENANCE_COMPONENT_SUPPLIER_INVALID",
            label="Supplier",
        )
        component = MaintenanceAssetComponent.create(
            organization_id=organization.id,
            asset_id=asset.id,
            component_code=component_code,
            name=name,
            description=description,
            parent_component_id=parent.id if parent is not None else None,
            component_type=component_type,
            status=status,
            manufacturer_party_id=manufacturer.id if manufacturer is not None else None,
            supplier_party_id=supplier.id if supplier is not None else None,
            manufacturer_part_number=manufacturer_part_number,
            supplier_part_number=supplier_part_number,
            model_number=model_number,
            serial_number=serial_number,
            install_date=install_date,
            warranty_end=warranty_end,
            expected_life_hours=expected_life_hours,
            expected_life_cycles=expected_life_cycles,
            is_critical_component=is_critical_component,
            is_active=is_active,
            notes=notes,
        )
        if self._component_repo.get_by_code(organization.id, component.component_code) is not None:
            raise ValidationError(
                "Component code already exists in the active organization.",
                code="MAINTENANCE_COMPONENT_CODE_EXISTS",
            )
        try:
            self._component_repo.add(component)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Component code already exists in the active organization.",
                code="MAINTENANCE_COMPONENT_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_asset_component.create", component)
        return component

    def update_component(
        self,
        component_id: str,
        *,
        asset_id: str | None = None,
        component_code: str | None = None,
        name: str | None = None,
        description: str | None = None,
        parent_component_id: str | None = None,
        component_type: str | None = None,
        status=None,
        manufacturer_party_id: str | None = None,
        supplier_party_id: str | None = None,
        manufacturer_part_number: str | None = None,
        supplier_part_number: str | None = None,
        model_number: str | None = None,
        serial_number: str | None = None,
        install_date=None,
        warranty_end=None,
        expected_life_hours=None,
        expected_life_cycles=None,
        is_critical_component: bool | None = None,
        is_active: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceAssetComponent:
        self._require_manage("update maintenance asset component")
        organization = self._active_organization()
        component = self._get_component(component_id, organization=organization)
        if expected_version is not None and component.version != expected_version:
            raise ConcurrencyError(
                "Maintenance asset component changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        target_asset_id = component.asset_id if asset_id is None else asset_id
        target_asset = self._get_asset(target_asset_id, organization=organization)
        requested_parent_id = (
            component.parent_component_id
            if parent_component_id is None
            else normalize_optional_text(parent_component_id) or None
        )
        target_parent = self._resolve_parent(
            requested_parent_id,
            asset_id=target_asset.id,
            organization=organization,
            self_id=component.id,
        )
        next_manufacturer_party_id = component.manufacturer_party_id
        if manufacturer_party_id is not None:
            manufacturer = self._resolve_party(
                normalize_optional_text(manufacturer_party_id) or None,
                organization=organization,
                allowed_types=_MANUFACTURER_PARTY_TYPES,
                not_found_code="MAINTENANCE_COMPONENT_MANUFACTURER_NOT_FOUND",
                invalid_code="MAINTENANCE_COMPONENT_MANUFACTURER_INVALID",
                label="Manufacturer",
            )
            next_manufacturer_party_id = manufacturer.id if manufacturer is not None else None
        next_supplier_party_id = component.supplier_party_id
        if supplier_party_id is not None:
            supplier = self._resolve_party(
                normalize_optional_text(supplier_party_id) or None,
                organization=organization,
                allowed_types=_SUPPLIER_PARTY_TYPES,
                not_found_code="MAINTENANCE_COMPONENT_SUPPLIER_NOT_FOUND",
                invalid_code="MAINTENANCE_COMPONENT_SUPPLIER_INVALID",
                label="Supplier",
            )
            next_supplier_party_id = supplier.id if supplier is not None else None
        updated = replace(
            component,
            asset_id=target_asset.id,
            component_code=component.component_code if component_code is None else component_code,
            name=component.name if name is None else name,
            description=component.description if description is None else description,
            parent_component_id=target_parent.id if target_parent is not None else None,
            component_type=component.component_type if component_type is None else component_type,
            status=component.status if status is None and is_active is None else status,
            manufacturer_party_id=next_manufacturer_party_id,
            supplier_party_id=next_supplier_party_id,
            manufacturer_part_number=(
                component.manufacturer_part_number
                if manufacturer_part_number is None
                else manufacturer_part_number
            ),
            supplier_part_number=(
                component.supplier_part_number
                if supplier_part_number is None
                else supplier_part_number
            ),
            model_number=component.model_number if model_number is None else model_number,
            serial_number=component.serial_number if serial_number is None else serial_number,
            install_date=component.install_date if install_date is None else install_date,
            warranty_end=component.warranty_end if warranty_end is None else warranty_end,
            expected_life_hours=(
                component.expected_life_hours
                if expected_life_hours is None
                else expected_life_hours
            ),
            expected_life_cycles=(
                component.expected_life_cycles
                if expected_life_cycles is None
                else expected_life_cycles
            ),
            is_critical_component=(
                component.is_critical_component
                if is_critical_component is None
                else is_critical_component
            ),
            is_active=component.is_active if is_active is None else is_active,
            notes=component.notes if notes is None else notes,
            updated_at=datetime.now(timezone.utc),
        )
        if component_code is not None:
            existing = self._component_repo.get_by_code(organization.id, updated.component_code)
            if existing is not None and existing.id != component.id:
                raise ValidationError(
                    "Component code already exists in the active organization.",
                    code="MAINTENANCE_COMPONENT_CODE_EXISTS",
                )
        try:
            self._component_repo.update(updated)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Component code already exists in the active organization.",
                code="MAINTENANCE_COMPONENT_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_asset_component.update", updated)
        return updated

    def _resolve_parent(
        self,
        parent_component_id: str | None,
        *,
        asset_id: str,
        organization: Organization,
        self_id: str | None = None,
    ) -> MaintenanceAssetComponent | None:
        if parent_component_id in (None, ""):
            return None
        if self_id and parent_component_id == self_id:
            raise BusinessRuleError(
                "A component cannot be its own parent.",
                code="MAINTENANCE_COMPONENT_PARENT_INVALID",
            )
        parent = self._get_component(parent_component_id, organization=organization)
        if parent.asset_id != asset_id:
            raise ValidationError(
                "Parent component must belong to the same asset.",
                code="MAINTENANCE_COMPONENT_ASSET_MISMATCH",
            )
        return parent

    def _resolve_party(
        self,
        party_id: str | None,
        *,
        organization: Organization,
        allowed_types: set[PartyType],
        not_found_code: str,
        invalid_code: str,
        label: str,
    ):
        if party_id in (None, ""):
            return None
        party = self._party_repo.get(party_id)
        if party is None or party.organization_id != organization.id:
            raise NotFoundError(f"{label} party not found in the active organization.", code=not_found_code)
        if not party.is_active or party.party_type not in allowed_types:
            raise ValidationError(
                f"{label} party must be active and of a supported business type.",
                code=invalid_code,
            )
        return party

    def _active_organization(self) -> Organization:
        return self._tenant_context_service.require_context(
            operation_label="maintenance asset components"
        ).organization

    def _get_asset(self, asset_id: str, *, organization: Organization):
        asset = self._asset_repo.get(asset_id)
        if asset is None or asset.organization_id != organization.id:
            raise NotFoundError("Maintenance asset not found in the active organization.", code="MAINTENANCE_ASSET_NOT_FOUND")
        return asset

    def _get_component(self, component_id: str, *, organization: Organization) -> MaintenanceAssetComponent:
        component = self._component_repo.get(component_id)
        if component is None or component.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance asset component not found in the active organization.",
                code="MAINTENANCE_COMPONENT_NOT_FOUND",
            )
        return component

    def _record_change(self, action: str, component: MaintenanceAssetComponent) -> None:
        record_activity(
            self,
            action=action,
            entity_type="maintenance_asset_component",
            entity_id=component.id,
            module="maintenance",
            details={
                "organization_id": component.organization_id,
                "asset_id": component.asset_id,
                "component_code": component.component_code,
                "name": component.name,
                "status": component.status.value,
                "component_type": component.component_type,
                "is_active": str(component.is_active),
                "is_critical_component": str(component.is_critical_component),
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_asset_component",
                entity_id=component.id,
                source_event="maintenance_asset_components_changed",
            )
        )

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenanceAssetComponentService"]
