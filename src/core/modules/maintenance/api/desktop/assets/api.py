from __future__ import annotations

from src.core.modules.maintenance import (
    MaintenanceAssetComponentService,
    MaintenanceAssetService,
    MaintenanceLocationService,
    MaintenanceSystemService,
)
from src.core.modules.maintenance.api.desktop._support import format_enum_label
from src.core.modules.maintenance.api.desktop.assets.models import (
    MaintenanceAssetCreateCommand,
    MaintenanceAssetDesktopDto,
    MaintenanceAssetUpdateCommand,
    MaintenanceComponentCreateCommand,
    MaintenanceComponentDesktopDto,
    MaintenanceComponentUpdateCommand,
    MaintenanceCriticalityDescriptor,
    MaintenanceLifecycleStatusDescriptor,
    MaintenanceLocationCreateCommand,
    MaintenanceLocationDesktopDto,
    MaintenanceLocationUpdateCommand,
    MaintenanceSystemCreateCommand,
    MaintenanceSystemDesktopDto,
    MaintenanceSystemUpdateCommand,
)
from src.core.modules.maintenance.api.desktop.assets.serializers import (
    asset_label,
    build_lookup,
    component_label,
    location_label,
    serialize_asset,
    serialize_component,
    serialize_location,
    serialize_system,
    system_label,
)
from src.core.modules.maintenance.api.desktop.shared_options import (
    MaintenanceAssetOptionDescriptor,
    MaintenanceBusinessPartyOptionDescriptor,
    MaintenanceComponentOptionDescriptor,
    MaintenanceLocationOptionDescriptor,
    MaintenanceSiteOptionDescriptor,
    MaintenanceSystemOptionDescriptor,
    serialize_asset_option,
    serialize_business_party_option,
    serialize_component_option,
    serialize_location_option,
    serialize_site_option,
    serialize_system_option,
)
from src.core.modules.maintenance.domain import (
    MaintenanceCriticality,
    MaintenanceLifecycleStatus,
)
from src.core.platform.site import SiteService
from src.core.platform.party import PartyService, PartyType

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


