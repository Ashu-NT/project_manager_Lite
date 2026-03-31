from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.modules.maintenance_management.domain import MaintenanceAsset
from core.modules.maintenance_management.interfaces import (
    MaintenanceAssetRepository,
    MaintenanceLocationRepository,
    MaintenanceSystemRepository,
)
from core.modules.maintenance_management.support import (
    coerce_criticality,
    coerce_lifecycle_status,
    coerce_optional_date,
    coerce_optional_decimal,
    coerce_optional_non_negative_int,
    normalize_maintenance_code,
    normalize_maintenance_name,
    normalize_optional_text,
)
from core.platform.access.authorization import filter_scope_rows, require_scope_permission
from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository, SiteRepository
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from core.platform.org.domain import Organization, Site
from core.platform.party.domain import PartyType
from core.platform.party.interfaces import PartyRepository

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
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._asset_repo = asset_repo
        self._organization_repo = organization_repo
        self._site_repo = site_repo
        self._location_repo = location_repo
        self._system_repo = system_repo
        self._party_repo = party_repo
        self._user_session = user_session
        self._audit_service = audit_service

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
        criticality=None,
        status=None,
        manufacturer_party_id: str | None = None,
        supplier_party_id: str | None = None,
        model_number: str = "",
        serial_number: str = "",
        barcode: str = "",
        install_date=None,
        commission_date=None,
        warranty_start=None,
        warranty_end=None,
        expected_life_years=None,
        replacement_cost=None,
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
        resolved_install_date = coerce_optional_date(install_date, label="Install date")
        resolved_commission_date = coerce_optional_date(commission_date, label="Commission date")
        resolved_warranty_start = coerce_optional_date(warranty_start, label="Warranty start")
        resolved_warranty_end = coerce_optional_date(warranty_end, label="Warranty end")
        self._validate_date_sequence(
            install_date=resolved_install_date,
            commission_date=resolved_commission_date,
            warranty_start=resolved_warranty_start,
            warranty_end=resolved_warranty_end,
        )
        asset = MaintenanceAsset.create(
            organization_id=organization.id,
            site_id=site.id,
            location_id=location.id,
            asset_code=normalized_code,
            name=normalize_maintenance_name(name, label="Asset name"),
            system_id=system.id if system is not None else None,
            description=normalize_optional_text(description),
            parent_asset_id=parent.id if parent is not None else None,
            asset_type=normalize_optional_text(asset_type),
            asset_category=normalize_optional_text(asset_category).upper(),
            criticality=coerce_criticality(criticality),
            status=coerce_lifecycle_status(status, is_active=bool(is_active)),
            manufacturer_party_id=manufacturer.id if manufacturer is not None else None,
            supplier_party_id=supplier.id if supplier is not None else None,
            model_number=normalize_optional_text(model_number),
            serial_number=normalize_optional_text(serial_number),
            barcode=normalize_optional_text(barcode),
            install_date=resolved_install_date,
            commission_date=resolved_commission_date,
            warranty_start=resolved_warranty_start,
            warranty_end=resolved_warranty_end,
            expected_life_years=coerce_optional_non_negative_int(expected_life_years, label="Expected life years"),
            replacement_cost=coerce_optional_decimal(replacement_cost, label="Replacement cost"),
            maintenance_strategy=normalize_optional_text(maintenance_strategy),
            service_level=normalize_optional_text(service_level),
            requires_shutdown_for_major_work=bool(requires_shutdown_for_major_work),
            is_active=bool(is_active),
            notes=normalize_optional_text(notes),
        )
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
        criticality=None,
        status=None,
        manufacturer_party_id: str | None = None,
        supplier_party_id: str | None = None,
        model_number: str | None = None,
        serial_number: str | None = None,
        barcode: str | None = None,
        install_date=None,
        commission_date=None,
        warranty_start=None,
        warranty_end=None,
        expected_life_years=None,
        replacement_cost=None,
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
        if asset_code is not None:
            normalized_code = normalize_maintenance_code(asset_code, label="Asset code")
            existing = self._asset_repo.get_by_code(organization.id, normalized_code)
            if existing is not None and existing.id != asset.id:
                raise ValidationError("Asset code already exists in the active organization.", code="MAINTENANCE_ASSET_CODE_EXISTS")
            asset.asset_code = normalized_code
        if name is not None:
            asset.name = normalize_maintenance_name(name, label="Asset name")
        if description is not None:
            asset.description = normalize_optional_text(description)
        if asset_type is not None:
            asset.asset_type = normalize_optional_text(asset_type)
        if asset_category is not None:
            asset.asset_category = normalize_optional_text(asset_category).upper()
        if criticality is not None:
            asset.criticality = coerce_criticality(criticality)
        if is_active is not None:
            asset.is_active = bool(is_active)
        if status is not None or is_active is not None:
            asset.status = coerce_lifecycle_status(status, is_active=asset.is_active)
        if manufacturer_party_id is not None:
            manufacturer = self._resolve_party(
                normalize_optional_text(manufacturer_party_id) or None,
                organization=organization,
                allowed_types=_MANUFACTURER_PARTY_TYPES,
                not_found_code="MAINTENANCE_ASSET_MANUFACTURER_NOT_FOUND",
                invalid_code="MAINTENANCE_ASSET_MANUFACTURER_INVALID",
                label="Manufacturer",
            )
            asset.manufacturer_party_id = manufacturer.id if manufacturer is not None else None
        if supplier_party_id is not None:
            supplier = self._resolve_party(
                normalize_optional_text(supplier_party_id) or None,
                organization=organization,
                allowed_types=_SUPPLIER_PARTY_TYPES,
                not_found_code="MAINTENANCE_ASSET_SUPPLIER_NOT_FOUND",
                invalid_code="MAINTENANCE_ASSET_SUPPLIER_INVALID",
                label="Supplier",
            )
            asset.supplier_party_id = supplier.id if supplier is not None else None
        if model_number is not None:
            asset.model_number = normalize_optional_text(model_number)
        if serial_number is not None:
            asset.serial_number = normalize_optional_text(serial_number)
        if barcode is not None:
            asset.barcode = normalize_optional_text(barcode)
        if install_date is not None:
            asset.install_date = coerce_optional_date(install_date, label="Install date")
        if commission_date is not None:
            asset.commission_date = coerce_optional_date(commission_date, label="Commission date")
        if warranty_start is not None:
            asset.warranty_start = coerce_optional_date(warranty_start, label="Warranty start")
        if warranty_end is not None:
            asset.warranty_end = coerce_optional_date(warranty_end, label="Warranty end")
        self._validate_date_sequence(
            install_date=asset.install_date,
            commission_date=asset.commission_date,
            warranty_start=asset.warranty_start,
            warranty_end=asset.warranty_end,
        )
        if expected_life_years is not None:
            asset.expected_life_years = coerce_optional_non_negative_int(
                expected_life_years,
                label="Expected life years",
            )
        if replacement_cost is not None:
            asset.replacement_cost = coerce_optional_decimal(replacement_cost, label="Replacement cost")
        if maintenance_strategy is not None:
            asset.maintenance_strategy = normalize_optional_text(maintenance_strategy)
        if service_level is not None:
            asset.service_level = normalize_optional_text(service_level)
        if requires_shutdown_for_major_work is not None:
            asset.requires_shutdown_for_major_work = bool(requires_shutdown_for_major_work)
        if notes is not None:
            asset.notes = normalize_optional_text(notes)
        asset.site_id = target_site_id
        asset.location_id = target_location.id
        asset.system_id = target_system.id if target_system is not None else None
        asset.parent_asset_id = target_parent.id if target_parent is not None else None
        asset.updated_at = datetime.now(timezone.utc)
        try:
            self._asset_repo.update(asset)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Asset code already exists in the active organization.", code="MAINTENANCE_ASSET_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_asset.update", asset)
        return asset

    def _resolve_location(
        self,
        location_id: str,
        *,
        site_id: str,
        organization: Organization,
    ):
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
    ):
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

    @staticmethod
    def _validate_date_sequence(
        *,
        install_date,
        commission_date,
        warranty_start,
        warranty_end,
    ) -> None:
        if install_date is not None and commission_date is not None and commission_date < install_date:
            raise ValidationError("Commission date cannot be earlier than install date.", code="MAINTENANCE_ASSET_DATE_SEQUENCE_INVALID")
        if warranty_start is not None and warranty_end is not None and warranty_end < warranty_start:
            raise ValidationError("Warranty end cannot be earlier than warranty start.", code="MAINTENANCE_ASSET_WARRANTY_RANGE_INVALID")

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _get_site(self, site_id: str, *, organization: Organization) -> Site:
        site = self._site_repo.get(site_id)
        if site is None or site.organization_id != organization.id:
            raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
        return site

    def _get_location(self, location_id: str, *, organization: Organization):
        location = self._location_repo.get(location_id)
        if location is None or location.organization_id != organization.id:
            raise NotFoundError("Maintenance location not found in the active organization.", code="MAINTENANCE_LOCATION_NOT_FOUND")
        return location

    def _get_system(self, system_id: str, *, organization: Organization):
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
        record_audit(
            self,
            action=action,
            entity_type="maintenance_asset",
            entity_id=asset.id,
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
