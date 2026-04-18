from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.modules.maintenance_management.domain import (
    MaintenanceAsset,
    MaintenanceLocation,
    MaintenanceSystem,
    MaintenanceWorkOrder,
    MaintenanceWorkOrderStatus,
)
from core.modules.maintenance_management.reliability_domain import (
    MaintenanceDowntimeEvent,
    MaintenanceFailureCode,
    MaintenanceFailureCodeType,
)
from core.modules.maintenance_management.services import MaintenanceReliabilityService
from src.core.platform.auth.domain.session import UserSessionContext, UserSessionPrincipal
from core.platform.common.exceptions import BusinessRuleError
from src.core.platform.org.domain import Organization, Site


class _OrgRepo:
    def __init__(self, organization: Organization) -> None:
        self.organization = organization

    def get_active(self):
        return self.organization


class _SiteRepo:
    def __init__(self, rows: list[Site]) -> None:
        self._rows = {row.id: row for row in rows}

    def get(self, site_id: str):
        return self._rows.get(site_id)


class _LocationRepo:
    def __init__(self, rows: list[MaintenanceLocation]) -> None:
        self._rows = {row.id: row for row in rows}

    def get(self, location_id: str):
        return self._rows.get(location_id)

    def list_for_organization(self, organization_id: str, **_kwargs):
        return [row for row in self._rows.values() if row.organization_id == organization_id]


class _SystemRepo:
    def __init__(self, rows: list[MaintenanceSystem]) -> None:
        self._rows = {row.id: row for row in rows}

    def get(self, system_id: str):
        return self._rows.get(system_id)

    def list_for_organization(self, organization_id: str, **_kwargs):
        return [row for row in self._rows.values() if row.organization_id == organization_id]


class _AssetRepo:
    def __init__(self, rows: list[MaintenanceAsset]) -> None:
        self._rows = {row.id: row for row in rows}

    def get(self, asset_id: str):
        return self._rows.get(asset_id)

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only=None,
        site_id=None,
        location_id=None,
        system_id=None,
        **_kwargs,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        if site_id is not None:
            rows = [row for row in rows if row.site_id == site_id]
        if location_id is not None:
            rows = [row for row in rows if row.location_id == location_id]
        if system_id is not None:
            rows = [row for row in rows if row.system_id == system_id]
        return rows


class _ComponentRepo:
    def get(self, _component_id: str):
        return None


