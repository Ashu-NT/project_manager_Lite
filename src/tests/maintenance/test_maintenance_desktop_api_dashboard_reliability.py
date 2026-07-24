from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.modules.maintenance.api.desktop import (
    MaintenanceAssetCreateCommand,
    MaintenanceDashboardSnapshotDescriptor,
    MaintenanceLocationCreateCommand,
    MaintenanceReliabilitySnapshotDescriptor,
    MaintenanceSystemCreateCommand,
    MaintenanceWorkOrderCreateCommand,
    MaintenanceWorkOrderUpdateCommand,
    build_maintenance_assets_desktop_api,
    build_maintenance_dashboard_desktop_api,
    build_maintenance_reliability_desktop_api,
    build_maintenance_work_orders_desktop_api,
)
from src.core.platform.party.domain import PartyType


def _create_shared_maintenance_references(services):
    site = services["site_service"].create_site(
        site_code="MNT-HQ",
        name="Maintenance HQ",
        city="Berlin",
        currency_code="EUR",
    )
    manufacturer = services["party_service"].create_party(
        party_code="MFR-001",
        party_name="Rotor Works GmbH",
        party_type=PartyType.MANUFACTURER,
        city="Hamburg",
        country="DE",
    )
    supplier = services["party_service"].create_party(
        party_code="SUP-001",
        party_name="Field Supply GmbH",
        party_type=PartyType.SUPPLIER,
        city="Munich",
        country="DE",
    )
    return site, manufacturer, supplier


def _build_assets_api(services):
    return build_maintenance_assets_desktop_api(
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
        asset_service=services["maintenance_asset_service"],
        component_service=services["maintenance_asset_component_service"],
        site_service=services["site_service"],
        party_service=services["party_service"],
    )


