from __future__ import annotations

from core.modules.maintenance_management.domain import (
    MaintenanceAsset,
    MaintenanceDowntimeEvent,
    MaintenanceFailureCode,
    MaintenanceWorkOrder,
)
from core.modules.maintenance_management.interfaces import (
    MaintenanceAssetComponentRepository,
    MaintenanceAssetRepository,
    MaintenanceDowntimeEventRepository,
    MaintenanceFailureCodeRepository,
    MaintenanceSystemRepository,
    MaintenanceWorkOrderRepository,
)
from core.modules.maintenance_management.services import (
    MaintenanceDowntimeEventService,
    MaintenanceFailureCodeService,
)
from src.core.platform.auth.domain.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.org.domain import Organization


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


class _FailureCodeRepo(MaintenanceFailureCodeRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenanceFailureCode] = {}

    def add(self, failure_code: MaintenanceFailureCode) -> None:
        self._rows[failure_code.id] = failure_code

    def update(self, failure_code: MaintenanceFailureCode) -> None:
        failure_code.version += 1
        self._rows[failure_code.id] = failure_code

    def get(self, failure_code_id: str):
        return self._rows.get(failure_code_id)

    def get_by_code(self, organization_id: str, failure_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.failure_code == failure_code:
                return row
        return None

    def list_for_organization(self, organization_id: str, *, active_only=None, code_type=None, parent_code_id=None):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        if code_type is not None:
            rows = [row for row in rows if row.code_type == code_type]
        if parent_code_id is not None:
            rows = [row for row in rows if row.parent_code_id == parent_code_id]
        return sorted(rows, key=lambda row: (row.code_type.value, row.failure_code))


class _DowntimeRepo(MaintenanceDowntimeEventRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenanceDowntimeEvent] = {}

    def add(self, downtime_event: MaintenanceDowntimeEvent) -> None:
        self._rows[downtime_event.id] = downtime_event

    def update(self, downtime_event: MaintenanceDowntimeEvent) -> None:
        downtime_event.version += 1
        self._rows[downtime_event.id] = downtime_event

    def get(self, downtime_event_id: str):
        return self._rows.get(downtime_event_id)

    def list_for_organization(
        self,
        organization_id: str,
        *,
        work_order_id=None,
        asset_id=None,
        system_id=None,
        downtime_type=None,
        reason_code=None,
        open_only=None,
        started_from=None,
        started_to=None,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if work_order_id is not None:
            rows = [row for row in rows if row.work_order_id == work_order_id]
        if asset_id is not None:
            rows = [row for row in rows if row.asset_id == asset_id]
        if system_id is not None:
            rows = [row for row in rows if row.system_id == system_id]
        if downtime_type is not None:
            rows = [row for row in rows if row.downtime_type == downtime_type]
        if reason_code is not None:
            rows = [row for row in rows if row.reason_code == reason_code]
        if open_only is True:
            rows = [row for row in rows if row.ended_at is None]
        elif open_only is False:
            rows = [row for row in rows if row.ended_at is not None]
        if started_from is not None:
            rows = [row for row in rows if row.started_at is not None and row.started_at >= started_from]
        if started_to is not None:
            rows = [row for row in rows if row.started_at is not None and row.started_at <= started_to]
        return sorted(rows, key=lambda row: row.started_at, reverse=True)


class _WorkOrderRepo(MaintenanceWorkOrderRepository):
    def __init__(self, rows: list[MaintenanceWorkOrder]) -> None:
        self._rows = {row.id: row for row in rows}

    def add(self, work_order: MaintenanceWorkOrder) -> None:
        self._rows[work_order.id] = work_order

    def update(self, work_order: MaintenanceWorkOrder) -> None:
        work_order.version += 1
        self._rows[work_order.id] = work_order

    def get(self, work_order_id: str):
        return self._rows.get(work_order_id)

    def get_by_code(self, organization_id: str, work_order_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.work_order_code == work_order_code:
                return row
        return None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        site_id=None,
        asset_id=None,
        component_id=None,
        system_id=None,
        location_id=None,
        status=None,
        priority=None,
        assigned_employee_id=None,
        assigned_team_id=None,
        planner_user_id=None,
        supervisor_user_id=None,
        work_order_type=None,
        is_preventive=None,
        is_emergency=None,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if asset_id is not None:
            rows = [row for row in rows if row.asset_id == asset_id]
        if system_id is not None:
            rows = [row for row in rows if row.system_id == system_id]
        return rows


class _AssetRepo(MaintenanceAssetRepository):
    def __init__(self, rows: list[MaintenanceAsset]) -> None:
        self._rows = {row.id: row for row in rows}

    def add(self, asset: MaintenanceAsset) -> None:
        self._rows[asset.id] = asset

    def update(self, asset: MaintenanceAsset) -> None:
        self._rows[asset.id] = asset

    def get(self, asset_id: str):
        return self._rows.get(asset_id)

    def get_by_code(self, organization_id: str, asset_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.asset_code == asset_code:
                return row
        return None

    def list_for_organization(self, organization_id: str, **kwargs):
        return [row for row in self._rows.values() if row.organization_id == organization_id]


class _EmptyComponentRepo(MaintenanceAssetComponentRepository):
    def add(self, component) -> None:
        raise NotImplementedError

    def update(self, component) -> None:
        raise NotImplementedError

    def get(self, component_id: str):
        return None

    def get_by_code(self, organization_id: str, component_code: str):
        return None

    def list_for_organization(self, organization_id: str, **kwargs):
        return []


class _EmptySystemRepo(MaintenanceSystemRepository):
    def add(self, system) -> None:
        raise NotImplementedError

    def update(self, system) -> None:
        raise NotImplementedError

    def get(self, system_id: str):
        return None

    def get_by_code(self, organization_id: str, system_code: str):
        return None

    def list_for_organization(self, organization_id: str, **kwargs):
        return []


def _maintenance_session() -> UserSessionContext:
    session = UserSessionContext()
    session.set_principal(
        UserSessionPrincipal(
            user_id="user-maint",
            username="maint",
            display_name="Maint User",
            role_names=frozenset({"admin"}),
            permissions=frozenset({"maintenance.read", "maintenance.manage"}),
        )
    )
    return session


def test_failure_code_service_creates_same_type_hierarchy(session) -> None:
    organization = Organization.create("MNT", "Maintenance Org")
    service = MaintenanceFailureCodeService(
        session,
        _FailureCodeRepo(),
        organization_repo=_OrgRepo(organization),
        user_session=_maintenance_session(),
    )

    symptom = service.create_failure_code(
        failure_code="seal-leak",
        name="Seal Leak",
        code_type="symptom",
    )
    child = service.create_failure_code(
        failure_code="seal-leak-major",
        name="Seal Leak Major",
        code_type="symptom",
        parent_code_id=symptom.id,
    )
    listed = service.list_failure_codes(code_type="symptom")

    assert child.parent_code_id == symptom.id
    assert [row.failure_code for row in listed] == ["SEAL-LEAK", "SEAL-LEAK-MAJOR"]


def test_downtime_event_service_tracks_duration_and_syncs_work_order(session) -> None:
    organization = Organization.create("MNT", "Maintenance Org")
    asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id="site-1",
        location_id="loc-1",
        asset_code="asset-1",
        name="Asset 1",
    )
    work_order = MaintenanceWorkOrder.create(
        organization_id=organization.id,
        site_id="site-1",
        work_order_code="wo-1",
        work_order_type="CORRECTIVE",
        source_type="MANUAL",
        asset_id=asset.id,
    )
    work_order_repo = _WorkOrderRepo([work_order])
    service = MaintenanceDowntimeEventService(
        session,
        _DowntimeRepo(),
        organization_repo=_OrgRepo(organization),
        work_order_repo=work_order_repo,
        asset_repo=_AssetRepo([asset]),
        component_repo=_EmptyComponentRepo(),
        system_repo=_EmptySystemRepo(),
        user_session=_maintenance_session(),
    )

    event = service.create_downtime_event(
        work_order_id=work_order.id,
        started_at="2026-04-03T08:00:00+00:00",
        ended_at="2026-04-03T09:15:00+00:00",
        downtime_type="unplanned",
        reason_code="SEAL-LEAK",
        impact_notes="Unit stopped for seal replacement.",
    )
    reloaded = service.get_downtime_event(event.id)
    synced_work_order = work_order_repo.get(work_order.id)

    assert reloaded.duration_minutes == 75
    assert synced_work_order is not None
    assert synced_work_order.downtime_minutes == 75