class _FailureCodeRepo:
    def __init__(self, rows: list[MaintenanceFailureCode]) -> None:
        self._rows = {row.id: row for row in rows}

    def get_by_code(self, organization_id: str, failure_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.failure_code == failure_code:
                return row
        return None

    def list_for_organization(self, organization_id: str, **_kwargs):
        return [row for row in self._rows.values() if row.organization_id == organization_id]


class _WorkOrderRepo:
    def __init__(self, rows: list[MaintenanceWorkOrder]) -> None:
        self._rows = {row.id: row for row in rows}

    def list_for_organization(
        self,
        organization_id: str,
        *,
        site_id=None,
        asset_id=None,
        component_id=None,
        system_id=None,
        location_id=None,
        **_kwargs,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if site_id is not None:
            rows = [row for row in rows if row.site_id == site_id]
        if asset_id is not None:
            rows = [row for row in rows if row.asset_id == asset_id]
        if component_id is not None:
            rows = [row for row in rows if row.component_id == component_id]
        if system_id is not None:
            rows = [row for row in rows if row.system_id == system_id]
        if location_id is not None:
            rows = [row for row in rows if row.location_id == location_id]
        return rows


class _DowntimeRepo:
    def __init__(self, rows: list[MaintenanceDowntimeEvent]) -> None:
        self._rows = {row.id: row for row in rows}

    def list_for_organization(
        self,
        organization_id: str,
        *,
        asset_id=None,
        system_id=None,
        started_from=None,
        **_kwargs,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if asset_id is not None:
            rows = [row for row in rows if row.asset_id == asset_id]
        if system_id is not None:
            rows = [row for row in rows if row.system_id == system_id]
        if started_from is not None:
            rows = [row for row in rows if row.started_at is not None and row.started_at >= started_from]
        return rows


def _maintenance_session(*, report_view: bool = True) -> UserSessionContext:
    permissions = {"maintenance.read"}
    if report_view:
        permissions.add("report.view")
    session = UserSessionContext()
    session.set_principal(
        UserSessionPrincipal(
            user_id="maint-user",
            username="maint",
            display_name="Maint User",
            role_names=frozenset({"maintenance_manager"}),
            permissions=frozenset(permissions),
        )
    )
    return session


def _build_service(*, report_view: bool = True) -> tuple[MaintenanceReliabilityService, MaintenanceAsset]:
    organization = Organization.create("MNT", "Maintenance Org")
    site = Site.create(organization.id, "PLANT-1", "Plant 1")
    location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-A",
        name="Area A",
    )
    system = MaintenanceSystem.create(
        organization_id=organization.id,
        site_id=site.id,
        system_code="SYS-PUMP",
        name="Pump Train",
        location_id=location.id,
    )
    asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        system_id=system.id,
        asset_code="P-100",
        name="Process Pump",
    )
    symptom = MaintenanceFailureCode.create(
        organization_id=organization.id,
        failure_code="SEAL-LEAK",
        name="Seal Leak",
        code_type=MaintenanceFailureCodeType.SYMPTOM,
    )
    cause_a = MaintenanceFailureCode.create(
        organization_id=organization.id,
        failure_code="MISALIGNMENT",
        name="Misalignment",
        code_type=MaintenanceFailureCodeType.CAUSE,
    )
    cause_b = MaintenanceFailureCode.create(
        organization_id=organization.id,
        failure_code="LUBE-LOSS",
        name="Lubrication Loss",
        code_type=MaintenanceFailureCodeType.CAUSE,
    )

    now = datetime.now(timezone.utc)
    work_orders: list[MaintenanceWorkOrder] = []
    occurrences = [
        (40, 2, MaintenanceWorkOrderStatus.CLOSED, "MISALIGNMENT", 120),
        (25, 1, MaintenanceWorkOrderStatus.CLOSED, "MISALIGNMENT", 60),
        (7, 0, MaintenanceWorkOrderStatus.IN_PROGRESS, "MISALIGNMENT", 30),
        (15, 1, MaintenanceWorkOrderStatus.CLOSED, "LUBE-LOSS", 45),
    ]
    for index, (days_ago, repair_hours, status, root_cause_code, downtime_minutes) in enumerate(occurrences, start=1):
        start_at = now - timedelta(days=days_ago, hours=repair_hours)
        end_at = start_at + timedelta(hours=repair_hours)
        work_order = MaintenanceWorkOrder.create(
            organization_id=organization.id,
            site_id=site.id,
            work_order_code=f"WO-{index}",
            work_order_type="CORRECTIVE",
            source_type="MANUAL",
            asset_id=asset.id,
            system_id=system.id,
            location_id=location.id,
            title=f"Pump repair {index}",
        )
        work_order.failure_code = symptom.failure_code
        work_order.root_cause_code = root_cause_code
        work_order.downtime_minutes = downtime_minutes
        work_order.actual_start = start_at
        work_order.actual_end = end_at if status != MaintenanceWorkOrderStatus.IN_PROGRESS else None
        work_order.closed_at = end_at if status == MaintenanceWorkOrderStatus.CLOSED else None
        work_order.planned_end = now - timedelta(days=1) if status == MaintenanceWorkOrderStatus.IN_PROGRESS else end_at
        work_order.status = status
        work_orders.append(work_order)

    open_downtime = MaintenanceDowntimeEvent.create(
        organization_id=organization.id,
        work_order_id=work_orders[2].id,
        asset_id=asset.id,
        system_id=system.id,
        started_at=now - timedelta(hours=3),
        downtime_type="UNPLANNED",
        reason_code=symptom.failure_code,
        impact_notes="Open event",
    )
    closed_downtime = MaintenanceDowntimeEvent.create(
        organization_id=organization.id,
        work_order_id=work_orders[0].id,
        asset_id=asset.id,
        system_id=system.id,
        started_at=now - timedelta(days=40, hours=2),
        ended_at=now - timedelta(days=40),
        duration_minutes=120,
        downtime_type="UNPLANNED",
        reason_code=symptom.failure_code,
        impact_notes="Closed event",
    )

    service = MaintenanceReliabilityService(
        None,
        organization_repo=_OrgRepo(organization),
        site_repo=_SiteRepo([site]),
        asset_repo=_AssetRepo([asset]),
        component_repo=_ComponentRepo(),
        location_repo=_LocationRepo([location]),
        system_repo=_SystemRepo([system]),
        work_order_repo=_WorkOrderRepo(work_orders),
        failure_code_repo=_FailureCodeRepo([symptom, cause_a, cause_b]),
        downtime_event_repo=_DowntimeRepo([open_downtime, closed_downtime]),
        user_session=_maintenance_session(report_view=report_view),
    )
    return service, asset


def test_reliability_service_builds_dashboard_and_root_cause_helpers() -> None:
    service, asset = _build_service()

    dashboard = service.build_reliability_dashboard(asset_id=asset.id, days=90)
    suggestions = service.suggest_root_causes(failure_code="seal-leak", asset_id=asset.id)

    summary = {metric.label: metric.value for metric in dashboard.summary}
    assert summary["Open work orders"] == 1
    assert summary["Overdue work orders"] == 1
    assert summary["Open downtime events"] == 1
    assert dashboard.top_root_causes[0].root_cause_code == "MISALIGNMENT"
    assert dashboard.top_root_causes[0].work_order_count == 3
    assert dashboard.recurring_failures[0].anchor_code == "P-100"
    assert dashboard.recurring_failures[0].occurrence_count == 3
    assert suggestions[0].root_cause_code == "MISALIGNMENT"
    assert suggestions[0].match_scope == "asset"


def test_reliability_service_requires_report_view_permission() -> None:
    service, asset = _build_service(report_view=False)

    with pytest.raises(BusinessRuleError):
        service.build_reliability_dashboard(asset_id=asset.id, days=30)
