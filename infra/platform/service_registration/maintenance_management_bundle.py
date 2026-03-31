from __future__ import annotations

from dataclasses import dataclass

from core.platform.access import ScopedRolePolicy
from core.modules.maintenance_management import (
    MaintenanceAssetService,
    MaintenanceAssetComponentService,
    MaintenanceLocationService,
    MaintenanceRuntimeContractCatalogService,
    MaintenanceSystemService,
)
from core.modules.maintenance_management.access import (
    MAINTENANCE_SCOPE_ROLE_CHOICES,
    normalize_maintenance_scope_role,
    resolve_maintenance_scope_permissions,
)
from infra.modules.maintenance_management.db import (
    SqlAlchemyMaintenanceAssetRepository,
    SqlAlchemyMaintenanceAssetComponentRepository,
    SqlAlchemyMaintenanceLocationRepository,
    SqlAlchemyMaintenanceSystemRepository,
)
from infra.platform.service_registration.platform_bundle import PlatformServiceBundle


@dataclass(frozen=True)
class MaintenanceManagementServiceBundle:
    maintenance_runtime_contract_catalog_service: MaintenanceRuntimeContractCatalogService
    maintenance_asset_service: MaintenanceAssetService
    maintenance_asset_component_service: MaintenanceAssetComponentService
    maintenance_location_service: MaintenanceLocationService
    maintenance_system_service: MaintenanceSystemService


def build_maintenance_management_service_bundle(
    platform_services: PlatformServiceBundle,
) -> MaintenanceManagementServiceBundle:
    location_repo = SqlAlchemyMaintenanceLocationRepository(platform_services.session)
    system_repo = SqlAlchemyMaintenanceSystemRepository(platform_services.session)
    asset_repo = SqlAlchemyMaintenanceAssetRepository(platform_services.session)
    component_repo = SqlAlchemyMaintenanceAssetComponentRepository(platform_services.session)
    platform_services.department_service.register_location_reference_repository(location_repo)
    platform_services.access_service.register_scope_policy(
        ScopedRolePolicy(
            scope_type="maintenance",
            role_choices=MAINTENANCE_SCOPE_ROLE_CHOICES,
            normalize_role=normalize_maintenance_scope_role,
            resolve_permissions=resolve_maintenance_scope_permissions,
        )
    )
    platform_services.access_service.register_scope_exists_resolver(
        "maintenance",
        lambda entity_id: (
            location_repo.get(entity_id) is not None
            or system_repo.get(entity_id) is not None
            or asset_repo.get(entity_id) is not None
        ),
    )
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
    maintenance_asset_component_service = MaintenanceAssetComponentService(
        platform_services.session,
        component_repo,
        asset_repo=asset_repo,
        organization_repo=platform_services.organization_repo,
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
        maintenance_asset_component_service=maintenance_asset_component_service,
        maintenance_location_service=maintenance_location_service,
        maintenance_system_service=maintenance_system_service,
    )


__all__ = [
    "MaintenanceManagementServiceBundle",
    "build_maintenance_management_service_bundle",
]