class MaintenanceAssetsDesktopApi:
    def __init__(
        self,
        *,
        location_service: MaintenanceLocationService | None = None,
        system_service: MaintenanceSystemService | None = None,
        asset_service: MaintenanceAssetService | None = None,
        component_service: MaintenanceAssetComponentService | None = None,
        site_service: SiteService | None = None,
        party_service: PartyService | None = None,
    ) -> None:
        self._location_service = location_service
        self._system_service = system_service
        self._asset_service = asset_service
        self._component_service = component_service
        self._site_service = site_service
        self._party_service = party_service

    def list_lifecycle_statuses(self) -> tuple[MaintenanceLifecycleStatusDescriptor, ...]:
        return tuple(
            MaintenanceLifecycleStatusDescriptor(
                value=status.value,
                label=format_enum_label(status.value),
            )
            for status in MaintenanceLifecycleStatus
        )

    def list_criticalities(self) -> tuple[MaintenanceCriticalityDescriptor, ...]:
        return tuple(
            MaintenanceCriticalityDescriptor(
                value=criticality.value,
                label=format_enum_label(criticality.value),
            )
            for criticality in MaintenanceCriticality
        )

    def list_sites(
        self,
        *,
        active_only: bool | None = None,
    ) -> tuple[MaintenanceSiteOptionDescriptor, ...]:
        if self._site_service is None:
            return ()
        sites = sorted(
            self._site_service.list_sites(active_only=active_only),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "name", "") or "").casefold(),
                str(getattr(row, "site_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_site_option(site) for site in sites)

    def list_manufacturer_parties(
        self,
        *,
        active_only: bool | None = None,
    ) -> tuple[MaintenanceBusinessPartyOptionDescriptor, ...]:
        return self._list_business_parties(
            allowed_types=_MANUFACTURER_PARTY_TYPES,
            active_only=active_only,
        )

    def list_supplier_parties(
        self,
        *,
        active_only: bool | None = None,
    ) -> tuple[MaintenanceBusinessPartyOptionDescriptor, ...]:
        return self._list_business_parties(
            allowed_types=_SUPPLIER_PARTY_TYPES,
            active_only=active_only,
        )

    def list_locations(
        self,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        parent_location_id: str | None = None,
    ) -> tuple[MaintenanceLocationDesktopDto, ...]:
        service = self._require_location_service()
        site_lookup = self._site_lookup(active_only=None)
        locations = sorted(
            service.list_locations(
                active_only=active_only,
                site_id=site_id,
                parent_location_id=parent_location_id,
            ),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "name", "") or "").casefold(),
                str(getattr(row, "location_code", "") or "").casefold(),
            ),
        )
        location_lookup = build_lookup(locations, label_getter=location_label)
        return tuple(
            serialize_location(
                location,
                site_lookup=site_lookup,
                location_lookup=location_lookup,
            )
            for location in locations
        )

    def list_location_options(
        self,
        *,
        active_only: bool | None = True,
        site_id: str | None = None,
    ) -> tuple[MaintenanceLocationOptionDescriptor, ...]:
        return tuple(
            serialize_location_option(row)
            for row in self.list_locations(active_only=active_only, site_id=site_id)
        )

    def create_location(
        self,
        command: MaintenanceLocationCreateCommand,
    ) -> MaintenanceLocationDesktopDto:
        service = self._require_location_service()
        row = service.create_location(
            site_id=command.site_id,
            location_code=command.location_code,
            name=command.name,
            description=command.description,
            parent_location_id=command.parent_location_id,
            location_type=command.location_type,
            criticality=command.criticality,
            status=command.status,
            is_active=command.is_active,
            notes=command.notes,
        )
        return self._serialize_location_by_id(row.id)

    def update_location(
        self,
        command: MaintenanceLocationUpdateCommand,
    ) -> MaintenanceLocationDesktopDto:
        service = self._require_location_service()
        row = service.update_location(
            command.location_id,
            site_id=command.site_id,
            location_code=command.location_code,
            name=command.name,
            description=command.description,
            parent_location_id=command.parent_location_id,
            location_type=command.location_type,
            criticality=command.criticality,
            status=command.status,
            is_active=command.is_active,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return self._serialize_location_by_id(row.id)

    def toggle_location_active(
        self,
        location_id: str,
        *,
        expected_version: int | None = None,
    ) -> MaintenanceLocationDesktopDto:
        service = self._require_location_service()
        row = service.get_location(location_id)
        updated = service.update_location(
            location_id,
            is_active=not bool(getattr(row, "is_active", True)),
            expected_version=expected_version,
        )
        return self._serialize_location_by_id(updated.id)

    def list_systems(
        self,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        location_id: str | None = None,
        parent_system_id: str | None = None,
    ) -> tuple[MaintenanceSystemDesktopDto, ...]:
        service = self._require_system_service()
        site_lookup = self._site_lookup(active_only=None)
        systems = sorted(
            service.list_systems(
                active_only=active_only,
                site_id=site_id,
                location_id=location_id,
                parent_system_id=parent_system_id,
            ),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "name", "") or "").casefold(),
                str(getattr(row, "system_code", "") or "").casefold(),
            ),
        )
        location_lookup = self._location_label_lookup(active_only=None)
        system_lookup = build_lookup(systems, label_getter=system_label)
        return tuple(
            serialize_system(
                system,
                site_lookup=site_lookup,
                location_lookup=location_lookup,
                system_lookup=system_lookup,
            )
            for system in systems
        )

    def list_system_options(
        self,
        *,
        active_only: bool | None = True,
        site_id: str | None = None,
        location_id: str | None = None,
    ) -> tuple[MaintenanceSystemOptionDescriptor, ...]:
        return tuple(
            serialize_system_option(row)
            for row in self.list_systems(
                active_only=active_only,
                site_id=site_id,
                location_id=location_id,
            )
        )

    def create_system(
        self,
        command: MaintenanceSystemCreateCommand,
    ) -> MaintenanceSystemDesktopDto:
        service = self._require_system_service()
        row = service.create_system(
            site_id=command.site_id,
            system_code=command.system_code,
            name=command.name,
            location_id=command.location_id,
            description=command.description,
            parent_system_id=command.parent_system_id,
            system_type=command.system_type,
            criticality=command.criticality,
            status=command.status,
            is_active=command.is_active,
            notes=command.notes,
        )
        return self._serialize_system_by_id(row.id)

    def update_system(
        self,
        command: MaintenanceSystemUpdateCommand,
    ) -> MaintenanceSystemDesktopDto:
        service = self._require_system_service()
        row = service.update_system(
            command.system_id,
            site_id=command.site_id,
            system_code=command.system_code,
            name=command.name,
            location_id=command.location_id,
            description=command.description,
            parent_system_id=command.parent_system_id,
            system_type=command.system_type,
            criticality=command.criticality,
            status=command.status,
            is_active=command.is_active,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return self._serialize_system_by_id(row.id)

    def toggle_system_active(
        self,
        system_id: str,
        *,
        expected_version: int | None = None,
    ) -> MaintenanceSystemDesktopDto:
        service = self._require_system_service()
        row = service.get_system(system_id)
        updated = service.update_system(
            system_id,
            is_active=not bool(getattr(row, "is_active", True)),
            expected_version=expected_version,
        )
        return self._serialize_system_by_id(updated.id)

    def list_assets(
        self,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        location_id: str | None = None,
        system_id: str | None = None,
        parent_asset_id: str | None = None,
        asset_category: str | None = None,
    ) -> tuple[MaintenanceAssetDesktopDto, ...]:
        service = self._require_asset_service()
        site_lookup = self._site_lookup(active_only=None)
        location_lookup = self._location_label_lookup(active_only=None)
        system_lookup = self._system_label_lookup(active_only=None)
        party_lookup = self._party_label_lookup(active_only=None)
        assets = sorted(
            service.list_assets(
                active_only=active_only,
                site_id=site_id,
                location_id=location_id,
                system_id=system_id,
                parent_asset_id=parent_asset_id,
                asset_category=asset_category,
            ),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "name", "") or "").casefold(),
                str(getattr(row, "asset_code", "") or "").casefold(),
            ),
        )
        asset_lookup = build_lookup(assets, label_getter=asset_label)
        return tuple(
            serialize_asset(
                asset,
                site_lookup=site_lookup,
                location_lookup=location_lookup,
                system_lookup=system_lookup,
                asset_lookup=asset_lookup,
                party_lookup=party_lookup,
            )
            for asset in assets
        )

    def list_asset_options(
        self,
        *,
        active_only: bool | None = True,
        site_id: str | None = None,
        location_id: str | None = None,
        system_id: str | None = None,
    ) -> tuple[MaintenanceAssetOptionDescriptor, ...]:
        return tuple(
            serialize_asset_option(row)
            for row in self.list_assets(
                active_only=active_only,
                site_id=site_id,
                location_id=location_id,
                system_id=system_id,
            )
        )

    def create_asset(
        self,
        command: MaintenanceAssetCreateCommand,
    ) -> MaintenanceAssetDesktopDto:
        service = self._require_asset_service()
        row = service.create_asset(
            site_id=command.site_id,
            location_id=command.location_id,
            asset_code=command.asset_code,
            name=command.name,
            system_id=command.system_id,
            description=command.description,
            parent_asset_id=command.parent_asset_id,
            asset_type=command.asset_type,
            asset_category=command.asset_category,
            criticality=command.criticality,
            status=command.status,
            manufacturer_party_id=command.manufacturer_party_id,
            supplier_party_id=command.supplier_party_id,
            model_number=command.model_number,
            serial_number=command.serial_number,
            barcode=command.barcode,
            install_date=command.install_date,
            commission_date=command.commission_date,
            warranty_start=command.warranty_start,
            warranty_end=command.warranty_end,
            expected_life_years=command.expected_life_years,
            replacement_cost=command.replacement_cost,
            maintenance_strategy=command.maintenance_strategy,
            service_level=command.service_level,
            requires_shutdown_for_major_work=command.requires_shutdown_for_major_work,
            is_active=command.is_active,
            notes=command.notes,
        )
        return self._serialize_asset_by_id(row.id)

    def update_asset(
        self,
        command: MaintenanceAssetUpdateCommand,
    ) -> MaintenanceAssetDesktopDto:
        service = self._require_asset_service()
        row = service.update_asset(
            command.asset_id,
            site_id=command.site_id,
            location_id=command.location_id,
            asset_code=command.asset_code,
            name=command.name,
            system_id=command.system_id,
            description=command.description,
            parent_asset_id=command.parent_asset_id,
            asset_type=command.asset_type,
            asset_category=command.asset_category,
            criticality=command.criticality,
            status=command.status,
            manufacturer_party_id=command.manufacturer_party_id,
            supplier_party_id=command.supplier_party_id,
            model_number=command.model_number,
            serial_number=command.serial_number,
            barcode=command.barcode,
            install_date=command.install_date,
            commission_date=command.commission_date,
            warranty_start=command.warranty_start,
            warranty_end=command.warranty_end,
            expected_life_years=command.expected_life_years,
            replacement_cost=command.replacement_cost,
            maintenance_strategy=command.maintenance_strategy,
            service_level=command.service_level,
            requires_shutdown_for_major_work=command.requires_shutdown_for_major_work,
            is_active=command.is_active,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return self._serialize_asset_by_id(row.id)

    def toggle_asset_active(
        self,
        asset_id: str,
        *,
        expected_version: int | None = None,
    ) -> MaintenanceAssetDesktopDto:
        service = self._require_asset_service()
        row = service.get_asset(asset_id)
        updated = service.update_asset(
            asset_id,
            is_active=not bool(getattr(row, "is_active", True)),
            expected_version=expected_version,
        )
        return self._serialize_asset_by_id(updated.id)

    def list_components(
        self,
        *,
        active_only: bool | None = None,
        asset_id: str | None = None,
        parent_component_id: str | None = None,
        component_type: str | None = None,
    ) -> tuple[MaintenanceComponentDesktopDto, ...]:
        service = self._require_component_service()
        asset_lookup = self._asset_label_lookup(active_only=None)
        party_lookup = self._party_label_lookup(active_only=None)
        components = sorted(
            service.list_components(
                active_only=active_only,
                asset_id=asset_id,
                parent_component_id=parent_component_id,
                component_type=component_type,
            ),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "name", "") or "").casefold(),
                str(getattr(row, "component_code", "") or "").casefold(),
            ),
        )
        component_lookup = build_lookup(components, label_getter=component_label)
        return tuple(
            serialize_component(
                component,
                asset_lookup=asset_lookup,
                component_lookup=component_lookup,
                party_lookup=party_lookup,
            )
            for component in components
        )

    def list_component_options(
        self,
        *,
        active_only: bool | None = True,
        asset_id: str | None = None,
    ) -> tuple[MaintenanceComponentOptionDescriptor, ...]:
        return tuple(
            serialize_component_option(row)
            for row in self.list_components(
                active_only=active_only,
                asset_id=asset_id,
            )
        )

    def create_component(
        self,
        command: MaintenanceComponentCreateCommand,
    ) -> MaintenanceComponentDesktopDto:
        service = self._require_component_service()
        row = service.create_component(
            asset_id=command.asset_id,
            component_code=command.component_code,
            name=command.name,
            description=command.description,
            parent_component_id=command.parent_component_id,
            component_type=command.component_type,
            status=command.status,
            manufacturer_party_id=command.manufacturer_party_id,
            supplier_party_id=command.supplier_party_id,
            manufacturer_part_number=command.manufacturer_part_number,
            supplier_part_number=command.supplier_part_number,
            model_number=command.model_number,
            serial_number=command.serial_number,
            install_date=command.install_date,
            warranty_end=command.warranty_end,
            expected_life_hours=command.expected_life_hours,
            expected_life_cycles=command.expected_life_cycles,
            is_critical_component=command.is_critical_component,
            is_active=command.is_active,
            notes=command.notes,
        )
        return self._serialize_component_by_id(row.id)

    def update_component(
        self,
        command: MaintenanceComponentUpdateCommand,
    ) -> MaintenanceComponentDesktopDto:
        service = self._require_component_service()
        row = service.update_component(
            command.component_id,
            asset_id=command.asset_id,
            component_code=command.component_code,
            name=command.name,
            description=command.description,
            parent_component_id=command.parent_component_id,
            component_type=command.component_type,
            status=command.status,
            manufacturer_party_id=command.manufacturer_party_id,
            supplier_party_id=command.supplier_party_id,
            manufacturer_part_number=command.manufacturer_part_number,
            supplier_part_number=command.supplier_part_number,
            model_number=command.model_number,
            serial_number=command.serial_number,
            install_date=command.install_date,
            warranty_end=command.warranty_end,
            expected_life_hours=command.expected_life_hours,
            expected_life_cycles=command.expected_life_cycles,
            is_critical_component=command.is_critical_component,
            is_active=command.is_active,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return self._serialize_component_by_id(row.id)

    def toggle_component_active(
        self,
        component_id: str,
        *,
        expected_version: int | None = None,
    ) -> MaintenanceComponentDesktopDto:
        service = self._require_component_service()
        row = service.get_component(component_id)
        updated = service.update_component(
            component_id,
            is_active=not bool(getattr(row, "is_active", True)),
            expected_version=expected_version,
        )
        return self._serialize_component_by_id(updated.id)

    def _require_location_service(self) -> MaintenanceLocationService:
        if self._location_service is None:
            raise RuntimeError("Maintenance assets desktop API is not connected.")
        return self._location_service

    def _require_system_service(self) -> MaintenanceSystemService:
        if self._system_service is None:
            raise RuntimeError("Maintenance assets desktop API is not connected.")
        return self._system_service

    def _require_asset_service(self) -> MaintenanceAssetService:
        if self._asset_service is None:
            raise RuntimeError("Maintenance assets desktop API is not connected.")
        return self._asset_service

    def _require_component_service(self) -> MaintenanceAssetComponentService:
        if self._component_service is None:
            raise RuntimeError("Maintenance assets desktop API is not connected.")
        return self._component_service

    def _serialize_location_by_id(self, location_id: str) -> MaintenanceLocationDesktopDto:
        row = self._require_location_service().get_location(location_id)
        site_lookup = self._site_lookup(active_only=None)
        location_lookup = self._location_label_lookup(active_only=None)
        return serialize_location(
            row,
            site_lookup=site_lookup,
            location_lookup=location_lookup,
        )

    def _serialize_system_by_id(self, system_id: str) -> MaintenanceSystemDesktopDto:
        row = self._require_system_service().get_system(system_id)
        site_lookup = self._site_lookup(active_only=None)
        location_lookup = self._location_label_lookup(active_only=None)
        system_lookup = self._system_label_lookup(active_only=None)
        return serialize_system(
            row,
            site_lookup=site_lookup,
            location_lookup=location_lookup,
            system_lookup=system_lookup,
        )

    def _serialize_asset_by_id(self, asset_id: str) -> MaintenanceAssetDesktopDto:
        row = self._require_asset_service().get_asset(asset_id)
        site_lookup = self._site_lookup(active_only=None)
        location_lookup = self._location_label_lookup(active_only=None)
        system_lookup = self._system_label_lookup(active_only=None)
        asset_lookup = self._asset_label_lookup(active_only=None)
        party_lookup = self._party_label_lookup(active_only=None)
        return serialize_asset(
            row,
            site_lookup=site_lookup,
            location_lookup=location_lookup,
            system_lookup=system_lookup,
            asset_lookup=asset_lookup,
            party_lookup=party_lookup,
        )

    def _serialize_component_by_id(self, component_id: str) -> MaintenanceComponentDesktopDto:
        row = self._require_component_service().get_component(component_id)
        asset_lookup = self._asset_label_lookup(active_only=None)
        component_lookup = self._component_label_lookup(active_only=None, asset_id=None)
        party_lookup = self._party_label_lookup(active_only=None)
        return serialize_component(
            row,
            asset_lookup=asset_lookup,
            component_lookup=component_lookup,
            party_lookup=party_lookup,
        )

    def _site_lookup(self, *, active_only: bool | None) -> dict[str, str]:
        return {
            option.value: option.label
            for option in self.list_sites(active_only=active_only)
        }

    def _location_label_lookup(self, *, active_only: bool | None) -> dict[str, str]:
        return {
            row.id: location_label(row)
            for row in self._require_location_service().list_locations(active_only=active_only)
        }

    def _system_label_lookup(self, *, active_only: bool | None) -> dict[str, str]:
        return {
            row.id: system_label(row)
            for row in self._require_system_service().list_systems(active_only=active_only)
        }

    def _asset_label_lookup(self, *, active_only: bool | None) -> dict[str, str]:
        return {
            row.id: asset_label(row)
            for row in self._require_asset_service().list_assets(active_only=active_only)
        }

    def _component_label_lookup(
        self,
        *,
        active_only: bool | None,
        asset_id: str | None,
    ) -> dict[str, str]:
        return {
            row.id: component_label(row)
            for row in self._require_component_service().list_components(
                active_only=active_only,
                asset_id=asset_id,
            )
        }

    def _party_label_lookup(self, *, active_only: bool | None) -> dict[str, str]:
        return {
            option.value: option.label
            for option in self._list_business_parties(
                allowed_types=None,
                active_only=active_only,
            )
        }

    def _list_business_parties(
        self,
        *,
        allowed_types: set[PartyType] | None,
        active_only: bool | None,
    ) -> tuple[MaintenanceBusinessPartyOptionDescriptor, ...]:
        if self._party_service is None:
            return ()
        parties = sorted(
            (
                row
                for row in self._party_service.list_parties(active_only=active_only)
                if allowed_types is None or getattr(row, "party_type", None) in allowed_types
            ),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "party_name", "") or "").casefold(),
                str(getattr(row, "party_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_business_party_option(party) for party in parties)


def build_maintenance_assets_desktop_api(
    *,
    location_service: MaintenanceLocationService | None = None,
    system_service: MaintenanceSystemService | None = None,
    asset_service: MaintenanceAssetService | None = None,
    component_service: MaintenanceAssetComponentService | None = None,
    site_service: SiteService | None = None,
    party_service: PartyService | None = None,
) -> MaintenanceAssetsDesktopApi:
    return MaintenanceAssetsDesktopApi(
        location_service=location_service,
        system_service=system_service,
        asset_service=asset_service,
        component_service=component_service,
        site_service=site_service,
        party_service=party_service,
    )


__all__ = [
    "MaintenanceAssetsDesktopApi",
    "build_maintenance_assets_desktop_api",
]
