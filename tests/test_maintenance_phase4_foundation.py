from __future__ import annotations

from core.modules.maintenance_management.domain import (
    MaintenanceIntegrationSource,
    MaintenanceLocation,
    MaintenanceSensor,
    MaintenanceSensorException,
    MaintenanceSensorReading,
    MaintenanceSensorSourceMapping,
)
from core.modules.maintenance_management.interfaces import (
    MaintenanceSensorExceptionRepository,
    MaintenanceSensorSourceMappingRepository,
)
from core.modules.maintenance_management.services import (
    MaintenanceIntegrationSourceService,
    MaintenanceSensorExceptionService,
    MaintenanceSensorReadingService,
    MaintenanceSensorSourceMappingService,
)
from src.core.platform.org.domain import Organization, Site
from tests.test_maintenance_foundation import _AssetRepo, _LocationRepo, _OrgRepo, _SiteRepo, _user_session
from tests.test_maintenance_integration_foundation import _IntegrationSourceRepo
from tests.test_maintenance_sensor_foundation import _SensorReadingRepo, _SensorRepo
from core.modules.maintenance_management.domain import MaintenanceAsset


class _SensorSourceMappingRepo(MaintenanceSensorSourceMappingRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenanceSensorSourceMapping] = {}

    def add(self, sensor_source_mapping: MaintenanceSensorSourceMapping) -> None:
        self._rows[sensor_source_mapping.id] = sensor_source_mapping

    def update(self, sensor_source_mapping: MaintenanceSensorSourceMapping) -> None:
        sensor_source_mapping.version += 1
        self._rows[sensor_source_mapping.id] = sensor_source_mapping

    def get(self, sensor_source_mapping_id: str):
        return self._rows.get(sensor_source_mapping_id)

    def list_for_organization(
        self,
        organization_id: str,
        *,
        integration_source_id=None,
        sensor_id=None,
        active_only=None,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if integration_source_id is not None:
            rows = [row for row in rows if row.integration_source_id == integration_source_id]
        if sensor_id is not None:
            rows = [row for row in rows if row.sensor_id == sensor_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        return rows


class _SensorExceptionRepo(MaintenanceSensorExceptionRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenanceSensorException] = {}

    def add(self, sensor_exception: MaintenanceSensorException) -> None:
        self._rows[sensor_exception.id] = sensor_exception

    def update(self, sensor_exception: MaintenanceSensorException) -> None:
        sensor_exception.version += 1
        self._rows[sensor_exception.id] = sensor_exception

    def get(self, sensor_exception_id: str):
        return self._rows.get(sensor_exception_id)

    def list_for_organization(
        self,
        organization_id: str,
        *,
        sensor_id=None,
        integration_source_id=None,
        source_mapping_id=None,
        exception_type=None,
        status=None,
        source_batch_id=None,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if sensor_id is not None:
            rows = [row for row in rows if row.sensor_id == sensor_id]
        if integration_source_id is not None:
            rows = [row for row in rows if row.integration_source_id == integration_source_id]
        if source_mapping_id is not None:
            rows = [row for row in rows if row.source_mapping_id == source_mapping_id]
        if exception_type is not None:
            rows = [row for row in rows if row.exception_type.value == exception_type]
        if status is not None:
            rows = [row for row in rows if row.status.value == status]
        if source_batch_id is not None:
            rows = [row for row in rows if row.source_batch_id == source_batch_id]
        return rows


def _phase4_context():
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-P4",
        name="Phase4 Area",
    )
    asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        asset_code="ASSET-P4",
        name="Phase4 Asset",
    )
    sensor = MaintenanceSensor.create(
        organization_id=organization.id,
        site_id=site.id,
        sensor_code="SNS-P4",
        sensor_name="Phase4 Sensor",
        asset_id=asset.id,
        unit="C",
    )
    source = MaintenanceIntegrationSource.create(
        organization_id=organization.id,
        integration_code="SRC-P4",
        name="Phase4 Source",
        integration_type="IOT_GATEWAY",
    )
    return organization, site, location, asset, sensor, source


def test_maintenance_sensor_source_mapping_service_creates_sensor_bindings(session) -> None:
    organization, site, location, asset, sensor, source = _phase4_context()
    sensor_repo = _SensorRepo()
    sensor_repo.add(sensor)
    source_repo = _IntegrationSourceRepo()
    source_repo.add(source)
    mapping_service = MaintenanceSensorSourceMappingService(
        session,
        _SensorSourceMappingRepo(),
        organization_repo=_OrgRepo(organization),
        integration_source_repo=source_repo,
        sensor_repo=sensor_repo,
        user_session=_user_session(),
    )

    mapping = mapping_service.create_mapping(
        integration_source_id=source.id,
        sensor_id=sensor.id,
        external_equipment_key="EQ-100",
        external_measurement_key="TEMP_MAIN",
        unit_conversion_rule="x",
    )

    rows = mapping_service.list_mappings(sensor_id=sensor.id)
    assert mapping.external_measurement_key == "TEMP_MAIN"
    assert rows[0].id == mapping.id


def test_phase4_services_raise_and_resolve_sensor_exceptions(session) -> None:
    organization, site, location, asset, sensor, source = _phase4_context()
    source_repo = _IntegrationSourceRepo()
    source_repo.add(source)
    sensor_repo = _SensorRepo()
    sensor_repo.add(sensor)
    mapping_repo = _SensorSourceMappingRepo()
    exception_repo = _SensorExceptionRepo()
    exception_service = MaintenanceSensorExceptionService(
        session,
        exception_repo,
        organization_repo=_OrgRepo(organization),
        sensor_repo=sensor_repo,
        integration_source_repo=source_repo,
        sensor_source_mapping_repo=mapping_repo,
        user_session=_user_session(),
    )
    integration_service = MaintenanceIntegrationSourceService(
        session,
        source_repo,
        organization_repo=_OrgRepo(organization),
        sensor_exception_service=exception_service,
        user_session=_user_session(),
    )
    reading_service = MaintenanceSensorReadingService(
        session,
        _SensorReadingRepo(),
        organization_repo=_OrgRepo(organization),
        sensor_repo=sensor_repo,
        component_repo=_AssetRepo(),
        sensor_exception_service=exception_service,
        user_session=_user_session(),
    )

    failed = integration_service.record_sync_failure(
        source.id,
        error_message="Gateway timeout",
        expected_version=source.version,
    )
    reading = reading_service.record_reading(
        sensor_id=sensor.id,
        reading_value="98.2",
        reading_unit="C",
        quality_state="STALE",
        source_batch_id="BATCH-P4",
    )
    rows = exception_service.list_exceptions()
    sync_exception = next(row for row in rows if row.integration_source_id == source.id)
    stale_exception = next(row for row in rows if row.sensor_id == sensor.id)
    resolved = exception_service.update_exception_status(
        stale_exception.id,
        status="RESOLVED",
        expected_version=stale_exception.version,
    )

    assert failed.last_error_message == "Gateway timeout"
    assert sync_exception.exception_type.value == "EXTERNAL_SYNC_FAILURE"
    assert stale_exception.exception_type.value == "STALE_READING"
    assert stale_exception.source_batch_id == "BATCH-P4"
    assert resolved.status.value == "RESOLVED"
    assert resolved.resolved_at is not None
    assert reading.sensor_id == sensor.id
