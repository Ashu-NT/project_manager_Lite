from __future__ import annotations

from dataclasses import dataclass

from core.modules.maintenance_management import (
    MaintenanceAssetService,
    MaintenanceLocationService,
    MaintenanceRuntimeContractCatalogService,
    MaintenanceSystemService,
)
from infra.modules.maintenance_management.db import (
    SqlAlchemyMaintenanceAssetRepository,
    SqlAlchemyMaintenanceLocationRepository,
    SqlAlchemyMaintenanceSystemRepository,
)
from infra.platform.service_registration.platform_bundle import PlatformServiceBundle


@dataclass(frozen=True)
class MaintenanceManagementServiceBundle:
    maintenance_runtime_contract_catalog_service: MaintenanceRuntimeContractCatalogService
    maintenance_asset_service: MaintenanceAssetService
    maintenance_location_service: MaintenanceLocationService
    maintenance_system_service: MaintenanceSystemService


def build_maintenance_management_service_bundle(
    platform_services: PlatformServiceBundle,
) -> MaintenanceManagementServiceBundle:
    location_repo = SqlAlchemyMaintenanceLocationRepository(platform_services.session)
    system_repo = SqlAlchemyMaintenanceSystemRepository(platform_services.session)
    asset_repo = SqlAlchemyMaintenanceAssetRepository(platform_services.session)
    platform_services.department_service.register_location_reference_repository(location_repo)
    maintenance_runtime_contract_catalog_service = MaintenanceRuntimeContractCatalogService()
    maintenance_asset_service = MaintenanceAssetService(
        platform_services.session,
        asset_repo,
        organization_repo=platform_services.organization_repo,
        site_repo=platform_services.site_repo,
        location_repo=location_repo,
        system_repo=system_repo,
        party_repo=platform_services.party_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_location_service = MaintenanceLocationService(
        platform_services.session,
        location_repo,
        organization_repo=platform_services.organization_repo,
        site_repo=platform_services.site_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    maintenance_system_service = MaintenanceSystemService(
        platform_services.session,
        system_repo,
        organization_repo=platform_services.organization_repo,
        site_repo=platform_services.site_repo,
        location_repo=location_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    return MaintenanceManagementServiceBundle(
        maintenance_runtime_contract_catalog_service=maintenance_runtime_contract_catalog_service,
        maintenance_asset_service=maintenance_asset_service,
        maintenance_location_service=maintenance_location_service,
        maintenance_system_service=maintenance_system_service,
    )


__all__ = [
    "MaintenanceManagementServiceBundle",
    "build_maintenance_management_service_bundle",
]
