from __future__ import annotations

from src.core.modules.maintenance import (
    MaintenanceAssetComponentService,
)
from src.core.modules.maintenance.domain import (
    MaintenanceAsset,
    MaintenanceAssetComponent,
    MaintenanceLocation,
)
from src.core.modules.maintenance.contracts.repositories import (
    MaintenanceAssetComponentRepository,
    MaintenanceAssetRepository,
    MaintenanceLocationRepository,
)
from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.shared.events.domain_events import domain_events
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.master_data.site import Site
from src.core.platform.domain.master_data.party import Party, PartyType
from src.core.platform.contract.repositories.master_data.party.contracts import PartyRepository


class _OrgRepo(OrganizationRepository):
    def __init__(self, organization: Organization) -> None:
        self.organization = organization

    def add(self, organization: Organization) -> None:
        self.organization = organization

    def update(self, organization: Organization) -> None:
        self.organization = organization

    def get(self, organization_id: str):
        return self.organization if self.organization.id == organization_id else None

    def get_by_code(self, organization_code: str):
        return self.organization if self.organization.organization_code == organization_code else None

    def get_active(self):
        return self.organization

    def list_all(self, *, active_only=None):
        rows = [self.organization]
        if active_only is None:
            return rows
        return [row for row in rows if row.is_active == bool(active_only)]

    def get_for_tenant(self, organization_id: str, tenant_id: str):
        if self.organization.tenant_id != tenant_id:
            return None
        return self.get(organization_id)

    def get_by_code_for_tenant(self, organization_code: str, tenant_id: str):
        if self.organization.tenant_id != tenant_id:
            return None
        return self.get_by_code(organization_code)

    def get_active_for_tenant(self, tenant_id: str):
        return self.organization if self.organization.tenant_id == tenant_id else None

    def list_for_tenant(self, tenant_id: str, *, active_only=None):
        rows = [self.organization] if self.organization.tenant_id == tenant_id else []
        if active_only is None:
            return rows
        return [row for row in rows if row.is_active == bool(active_only)]


class _TenantContext:
    def __init__(self, organization: Organization) -> None:
        self.organization = organization

    def require_context(self, *, operation_label: str):
        return type(
            "TenantContext",
            (),
            {"organization_id": self.organization.id, "organization": self.organization},
        )()

    def require_organization_context(self, *, operation_label: str):
        return self.require_context(operation_label=operation_label)

    def require_active_organization_id(self, *, operation_label: str) -> str:
        return self.organization.id

    def get_active_organization_id(self) -> str:
        return self.organization.id

    def get_active_tenant_id(self) -> str | None:
        return self.organization.tenant_id