def _build_work_orders_api(services):
    return build_maintenance_work_orders_desktop_api(
        work_order_service=services["maintenance_work_order_service"],
        work_request_service=services["maintenance_work_request_service"],
        site_service=services["site_service"],
        employee_service=services["employee_service"],
        party_service=services["party_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
        asset_service=services["maintenance_asset_service"],
        component_service=services["maintenance_asset_component_service"],
    )


def _build_dashboard_api(services):
    return build_maintenance_dashboard_desktop_api(
        reliability_service=services["maintenance_reliability_service"],
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
    )


def _build_reliability_api(services):
    return build_maintenance_reliability_desktop_api(
        reliability_service=services["maintenance_reliability_service"],
        failure_code_service=services["maintenance_failure_code_service"],
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
    )


def _create_maintenance_reliability_context(services):
    site, manufacturer, supplier = _create_shared_maintenance_references(services)
    assets_api = _build_assets_api(services)
    work_orders_api = _build_work_orders_api(services)
    now = datetime.now(timezone.utc)

    location = assets_api.create_location(
        MaintenanceLocationCreateCommand(
            site_id=site.id,
            location_code="LOC-REL",
            name="Reliability Area",
            location_type="PRODUCTION",
        )
    )
    system = assets_api.create_system(
        MaintenanceSystemCreateCommand(
            site_id=site.id,
            location_id=location.id,
            system_code="SYS-REL",
            name="Reliability Line",
            system_type="LINE",
        )
    )
    asset = assets_api.create_asset(
        MaintenanceAssetCreateCommand(
            site_id=site.id,
            location_id=location.id,
            system_id=system.id,
            asset_code="AST-REL",
            name="Pump 501",
            manufacturer_party_id=manufacturer.id,
            supplier_party_id=supplier.id,
        )
    )
    open_order = work_orders_api.create_work_order(
        MaintenanceWorkOrderCreateCommand(
            site_id=site.id,
            work_order_code="WO-REL-OPEN",
            work_order_type="CORRECTIVE",
            asset_id=asset.id,
            system_id=system.id,
            location_id=location.id,
            title="Open backlog repair",
            description="Still waiting in the active backlog.",
            priority="HIGH",
        )
    )
    open_order = work_orders_api.update_work_order(
        MaintenanceWorkOrderUpdateCommand(
            work_order_id=open_order.id,
            status="PLANNED",
            expected_version=open_order.version,
        )
    )
    symptom = services["maintenance_failure_code_service"].create_failure_code(
        failure_code="REL-SYM-001",
        name="Seal Leak",
        code_type="symptom",
    )
    cause = services["maintenance_failure_code_service"].create_failure_code(
        failure_code="REL-CAUSE-001",
        name="Misalignment",
        code_type="cause",
    )

    completed_orders = []
    for index, downtime_minutes in enumerate((45, 60), start=1):
        row = work_orders_api.create_work_order(
            MaintenanceWorkOrderCreateCommand(
                site_id=site.id,
                work_order_code=f"WO-REL-{index:03d}",
                work_order_type="CORRECTIVE",
                asset_id=asset.id,
                system_id=system.id,
                location_id=location.id,
                title=f"Recurring repair {index}",
                description="Recurring reliability repair.",
                priority="MEDIUM",
            )
        )
        for status in ("PLANNED", "RELEASED", "IN_PROGRESS"):
            row = work_orders_api.update_work_order(
                MaintenanceWorkOrderUpdateCommand(
                    work_order_id=row.id,
                    status=status,
                    expected_version=row.version,
                )
            )
        row = work_orders_api.update_work_order(
            MaintenanceWorkOrderUpdateCommand(
                work_order_id=row.id,
                status="COMPLETED",
                failure_code=symptom.failure_code,
                root_cause_code=cause.failure_code,
                downtime_minutes=downtime_minutes,
                expected_version=row.version,
            )
        )
        services["maintenance_downtime_event_service"].create_downtime_event(
            work_order_id=row.id,
            started_at=(now - timedelta(days=index, hours=2)).isoformat(),
            ended_at=(now - timedelta(days=index, hours=1)).isoformat(),
            downtime_type="UNPLANNED",
            reason_code=symptom.failure_code,
            impact_notes=f"Recurring leak event {index}.",
        )
        completed_orders.append(row)

    return {
        "site": site,
        "location": location,
        "system": system,
        "asset": asset,
        "symptom": symptom,
        "cause": cause,
        "open_order": open_order,
        "completed_orders": tuple(completed_orders),
    }


def test_maintenance_dashboard_desktop_api_builds_reliability_snapshot(services) -> None:
    api = _build_dashboard_api(services)
    context = _create_maintenance_reliability_context(services)

    snapshot = api.build_snapshot(
        site_id=context["site"].id,
        asset_id=context["asset"].id,
        system_id=context["system"].id,
        location_id=context["location"].id,
        days=90,
    )

    assert isinstance(snapshot, MaintenanceDashboardSnapshotDescriptor)
    assert snapshot.overview.title == "Maintenance Dashboard"
    metrics = {metric.label: metric.value for metric in snapshot.overview.metrics}
    assert metrics["Open work orders"] == "1"
    assert metrics["Completed in window"] == "2"
    assert metrics["Downtime minutes"] == "120"
    assert snapshot.backlog_rows[0].label == "Planned"
    assert snapshot.root_cause_rows[0].root_cause_name == "Misalignment"
    assert snapshot.recurring_rows[0].anchor_label == "AST-REL - Pump 501"


def test_maintenance_reliability_desktop_api_builds_analysis_snapshot(services) -> None:
    api = _build_reliability_api(services)
    context = _create_maintenance_reliability_context(services)

    snapshot = api.build_snapshot(
        site_id=context["site"].id,
        asset_id=context["asset"].id,
        system_id=context["system"].id,
        location_id=context["location"].id,
        failure_code=context["symptom"].failure_code,
        days=90,
        limit=20,
        threshold=2,
    )

    assert isinstance(snapshot, MaintenanceReliabilitySnapshotDescriptor)
    assert snapshot.overview.title == "Reliability"
    metrics = {metric.label: metric.value for metric in snapshot.overview.metrics}
    assert metrics["Suggestions"] == "1"
    assert metrics["Root causes"] == "1"
    assert metrics["Recurring patterns"] == "1"
    assert snapshot.suggestion_rows[0].root_cause_name == "Misalignment"
    assert snapshot.root_cause_rows[0].failure_name == "Seal Leak"
    assert snapshot.recurring_rows[0].anchor_label == "AST-REL - Pump 501"
