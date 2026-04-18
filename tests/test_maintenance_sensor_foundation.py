from __future__ import annotations

from decimal import Decimal

from core.modules.maintenance_management.domain import MaintenanceAsset, MaintenanceLocation, MaintenanceSensor, MaintenanceSensorReading
from core.modules.maintenance_management.interfaces import MaintenanceSensorReadingRepository, MaintenanceSensorRepository
from core.modules.maintenance_management.services import MaintenanceSensorReadingService, MaintenanceSensorService
from src.core.platform.org.domain import Organization, Site
from tests.test_maintenance_foundation import (
    _AssetRepo,
    _ComponentRepo,
    _LocationRepo,
    _OrgRepo,
    _SiteRepo,
    _SystemRepo,
    _user_session,
)


class _SensorRepo(MaintenanceSensorRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenanceSensor] = {}

    def add(self, sensor: MaintenanceSensor) -> None:
        self._rows[sensor.id] = sensor

    def update(self, sensor: MaintenanceSensor) -> None:
        sensor.version += 1
        self._rows[sensor.id] = sensor

    def get(self, sensor_id: str):
        return self._rows.get(sensor_id)

    def get_by_code(self, organization_id: str, sensor_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.sensor_code == sensor_code:
                return row
        return None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only=None,
        site_id=None,
        asset_id=None,
        component_id=None,
        system_id=None,
        sensor_type=None,
        source_type=None,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        if site_id is not None:
            rows = [row for row in rows if row.site_id == site_id]
        if asset_id is not None:
            rows = [row for row in rows if row.asset_id == asset_id]
        if component_id is not None:
            rows = [row for row in rows if row.component_id == component_id]
        if system_id is not None:
            rows = [row for row in rows if row.system_id == system_id]
        if sensor_type is not None:
            rows = [row for row in rows if row.sensor_type == sensor_type]
        if source_type is not None:
            rows = [row for row in rows if row.source_type == source_type]
        return rows


class _SensorReadingRepo(MaintenanceSensorReadingRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenanceSensorReading] = {}

    def add(self, sensor_reading: MaintenanceSensorReading) -> None:
        self._rows[sensor_reading.id] = sensor_reading

    def get(self, sensor_reading_id: str):
        return self._rows.get(sensor_reading_id)

    def list_for_organization(
        self,
        organization_id: str,
        *,
        sensor_id=None,
        quality_state=None,
        source_batch_id=None,
        reading_from=None,
        reading_to=None,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if sensor_id is not None:
            rows = [row for row in rows if row.sensor_id == sensor_id]
        if quality_state is not None:
            rows = [row for row in rows if row.quality_state.value == quality_state]
        if source_batch_id is not None:
            rows = [row for row in rows if row.source_batch_id == source_batch_id]
        if reading_from is not None:
            rows = [row for row in rows if row.reading_timestamp >= reading_from]
        if reading_to is not None:
            rows = [row for row in rows if row.reading_timestamp <= reading_to]
        return sorted(rows, key=lambda row: row.reading_timestamp, reverse=True)


def test_maintenance_sensor_service_creates_asset_anchored_sensors(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-SENSOR",
        name="Sensor Area",
    )
    asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        asset_code="ASSET-SENSOR",
        name="Sensor Asset",
    )

    location_repo = _LocationRepo()
    location_repo.add(location)
    asset_repo = _AssetRepo()
    asset_repo.add(asset)
    sensor_service = MaintenanceSensorService(
        session,
        _SensorRepo(),
        organization_repo=_OrgRepo(organization),
        site_repo=_SiteRepo([site]),
        asset_repo=asset_repo,
        component_repo=_ComponentRepo(),
        system_repo=_SystemRepo(),
        user_session=_user_session(),
    )

    sensor = sensor_service.create_sensor(
        site_id=site.id,
        sensor_code="run-hours-1",
        sensor_name="Running Hours 1",
        asset_id=asset.id,
        sensor_type="running_hours",
        source_type="iot_gateway",
        unit="H",
    )
    found = sensor_service.find_sensor_by_code("RUN-HOURS-1")

    assert sensor.sensor_code == "RUN-HOURS-1"
    assert sensor.asset_id == asset.id
    assert found is not None
    assert found.id == sensor.id
    assert sensor_service.list_sensors(asset_id=asset.id)[0].id == sensor.id


def test_maintenance_sensor_reading_service_updates_sensor_snapshot(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-READING",
        name="Reading Area",
    )
    asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        asset_code="ASSET-READING",
        name="Reading Asset",
    )

    sensor_repo = _SensorRepo()
    sensor = MaintenanceSensor.create(
        organization_id=organization.id,
        site_id=site.id,
        sensor_code="TEMP-1",
        sensor_name="Temperature 1",
        asset_id=asset.id,
        sensor_type="TEMPERATURE",
        unit="C",
    )
    sensor_repo.add(sensor)
    reading_service = MaintenanceSensorReadingService(
        session,
        _SensorReadingRepo(),
        organization_repo=_OrgRepo(organization),
        sensor_repo=sensor_repo,
        component_repo=_ComponentRepo(),
        user_session=_user_session(),
    )

    reading = reading_service.record_reading(
        sensor_id=sensor.id,
        reading_value="82.4",
        reading_unit="C",
        source_name="PLC",
        source_batch_id="BATCH-1",
    )
    refreshed_sensor = sensor_repo.get(sensor.id)
    rows = reading_service.list_readings(sensor_id=sensor.id)

    assert reading.reading_value == Decimal("82.4")
    assert reading.source_batch_id == "BATCH-1"
    assert refreshed_sensor is not None
    assert refreshed_sensor.current_value == Decimal("82.4")
    assert refreshed_sensor.last_read_at == reading.reading_timestamp
    assert rows[0].id == reading.id
