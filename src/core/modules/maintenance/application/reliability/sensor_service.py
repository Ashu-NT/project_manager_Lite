from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.modules.maintenance.domain import MaintenanceSensor
from src.core.modules.maintenance.contracts.repositories import (
    MaintenanceAssetComponentRepository,
    MaintenanceAssetRepository,
    MaintenanceSensorRepository,
    MaintenanceSystemRepository,
)
from src.core.modules.maintenance.application.common.support import (
    normalize_maintenance_code,
    normalize_optional_text,
)
from src.core.modules.maintenance.application.common.scope_authorization import (
    deny_maintenance_scope_access,
)
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.shared.activity.activity_recorder import record_activity
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.contract.master_data.org.contracts import OrganizationRepository
from src.core.platform.contract.master_data.site.contracts import SiteRepository
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)
from src.core.shared.events.domain_events import DomainChangeEvent, domain_events
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.master_data.site import Site


class MaintenanceSensorService:
    def __init__(
        self,
        session: Session,
        sensor_repo: MaintenanceSensorRepository,
        *,
        organization_repo: OrganizationRepository,
        site_repo: SiteRepository,
        asset_repo: MaintenanceAssetRepository,
        component_repo: MaintenanceAssetComponentRepository,
        system_repo: MaintenanceSystemRepository,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        activity_service=None,
    ) -> None:
        self._session = session
        self._sensor_repo = sensor_repo
        self._organization_repo = organization_repo
        self._tenant_context_service = require_tenant_context_service(
            tenant_context_service,
            consumer_label="MaintenanceSensorService",
        )
        self._site_repo = site_repo
        self._asset_repo = asset_repo
        self._component_repo = component_repo
        self._system_repo = system_repo
        self._user_session = user_session
        self._activity_service = activity_service

    def list_sensors(
        self,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        sensor_type: str | None = None,
        source_type: str | None = None,
    ) -> list[MaintenanceSensor]:
        self._require_read("list maintenance sensors")
        organization = self._active_organization()
        if site_id is not None:
            self._get_site(site_id, organization=organization)
        if asset_id is not None:
            self._get_asset(asset_id, organization=organization)
        if component_id is not None:
            self._get_component(component_id, organization=organization)
        if system_id is not None:
            self._get_system(system_id, organization=organization)
        rows = self._sensor_repo.list_for_organization(
            organization.id,
            active_only=active_only,
            site_id=site_id,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            sensor_type=normalize_optional_text(sensor_type).upper() or None,
            source_type=normalize_optional_text(source_type).upper() or None,
        )
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=self._scope_anchor_for,
        )

    def search_sensors(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
        site_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        sensor_type: str | None = None,
        source_type: str | None = None,
    ) -> list[MaintenanceSensor]:
        normalized_search = normalize_optional_text(search_text).lower()
        rows = self.list_sensors(
            active_only=active_only,
            site_id=site_id,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
            sensor_type=sensor_type,
            source_type=source_type,
        )
        if not normalized_search:
            return rows
        return [
            row
            for row in rows
            if normalized_search in " ".join(
                filter(
                    None,
                    [
                        row.sensor_code,
                        row.sensor_name,
                        row.sensor_tag,
                        row.sensor_type,
                        row.source_type,
                        row.source_name,
                        row.source_key,
                        row.unit,
                        row.last_quality_state.value,
                    ],
                )
            ).lower()
        ]

    def get_sensor(self, sensor_id: str) -> MaintenanceSensor:
        self._require_read("view maintenance sensor")
        sensor = self._get_sensor(sensor_id, organization=self._active_organization())
        self._require_scope_read(self._scope_anchor_for(sensor), operation_label="view maintenance sensor")
        return sensor

    def find_sensor_by_code(
        self,
        sensor_code: str,
        *,
        active_only: bool | None = None,
    ) -> MaintenanceSensor | None:
        self._require_read("resolve maintenance sensor")
        organization = self._active_organization()
        sensor = self._sensor_repo.get_by_code(
            organization.id,
            normalize_maintenance_code(sensor_code, label="Sensor code"),
        )
        if sensor is None:
            return None
        if active_only is not None and sensor.is_active != bool(active_only):
            return None
        return sensor

    def create_sensor(
        self,
        *,
        site_id: str,
        sensor_code: str,
        sensor_name: str,
        sensor_tag: str = "",
        sensor_type: str = "",
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        source_type: str = "",
        source_name: str = "",
        source_key: str = "",
        unit: str = "",
        current_value=None,
        last_read_at=None,
        last_quality_state=None,
        is_active: bool = True,
        notes: str = "",
    ) -> MaintenanceSensor:
        self._require_manage("create maintenance sensor")
        organization = self._active_organization()
        site = self._get_site(site_id, organization=organization)
        asset, component, system = self._resolve_context(
            organization=organization,
            site=site,
            asset_id=asset_id,
            component_id=component_id,
            system_id=system_id,
        )
        sensor = MaintenanceSensor.create(
            organization_id=organization.id,
            site_id=site.id,
            sensor_code=sensor_code,
            sensor_name=sensor_name,
            sensor_tag=sensor_tag,
            sensor_type=sensor_type,
            asset_id=asset.id if asset is not None else None,
            component_id=component.id if component is not None else None,
            system_id=system.id if system is not None else None,
            source_type=source_type,
            source_name=source_name,
            source_key=source_key,
            unit=unit,
            current_value=current_value,
            last_read_at=last_read_at,
            last_quality_state=last_quality_state,
            is_active=bool(is_active),
            notes=notes,
        )
        if self._sensor_repo.get_by_code(organization.id, sensor.sensor_code) is not None:
            raise ValidationError("Sensor code already exists in the active organization.", code="MAINTENANCE_SENSOR_CODE_EXISTS")
        try:
            self._sensor_repo.add(sensor)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Sensor code already exists in the active organization.", code="MAINTENANCE_SENSOR_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_sensor.create", sensor)
        return sensor

    def update_sensor(
        self,
        sensor_id: str,
        *,
        site_id: str | None = None,
        sensor_code: str | None = None,
        sensor_name: str | None = None,
        sensor_tag: str | None = None,
        sensor_type: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        source_type: str | None = None,
        source_name: str | None = None,
        source_key: str | None = None,
        unit: str | None = None,
        current_value=None,
        last_read_at=None,
        last_quality_state=None,
        is_active: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> MaintenanceSensor:
        self._require_manage("update maintenance sensor")
        organization = self._active_organization()
        sensor = self.get_sensor(sensor_id)
        if expected_version is not None and sensor.version != expected_version:
            raise ConcurrencyError(
                "Maintenance sensor changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        target_site = (
            self._get_site(site_id, organization=organization)
            if site_id is not None
            else self._get_site(sensor.site_id, organization=organization)
        )
        next_site_id = sensor.site_id
        next_asset_id = sensor.asset_id
        next_component_id = sensor.component_id
        next_system_id = sensor.system_id
        if any(value is not None for value in (site_id, asset_id, component_id, system_id)):
            asset, component, system = self._resolve_context(
                organization=organization,
                site=target_site,
                asset_id=sensor.asset_id if asset_id is None else (asset_id or None),
                component_id=sensor.component_id if component_id is None else (component_id or None),
                system_id=sensor.system_id if system_id is None else (system_id or None),
            )
            next_site_id = target_site.id
            next_asset_id = asset.id if asset is not None else None
            next_component_id = component.id if component is not None else None
            next_system_id = system.id if system is not None else None
        elif target_site.id != sensor.site_id:
            self._resolve_context(
                organization=organization,
                site=target_site,
                asset_id=sensor.asset_id,
                component_id=sensor.component_id,
                system_id=sensor.system_id,
            )
            next_site_id = target_site.id

        updated = replace(
            sensor,
            site_id=next_site_id,
            sensor_code=sensor.sensor_code if sensor_code is None else sensor_code,
            sensor_name=sensor.sensor_name if sensor_name is None else sensor_name,
            sensor_tag=sensor.sensor_tag if sensor_tag is None else sensor_tag,
            sensor_type=sensor.sensor_type if sensor_type is None else sensor_type,
            asset_id=next_asset_id,
            component_id=next_component_id,
            system_id=next_system_id,
            source_type=sensor.source_type if source_type is None else source_type,
            source_name=sensor.source_name if source_name is None else source_name,
            source_key=sensor.source_key if source_key is None else source_key,
            unit=sensor.unit if unit is None else unit,
            current_value=sensor.current_value if current_value is None else current_value,
            last_read_at=sensor.last_read_at if last_read_at is None else last_read_at,
            last_quality_state=sensor.last_quality_state if last_quality_state is None else last_quality_state,
            is_active=sensor.is_active if is_active is None else bool(is_active),
            notes=sensor.notes if notes is None else notes,
            updated_at=datetime.now(timezone.utc),
        )
        existing = self._sensor_repo.get_by_code(organization.id, updated.sensor_code)
        if existing is not None and existing.id != sensor.id:
            raise ValidationError("Sensor code already exists in the active organization.", code="MAINTENANCE_SENSOR_CODE_EXISTS")
        try:
            self._sensor_repo.update(updated)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Sensor code already exists in the active organization.", code="MAINTENANCE_SENSOR_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        self._record_change("maintenance_sensor.update", updated)
        return updated

    def _resolve_context(
        self,
        *,
        organization: Organization,
        site: Site,
        asset_id: str | None,
        component_id: str | None,
        system_id: str | None,
    ):
        asset = self._get_asset(asset_id, organization=organization) if asset_id else None
        component = self._get_component(component_id, organization=organization) if component_id else None
        system = self._get_system(system_id, organization=organization) if system_id else None
        if component is not None:
            component_asset = self._get_asset(component.asset_id, organization=organization)
            if asset is None:
                asset = component_asset
            elif asset.id != component_asset.id:
                raise ValidationError(
                    "Selected component must belong to the selected asset.",
                    code="MAINTENANCE_SENSOR_COMPONENT_ASSET_MISMATCH",
                )
        if asset is None and component is None and system is None:
            raise ValidationError(
                "Maintenance sensor must be linked to an asset, component, or system.",
                code="MAINTENANCE_SENSOR_CONTEXT_REQUIRED",
            )
        if asset is not None and asset.site_id != site.id:
            raise ValidationError("Selected asset must belong to the selected site.", code="MAINTENANCE_SENSOR_SITE_MISMATCH")
        if system is not None and system.site_id != site.id:
            raise ValidationError("Selected system must belong to the selected site.", code="MAINTENANCE_SENSOR_SITE_MISMATCH")
        if asset is not None and system is not None and asset.system_id and asset.system_id != system.id:
            raise ValidationError(
                "Selected asset is already anchored to a different maintenance system.",
                code="MAINTENANCE_SENSOR_SYSTEM_MISMATCH",
            )
        return asset, component, system

    def _scope_anchor_for(self, sensor: MaintenanceSensor) -> str:
        if sensor.asset_id:
            return sensor.asset_id
        if sensor.component_id:
            component = self._component_repo.get(sensor.component_id)
            if component is not None and component.asset_id:
                return component.asset_id
        if sensor.system_id:
            return sensor.system_id
        return ""

    def _require_scope_read(self, scope_id: str, *, operation_label: str) -> None:
        if scope_id:
            require_scope_permission(
                self._user_session,
                "maintenance",
                scope_id,
                "maintenance.read",
                operation_label=operation_label,
            )
            return
        if self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            deny_maintenance_scope_access(
                self._user_session,
                operation_label=operation_label,
                message=(
                    f"Permission denied for {operation_label}. The record is "
                    "not anchored to a maintenance scope grant."
                ),
            )

    def _record_change(self, action: str, sensor: MaintenanceSensor) -> None:
        record_activity(
            self,
            action=action,
            entity_type="maintenance_sensor",
            entity_id=sensor.id,
            module="maintenance",
            details={
                "organization_id": sensor.organization_id,
                "site_id": sensor.site_id,
                "sensor_code": sensor.sensor_code,
                "asset_id": sensor.asset_id,
                "component_id": sensor.component_id,
                "system_id": sensor.system_id,
                "sensor_type": sensor.sensor_type,
                "source_type": sensor.source_type,
                "source_name": sensor.source_name,
                "source_key": sensor.source_key,
                "unit": sensor.unit,
                "last_quality_state": sensor.last_quality_state.value,
            },
        )
        domain_events.domain_changed.emit(
            DomainChangeEvent(
                category="module",
                scope_code="maintenance_management",
                entity_type="maintenance_sensor",
                entity_id=sensor.id,
                source_event="maintenance_sensors_changed",
            )
        )

    def _get_sensor(self, sensor_id: str, *, organization: Organization) -> MaintenanceSensor:
        sensor = self._sensor_repo.get(sensor_id)
        if sensor is None or sensor.organization_id != organization.id:
            raise NotFoundError("Maintenance sensor not found in the active organization.", code="MAINTENANCE_SENSOR_NOT_FOUND")
        return sensor

    def _get_site(self, site_id: str, *, organization: Organization) -> Site:
        site = self._site_repo.get(site_id)
        if site is None or site.organization_id != organization.id:
            raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
        return site

    def _get_asset(self, asset_id: str, *, organization: Organization):
        asset = self._asset_repo.get(asset_id)
        if asset is None or asset.organization_id != organization.id:
            raise NotFoundError("Maintenance asset not found in the active organization.", code="MAINTENANCE_ASSET_NOT_FOUND")
        return asset

    def _get_component(self, component_id: str, *, organization: Organization):
        component = self._component_repo.get(component_id)
        if component is None or component.organization_id != organization.id:
            raise NotFoundError(
                "Maintenance asset component not found in the active organization.",
                code="MAINTENANCE_COMPONENT_NOT_FOUND",
            )
        return component

    def _get_system(self, system_id: str, *, organization: Organization):
        system = self._system_repo.get(system_id)
        if system is None or system.organization_id != organization.id:
            raise NotFoundError("Maintenance system not found in the active organization.", code="MAINTENANCE_SYSTEM_NOT_FOUND")
        return system

    def _active_organization(self) -> Organization:
        return self._tenant_context_service.require_context(
            operation_label="maintenance sensors"
        ).organization

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)


__all__ = ["MaintenanceSensorService"]
