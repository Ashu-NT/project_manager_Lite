from __future__ import annotations

from core.modules.maintenance_management.domain import MaintenanceIntegrationSource
from core.modules.maintenance_management.interfaces import MaintenanceIntegrationSourceRepository
from core.modules.maintenance_management.services import MaintenanceIntegrationSourceService
from core.platform.org.domain import Organization
from tests.test_maintenance_foundation import _OrgRepo, _user_session


class _IntegrationSourceRepo(MaintenanceIntegrationSourceRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenanceIntegrationSource] = {}

    def add(self, integration_source: MaintenanceIntegrationSource) -> None:
        self._rows[integration_source.id] = integration_source

    def update(self, integration_source: MaintenanceIntegrationSource) -> None:
        integration_source.version += 1
        self._rows[integration_source.id] = integration_source

    def get(self, integration_source_id: str):
        return self._rows.get(integration_source_id)

    def get_by_code(self, organization_id: str, integration_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.integration_code == integration_code:
                return row
        return None

    def list_for_organization(self, organization_id: str, *, active_only=None, integration_type=None):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        if integration_type is not None:
            rows = [row for row in rows if row.integration_type == integration_type]
        return rows


def test_maintenance_integration_source_service_tracks_sync_status(session) -> None:
    organization = Organization.create("ORG", "Org")
    repo = _IntegrationSourceRepo()
    service = MaintenanceIntegrationSourceService(
        session,
        repo,
        organization_repo=_OrgRepo(organization),
        user_session=_user_session(),
    )

    source = service.create_source(
        integration_code="iot-gateway-1",
        name="IoT Gateway 1",
        integration_type="iot_gateway",
        endpoint_or_path="mqtt://broker/factory",
        authentication_mode="token",
        schedule_expression="*/10 * * * *",
    )
    failed = service.record_sync_failure(
        source.id,
        error_message="Gateway timeout",
        expected_version=source.version,
    )
    assert failed.last_error_message == "Gateway timeout"
    assert failed.last_failed_sync_at is not None

    recovered = service.record_sync_success(
        source.id,
        expected_version=failed.version,
    )

    assert source.integration_code == "IOT-GATEWAY-1"
    assert recovered.last_successful_sync_at is not None
    assert recovered.last_error_message == ""
    assert service.find_source_by_code("IOT-GATEWAY-1") is not None
