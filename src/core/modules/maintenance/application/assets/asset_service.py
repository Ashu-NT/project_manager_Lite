from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from datetime import date

from decimal import Decimal

from src.core.modules.maintenance.domain._validation import normalize_maintenance_code
from src.core.modules.maintenance.domain import (
    MaintenanceAsset,
    MaintenanceCriticality,
    MaintenanceLifecycleStatus,
    MaintenanceLocation,
    MaintenanceSystem,
)
from src.core.modules.maintenance.contracts.repositories import (
    MaintenanceAssetRepository,
    MaintenanceLocationRepository,
    MaintenanceSystemRepository,
)
from src.core.modules.maintenance.application.common.support import (
    normalize_optional_text,
)
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.shared.activity.activity_recorder import record_activity
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.contract.master_data.site.contracts import SiteRepository
from src.core.platform.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)
from src.core.shared.events.domain_events import DomainChangeEvent, domain_events
from src.core.platform.org.domain import Organization
from src.core.platform.domain.master_data.site import Site
from src.core.platform.party.domain import Party, PartyType
from src.core.platform.party.contracts import PartyRepository

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


class MaintenanceAssetService:
    def __init__(
        self,
        session: Session,
        asset_repo: MaintenanceAssetRepository,
        *,
        organization_repo: OrganizationRepository,
        site_repo: SiteRepository,
        location_repo: MaintenanceLocationRepository,
        system_repo: MaintenanceSystemRepository,
        party_repo: PartyRepository,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        activity_service=None,
    ) -> None:
        self._session: Session = session
        self._asset_repo: MaintenanceAssetRepository = asset_repo
        self._organization_repo: OrganizationRepository = organization_repo
        self._tenant_context_service: TenantContextService = require_tenant_context_service(
            tenant_context_service,
            consumer_label="MaintenanceAssetService",
        )
        self._site_repo: SiteRepository = site_repo
        self._location_repo: MaintenanceLocationRepository = location_repo
        self._system_repo: MaintenanceSystemRepository = system_repo
        self._party_repo: PartyRepository = party_repo
        self._user_session = user_session
        self._activity_service = activity_service

    def list_assets(
        self,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        location_id: str | None = None,
        system_id: str | None = None,
        parent_asset_id: str | None = None,
        asset_category: str | None = None,
    ) -> list[MaintenanceAsset]:
        self._require_read("list maintenance assets")
        organization = self._active_organization()
        if site_id is not None:
            self._get_site(site_id, organization=organization)
        if location_id is not None:
            self._get_location(location_id, organization=organization)
        if system_id is not None:
            self._get_system(system_id, organization=organization)
        if parent_asset_id is not None:
            self._get_asset(parent_asset_id, organization=organization)
        rows = self._asset_repo.list_for_organization(
            organization.id,
            active_only=active_only,
            site_id=site_id,
            location_id=location_id,
            system_id=system_id,
            parent_asset_id=parent_asset_id,
            asset_category=normalize_optional_text(asset_category).upper() or None,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=lambda row: getattr(row, "id", ""),
        )

    def search_assets(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
        site_id: str | None = None,
        location_id: str | None = None,
        system_id: str | None = None,
        asset_category: str | None = None,
    ) -> list[MaintenanceAsset]:
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self.list_assets(
            active_only=active_only,
            site_id=site_id,
            location_id=location_id,
            system_id=system_id,
            asset_category=asset_category,
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
                        row.asset_code,
                        row.name,
                        row.description,
                        row.asset_type,
                        row.asset_category,
                        row.status.value,
                        row.criticality.value,
                        row.model_number,
                        row.serial_number,
                        row.barcode,
                        row.maintenance_strategy,
                        row.service_level,
                    ],
                )
            ).lower()
        ]

    def get_asset(self, asset_id: str) -> MaintenanceAsset:
        self._require_read("view maintenance asset")
        asset = self._get_asset(asset_id, organization=self._active_organization())
        require_scope_permission(
            self._user_session,
            "maintenance",
            asset.id,
            "maintenance.read",
            operation_label="view maintenance asset",
        )
        return asset

    def find_asset_by_code(
        self,
        asset_code: str,
        *,
        active_only: bool | None = None,
    ) -> MaintenanceAsset | None:
        self._require_read("resolve maintenance asset")
        organization = self._active_organization()
        asset = self._asset_repo.get_by_code(
            organization.id,
            normalize_maintenance_code(asset_code, label="Asset code"),
        )
        if asset is None:
            return None
        if active_only is not None and asset.is_active != bool(active_only):
            return None
        return asset

    def create_asset(
        self,
        *,
        site_id: str,
        location_id: str,
        asset_code: str,
        name: str,
        system_id: str | None = None,
        description: str = "",
        parent_asset_id: str | None = None,
        asset_type: str = "",
        asset_category: str = "",
        criticality: MaintenanceCriticality | str | None = None,
        status: MaintenanceLifecycleStatus | str | None = None,
        manufacturer_party_id: str | None = None,
        supplier_party_id: str | None = None,
        model_number: str = "",
        serial_number: str = "",
        barcode: str = "",
        install_date: date | str | None = None,
        commission_date: date | str | None = None,
        warranty_start: date | str | None = None,
        warranty_end: date | str | None = None,
        expected_life_years: int | str | None = None,
        replacement_cost: Decimal | int | float | str | None = None,
        maintenance_strategy: str = "",
        service_level: str = "",
        requires_shutdown_for_major_work: bool = False,
        is_active: bool = True,
        notes: str = "",
    ) -> MaintenanceAsset:
        self._require_manage("create maintenance asset")
        organization = self._active_organization()
        site = self._get_site(site_id, organization=organization)
        normalized_code = normalize_maintenance_code(asset_code, label="Asset code")
        if self._asset_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError("Asset code already exists in the active organization.", code="MAINTENANCE_ASSET_CODE_EXISTS")
        location = self._resolve_location(location_id, site_id=site.id, organization=organization)
        system = self._resolve_system(system_id, site_id=site.id, organization=organization, location_id=location.id)
        parent = self._resolve_parent(
            parent_asset_id,
            site_id=site.id,
            organization=organization,
            location_id=location.id,
            system_id=system.id if system is not None else None,
        )
        manufacturer = self._resolve_party(
            manufacturer_party_id,
            organization=organization,
            allowed_types=_MANUFACTURER_PARTY_TYPES,
            not_found_code="MAINTENANCE_ASSET_MANUFACTURER_NOT_FOUND",
            invalid_code="MAINTENANCE_ASSET_MANUFACTURER_INVALID",
            label="Manufacturer",
        )
        supplier = self._resolve_party(
            supplier_party_id,
            organization=organization,
            allowed_types=_SUPPLIER_PARTY_TYPES,
            not_found_code="MAINTENANCE_ASSET_SUPPLIER_NOT_FOUND",
            invalid_code="MAINTENANCE_ASSET_SUPPLIER_INVALID",
            label="Supplier",
        )
        asset = MaintenanceAsset.create(
            organization_id=organization.id,
            site_id=site.id,
            location_id=location.id,
            asset_code=asset_code,
            name=name,
            system_id=system.id if system is not None else None,
            description=description,
            parent_asset_id=parent.id if parent is not None else None,
            asset_type=asset_type,
            asset_category=asset_category,
            criticality=criticality,
            status=status,
            manufacturer_party_id=manufacturer.id if manufacturer is not None else None,
            supplier_party_id=supplier.id if supplier is not None else None,
            model_number=model_number,
            serial_number=serial_number,
            barcode=barcode,
            install_date=install_date,
            commission_date=commission_date,
            warranty_start=warranty_start,
            warranty_end=warranty_end,
            expected_life_years=expected_life_years,
            replacement_cost=replacement_cost,
            maintenance_strategy=maintenance_strategy,
            service_level=service_level,
            requires_shutdown_for_major_work=requires_shutdown_for_major_work,
            is_active=is_active,
            notes=notes,
        )
        if self._asset_repo.get_by_code(organization.id, asset.asset_code) is not None:
            raise ValidationError("Asset code already exists in the active organization.", code="MAINTENANCE_ASSET_CODE_EXISTS")
        try:
            self._asset_repo.add(asset)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Asset code already exists in the active organization.", code="MAINTENANCE_ASSET_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_asset.create", asset)
        return asset

    def update_asset(
        self,
        asset_id: str,
        *,
        site_id: str | None = None,
        location_id: str | None = None,
        asset_code: str | None = None,
        name: str | None = None,
        system_id: str | None = None,
        description: str | None = None,
        parent_asset_id: str | None = None,
        asset_type: str | None = None,
        asset_category: str | None = None,
        criticality: MaintenanceCriticality | str | None = None,
        status: MaintenanceLifecycleStatus | str | None = None,
        manufacturer_party_id: str | None = None,
        supplier_party_id: str | None = None,
        model_number: str | None = None,
        serial_number: str | None = None,
        barcode: str | None = None,
        install_date: date | str | None = None,
        commission_date: date | str | None = None,
        warranty_start: date | str | None = None,
        warranty_end: date | str | None = None,
        expected_life_years: int | str | None = None,
        replacement_cost: Decimal | int | float | str | None = None,
        maintenance_strategy: str | None = None,
        service_level: str | None = None,
        requires_shutdown_for_major_work: bool | None = None,
        is_active: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceAsset:
        self._require_manage("update maintenance asset")
        organization = self._active_organization()
        asset = self._get_asset(asset_id, organization=organization)
        if expected_version is not None and asset.version != expected_version:
            raise ConcurrencyError(
                "Maintenance asset changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        target_site_id = asset.site_id
        if site_id is not None:
            target_site_id = self._get_site(site_id, organization=organization).id
        target_location_id = asset.location_id if location_id is None else location_id
        target_location = self._resolve_location(target_location_id, site_id=target_site_id, organization=organization)
        requested_system_id = asset.system_id if system_id is None else normalize_optional_text(system_id) or None
        target_system = self._resolve_system(
            requested_system_id,
            site_id=target_site_id,
            organization=organization,
            location_id=target_location.id,
        )
        requested_parent_id = asset.parent_asset_id if parent_asset_id is None else normalize_optional_text(parent_asset_id) or None
        target_parent = self._resolve_parent(
            requested_parent_id,
            site_id=target_site_id,
            organization=organization,
            location_id=target_location.id,
            system_id=target_system.id if target_system is not None else None,
            self_id=asset.id,
        )
        next_manufacturer_party_id = asset.manufacturer_party_id
        if manufacturer_party_id is not None:
            manufacturer = self._resolve_party(
                normalize_optional_text(manufacturer_party_id) or None,
                organization=organization,
                allowed_types=_MANUFACTURER_PARTY_TYPES,
                not_found_code="MAINTENANCE_ASSET_MANUFACTURER_NOT_FOUND",
                invalid_code="MAINTENANCE_ASSET_MANUFACTURER_INVALID",
                label="Manufacturer",
            )
            next_manufacturer_party_id = manufacturer.id if manufacturer is not None else None
        next_supplier_party_id = asset.supplier_party_id
        if supplier_party_id is not None:
            supplier = self._resolve_party(
                normalize_optional_text(supplier_party_id) or None,
                organization=organization,
                allowed_types=_SUPPLIER_PARTY_TYPES,
                not_found_code="MAINTENANCE_ASSET_SUPPLIER_NOT_FOUND",
                invalid_code="MAINTENANCE_ASSET_SUPPLIER_INVALID",
                label="Supplier",
            )
            next_supplier_party_id = supplier.id if supplier is not None else None
        updated = replace(
            asset,
            site_id=target_site_id,
            location_id=target_location.id,
            asset_code=asset.asset_code if asset_code is None else asset_code,
            name=asset.name if name is None else name,
            system_id=target_system.id if target_system is not None else None,
            description=asset.description if description is None else description,
            parent_asset_id=target_parent.id if target_parent is not None else None,
            asset_type=asset.asset_type if asset_type is None else asset_type,
            asset_category=asset.asset_category if asset_category is None else asset_category,
            criticality=asset.criticality if criticality is None else criticality,
            status=asset.status if status is None and is_active is None else status,
            manufacturer_party_id=next_manufacturer_party_id,
            supplier_party_id=next_supplier_party_id,
            model_number=asset.model_number if model_number is None else model_number,
            serial_number=asset.serial_number if serial_number is None else serial_number,
            barcode=asset.barcode if barcode is None else barcode,
            install_date=asset.install_date if install_date is None else install_date,
            commission_date=asset.commission_date if commission_date is None else commission_date,
            warranty_start=asset.warranty_start if warranty_start is None else warranty_start,
            warranty_end=asset.warranty_end if warranty_end is None else warranty_end,
            expected_life_years=asset.expected_life_years if expected_life_years is None else expected_life_years,
            replacement_cost=asset.replacement_cost if replacement_cost is None else replacement_cost,
            maintenance_strategy=asset.maintenance_strategy if maintenance_strategy is None else maintenance_strategy,
            service_level=asset.service_level if service_level is None else service_level,
            requires_shutdown_for_major_work=(
                asset.requires_shutdown_for_major_work
                if requires_shutdown_for_major_work is None
                else requires_shutdown_for_major_work
            ),
            is_active=asset.is_active if is_active is None else is_active,
            notes=asset.notes if notes is None else notes,
            updated_at=datetime.now(timezone.utc),
        )
        if asset_code is not None:
            existing = self._asset_repo.get_by_code(organization.id, updated.asset_code)
            if existing is not None and existing.id != asset.id:
                raise ValidationError("Asset code already exists in the active organization.", code="MAINTENANCE_ASSET_CODE_EXISTS")
        try:
            self._asset_repo.update(updated)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Asset code already exists in the active organization.", code="MAINTENANCE_ASSET_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_asset.update", updated)
        return updated

    def _resolve_location(
        self,
        location_id: str,
        *,
        site_id: str,
        organization: Organization,
    ) -> MaintenanceLocation:
        location = self._get_location(location_id, organization=organization)
        if location.site_id != site_id:
            raise ValidationError("Maintenance asset location must belong to the same site.", code="MAINTENANCE_ASSET_SITE_MISMATCH")
        return location

    def _resolve_system(
        self,
        system_id: str | None,
        *,
        site_id: str,
        organization: Organization,
        location_id: str,
    ) -> MaintenanceSystem | None:
        if system_id in (None, ""):
            return None
        system = self._get_system(system_id, organization=organization)
        if system.site_id != site_id:
            raise ValidationError("Maintenance asset system must belong to the same site.", code="MAINTENANCE_ASSET_SITE_MISMATCH")
        if system.location_id not in (None, location_id):
            raise ValidationError("Maintenance asset system must align to the same location.", code="MAINTENANCE_ASSET_LOCATION_MISMATCH")
        return system

    def _resolve_parent(
        self,
        parent_asset_id: str | None,
        *,
        site_id: str,
        organization: Organization,
        location_id: str,
        system_id: str | None,
        self_id: str | None = None,
    ) -> MaintenanceAsset | None:
        if parent_asset_id in (None, ""):
            return None
        if self_id and parent_asset_id == self_id:
            raise BusinessRuleError("An asset cannot be its own parent.", code="MAINTENANCE_ASSET_PARENT_INVALID")
        parent = self._get_asset(parent_asset_id, organization=organization)
        if parent.site_id != site_id:
            raise ValidationError("Parent maintenance asset must belong to the same site.", code="MAINTENANCE_ASSET_SITE_MISMATCH")
        if parent.location_id != location_id:
            raise ValidationError("Parent maintenance asset must belong to the same location.", code="MAINTENANCE_ASSET_LOCATION_MISMATCH")
        if system_id is not None and parent.system_id not in (None, system_id):
            raise ValidationError("Parent maintenance asset must align to the same system.", code="MAINTENANCE_ASSET_SYSTEM_MISMATCH")
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
    ) -> Party | None:
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
            operation_label="maintenance assets"
        ).organization

    def _get_site(self, site_id: str, *, organization: Organization) -> Site:
        site = self._site_repo.get(site_id)
        if site is None or site.organization_id != organization.id:
            raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
        return site

    def _get_location(self, location_id: str, *, organization: Organization) -> MaintenanceLocation:
        location = self._location_repo.get(location_id)
        if location is None or location.organization_id != organization.id:
            raise NotFoundError("Maintenance location not found in the active organization.", code="MAINTENANCE_LOCATION_NOT_FOUND")
        return location

    def _get_system(self, system_id: str, *, organization: Organization) -> MaintenanceSystem:
        system = self._system_repo.get(system_id)
        if system is None or system.organization_id != organization.id:
            raise NotFoundError("Maintenance system not found in the active organization.", code="MAINTENANCE_SYSTEM_NOT_FOUND")
        return system

    def _get_asset(self, asset_id: str, *, organization: Organization) -> MaintenanceAsset:
        asset = self._asset_repo.get(asset_id)
        if asset is None or asset.organization_id != organization.id:
            raise NotFoundError("Maintenance asset not found in the active organization.", code="MAINTENANCE_ASSET_NOT_FOUND")
        return asset

    def _record_change(self, action: str, asset: MaintenanceAsset) -> None:
        record_activity(
            self,
            action=action,
            entity_type="maintenance_asset",
            entity_id=asset.id,
            module="maintenance",
            details={
                "organization_id": asset.organization_id,
                "site_id": asset.site_id,
                "location_id": asset.location_id,
                "system_id": asset.system_id or "",
                "asset_code": asset.asset_code,
                "name": asset.name,
                "status": asset.status.value,
                "criticality": asset.criticality.value,
                "asset_category": asset.asset_category,
                "is_active": str(asset.is_active),
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_asset",
                entity_id=asset.id,
                source_event="maintenance_assets_changed",
            )
        )

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenanceAssetService"]