class _AssetRepo(MaintenanceAssetRepository):
    def __init__(self) -> None:
        self._rows = {}

    def add(self, asset) -> None:
        self._rows[asset.id] = asset

    def update(self, asset) -> None:
        self._rows[asset.id] = asset

    def get(self, asset_id: str):
        return self._rows.get(asset_id)

    def get_by_code(self, organization_id: str, asset_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.asset_code == asset_code:
                return row
        return None

    def list_for_organization(self, organization_id: str, *, active_only=None, site_id=None, location_id=None, system_id=None, parent_asset_id=None, asset_category=None):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        if site_id is not None:
            rows = [row for row in rows if row.site_id == site_id]
        if location_id is not None:
            rows = [row for row in rows if row.location_id == location_id]
        if system_id is not None:
            rows = [row for row in rows if row.system_id == system_id]
        if parent_asset_id is not None:
            rows = [row for row in rows if row.parent_asset_id == parent_asset_id]
        if asset_category is not None:
            rows = [row for row in rows if row.asset_category == asset_category]
        return rows


class _ComponentRepo(MaintenanceAssetComponentRepository):
    def __init__(self) -> None:
        self._rows = {}

    def add(self, component) -> None:
        self._rows[component.id] = component

    def update(self, component) -> None:
        self._rows[component.id] = component

    def get(self, component_id: str):
        return self._rows.get(component_id)

    def get_by_code(self, organization_id: str, component_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.component_code == component_code:
                return row
        return None

    def list_for_organization(self, organization_id: str, *, active_only=None, asset_id=None, parent_component_id=None, component_type=None):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        if asset_id is not None:
            rows = [row for row in rows if row.asset_id == asset_id]
        if parent_component_id is not None:
            rows = [row for row in rows if row.parent_component_id == parent_component_id]
        if component_type is not None:
            rows = [row for row in rows if row.component_type == component_type]
        return rows


class _PartyRepo(PartyRepository):
    def __init__(self, parties: list[Party] | None = None) -> None:
        self._rows = {party.id: party for party in parties or []}

    def add(self, party: Party) -> None:
        self._rows[party.id] = party

    def update(self, party: Party) -> None:
        self._rows[party.id] = party

    def get(self, party_id: str):
        return self._rows.get(party_id)

    def get_by_code(self, organization_id: str, party_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.party_code == party_code:
                return row
        return None

    def list_for_organization(self, organization_id: str, *, active_only=None):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is None:
            return rows
        return [row for row in rows if row.is_active == bool(active_only)]


def _user_session() -> UserSessionContext:
    user_session = UserSessionContext()
    user_session.set_principal(
        UserSessionPrincipal(
            user_id="u1",
            username="maintenance.admin",
            display_name="Maintenance Admin",
            role_names=frozenset({"maintenance_admin"}),
            permissions=frozenset({"maintenance.read", "maintenance.manage"}),
        )
    )
    return user_session


def test_maintenance_asset_component_service_creates_components_and_emits_domain_events(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    asset_repo = _AssetRepo()
    component_repo = _ComponentRepo()
    supplier = Party.create(
        organization_id=organization.id,
        party_code="SUP-COMP",
        party_name="Component Supplier",
        party_type=PartyType.SUPPLIER,
    )
    location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-A",
        name="Area A",
    )
    asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        asset_code="PUMP-001",
        name="Process Pump",
    )
    asset_repo.add(asset)
    service = MaintenanceAssetComponentService(
        session,
        component_repo,
        asset_repo=asset_repo,
        organization_repo=_OrgRepo(organization),
        party_repo=_PartyRepo([supplier]),
        tenant_context_service=_TenantContext(organization),
        user_session=_user_session(),
    )
    captured = []
    domain_events.domain_changed.connect(captured.append)

    component = service.create_component(
        asset_id=asset.id,
        component_code="seal-001",
        name="Seal Cartridge",
        component_type="SEAL",
        supplier_party_id=supplier.id,
        expected_life_hours=12000,
        is_critical_component=True,
    )

    assert component.component_code == "SEAL-001"
    assert component.asset_id == asset.id
    assert component.component_type == "SEAL"
    assert component.is_critical_component is True
    assert service.find_component_by_code("SEAL-001").id == component.id
    assert service.search_components(search_text="seal")[0].id == component.id
    assert captured[-1].entity_type == "maintenance_asset_component"
    assert captured[-1].source_event == "maintenance_asset_components_changed"


def test_maintenance_asset_component_service_rejects_parent_from_other_asset(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-A",
        name="Area A",
    )
    asset_repo = _AssetRepo()
    first_asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        asset_code="ASSET-A",
        name="Asset A",
    )
    second_asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        asset_code="ASSET-B",
        name="Asset B",
    )
    asset_repo.add(first_asset)
    asset_repo.add(second_asset)
    component_repo = _ComponentRepo()
    parent = MaintenanceAssetComponent.create(
        organization_id=organization.id,
        asset_id=first_asset.id,
        component_code="COMP-A",
        name="Component A",
    )
    component_repo.add(parent)
    service = MaintenanceAssetComponentService(
        session,
        component_repo,
        asset_repo=asset_repo,
        organization_repo=_OrgRepo(organization),
        party_repo=_PartyRepo(),
        tenant_context_service=_TenantContext(organization),
        user_session=_user_session(),
    )

    try:
        service.create_component(
            asset_id=second_asset.id,
            component_code="COMP-B",
            name="Component B",
            parent_component_id=parent.id,
        )
    except ValidationError as exc:
        assert exc.code == "MAINTENANCE_COMPONENT_ASSET_MISMATCH"
    else:
        raise AssertionError("Expected maintenance component asset mismatch validation error.")
