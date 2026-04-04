from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.modules.maintenance_management.domain import MaintenanceWorkOrder, MaintenanceWorkOrderStatus
from core.modules.maintenance_management.interfaces import (
    MaintenanceAssetComponentRepository,
    MaintenanceAssetRepository,
    MaintenanceDowntimeEventRepository,
    MaintenanceFailureCodeRepository,
    MaintenanceLocationRepository,
    MaintenanceSystemRepository,
    MaintenanceWorkOrderRepository,
)
from core.modules.maintenance_management.reporting import register_maintenance_management_report_definitions
from core.modules.maintenance_management.services.reliability import MaintenanceReliabilityService
from core.platform.access.authorization import filter_scope_rows
from core.platform.common.exceptions import NotFoundError
from core.platform.common.interfaces import OrganizationRepository, SiteRepository
from core.platform.exporting import ensure_output_path, finalize_artifact
from core.platform.report_runtime import ReportDefinitionRegistry, ReportRuntime

from .documents import (
    MaintenanceReportLookups,
    build_backlog_report_document,
    build_downtime_report_document,
    build_execution_overview_report_document,
    build_pm_compliance_report_document,
)
from .renderers import render_report_document_excel, render_report_document_pdf


@dataclass(frozen=True)
class MaintenanceReportRequest:
    output_path: Path
    site_id: str | None = None
    asset_id: str | None = None
    system_id: str | None = None
    location_id: str | None = None
    days: int = 90
    limit: int = 20
    recurring_threshold: int = 2


class MaintenanceReportingService:
    def __init__(
        self,
        *,
        organization_repo: OrganizationRepository,
        site_repo: SiteRepository,
        asset_repo: MaintenanceAssetRepository,
        component_repo: MaintenanceAssetComponentRepository,
        location_repo: MaintenanceLocationRepository,
        system_repo: MaintenanceSystemRepository,
        work_order_repo: MaintenanceWorkOrderRepository,
        failure_code_repo: MaintenanceFailureCodeRepository,
        downtime_event_repo: MaintenanceDowntimeEventRepository,
        reliability_service: MaintenanceReliabilityService,
        user_session=None,
        module_catalog_service=None,
        runtime_execution_service=None,
        report_registry: ReportDefinitionRegistry | None = None,
        report_runtime: ReportRuntime | None = None,
    ) -> None:
        self._organization_repo = organization_repo
        self._site_repo = site_repo
        self._asset_repo = asset_repo
        self._component_repo = component_repo
        self._location_repo = location_repo
        self._system_repo = system_repo
        self._work_order_repo = work_order_repo
        self._failure_code_repo = failure_code_repo
        self._downtime_event_repo = downtime_event_repo
        self._reliability_service = reliability_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

        registry = report_registry or ReportDefinitionRegistry()
        register_maintenance_management_report_definitions(
            registry,
            render_handlers={
                "maintenance_backlog_excel": self._render_backlog_excel,
                "maintenance_backlog_pdf": self._render_backlog_pdf,
                "maintenance_pm_compliance_excel": self._render_pm_compliance_excel,
                "maintenance_pm_compliance_pdf": self._render_pm_compliance_pdf,
                "maintenance_downtime_excel": self._render_downtime_excel,
                "maintenance_downtime_pdf": self._render_downtime_pdf,
                "maintenance_execution_overview_excel": self._render_execution_overview_excel,
                "maintenance_execution_overview_pdf": self._render_execution_overview_pdf,
            },
        )
        self._report_runtime = report_runtime or ReportRuntime(
            registry,
            user_session=user_session,
            module_catalog_service=module_catalog_service,
            runtime_execution_service=runtime_execution_service,
        )

    def generate_backlog_excel(self, output_path: str | Path, **filters):
        return self._render("maintenance_backlog_excel", output_path=output_path, **filters)

    def generate_backlog_pdf(self, output_path: str | Path, **filters):
        return self._render("maintenance_backlog_pdf", output_path=output_path, **filters)

    def generate_pm_compliance_excel(self, output_path: str | Path, **filters):
        return self._render("maintenance_pm_compliance_excel", output_path=output_path, **filters)

    def generate_pm_compliance_pdf(self, output_path: str | Path, **filters):
        return self._render("maintenance_pm_compliance_pdf", output_path=output_path, **filters)

    def generate_downtime_excel(self, output_path: str | Path, **filters):
        return self._render("maintenance_downtime_excel", output_path=output_path, **filters)

    def generate_downtime_pdf(self, output_path: str | Path, **filters):
        return self._render("maintenance_downtime_pdf", output_path=output_path, **filters)

    def generate_execution_overview_excel(self, output_path: str | Path, **filters):
        return self._render("maintenance_execution_overview_excel", output_path=output_path, **filters)

    def generate_execution_overview_pdf(self, output_path: str | Path, **filters):
        return self._render("maintenance_execution_overview_pdf", output_path=output_path, **filters)

    def _render(self, report_key: str, *, output_path: str | Path, **filters):
        return self._report_runtime.render(
            report_key,
            MaintenanceReportRequest(output_path=Path(output_path), **filters),
            user_session=self._user_session,
            module_catalog_service=self._module_catalog_service,
        )

    def _render_backlog_excel(self, request: object):
        assert isinstance(request, MaintenanceReportRequest)
        document = self._build_backlog_document(request)
        output = ensure_output_path(request.output_path)
        rendered = render_report_document_excel(document, output)
        return finalize_artifact(
            rendered,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def _render_backlog_pdf(self, request: object):
        assert isinstance(request, MaintenanceReportRequest)
        document = self._build_backlog_document(request)
        output = ensure_output_path(request.output_path)
        rendered = render_report_document_pdf(document, output)
        return finalize_artifact(rendered, media_type="application/pdf")

    def _render_pm_compliance_excel(self, request: object):
        assert isinstance(request, MaintenanceReportRequest)
        document = self._build_pm_compliance_document(request)
        output = ensure_output_path(request.output_path)
        rendered = render_report_document_excel(document, output)
        return finalize_artifact(
            rendered,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def _render_pm_compliance_pdf(self, request: object):
        assert isinstance(request, MaintenanceReportRequest)
        document = self._build_pm_compliance_document(request)
        output = ensure_output_path(request.output_path)
        rendered = render_report_document_pdf(document, output)
        return finalize_artifact(rendered, media_type="application/pdf")

    def _render_downtime_excel(self, request: object):
        assert isinstance(request, MaintenanceReportRequest)
        document = self._build_downtime_document(request)
        output = ensure_output_path(request.output_path)
        rendered = render_report_document_excel(document, output)
        return finalize_artifact(
            rendered,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def _render_downtime_pdf(self, request: object):
        assert isinstance(request, MaintenanceReportRequest)
        document = self._build_downtime_document(request)
        output = ensure_output_path(request.output_path)
        rendered = render_report_document_pdf(document, output)
        return finalize_artifact(rendered, media_type="application/pdf")

    def _render_execution_overview_excel(self, request: object):
        assert isinstance(request, MaintenanceReportRequest)
        document = self._build_execution_overview_document(request)
        output = ensure_output_path(request.output_path)
        rendered = render_report_document_excel(document, output)
        return finalize_artifact(
            rendered,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def _render_execution_overview_pdf(self, request: object):
        assert isinstance(request, MaintenanceReportRequest)
        document = self._build_execution_overview_document(request)
        output = ensure_output_path(request.output_path)
        rendered = render_report_document_pdf(document, output)
        return finalize_artifact(rendered, media_type="application/pdf")

    def _build_backlog_document(self, request: MaintenanceReportRequest):
        dashboard = self._reliability_service.build_reliability_dashboard(
            site_id=request.site_id,
            asset_id=request.asset_id,
            system_id=request.system_id,
            location_id=request.location_id,
            days=request.days,
            recurring_threshold=request.recurring_threshold,
            limit=request.limit,
        )
        organization_id = self._active_organization_id()
        rows = [
            row
            for row in self._list_work_orders(
                organization_id,
                request=request,
                open_only=True,
            )
        ][: request.limit]
        return build_backlog_report_document(
            dashboard=dashboard,
            work_orders=rows,
            lookups=self._lookups(organization_id),
        )

    def _build_downtime_document(self, request: MaintenanceReportRequest):
        dashboard = self._reliability_service.build_reliability_dashboard(
            site_id=request.site_id,
            asset_id=request.asset_id,
            system_id=request.system_id,
            location_id=request.location_id,
            days=request.days,
            recurring_threshold=request.recurring_threshold,
            limit=request.limit,
        )
        organization_id = self._active_organization_id()
        lookups = self._lookups(organization_id)
        work_orders = self._list_work_orders(organization_id, request=request)
        work_order_codes = {work_order.id: work_order.work_order_code for work_order in work_orders}
        downtime_rows = [
            (
                _timestamp(row.started_at),
                _timestamp(row.ended_at),
                int(row.duration_minutes or 0),
                row.downtime_type,
                self._failure_label(organization_id, row.reason_code),
                work_order_codes.get(row.work_order_id or "", ""),
                lookups.asset_labels.get(row.asset_id or "", ""),
                lookups.system_labels.get(row.system_id or "", ""),
                row.impact_notes,
            )
            for row in self._list_downtime_events(
                organization_id,
                request=request,
            )[: request.limit]
        ]
        recurring = self._reliability_service.list_recurring_failure_patterns(
            site_id=request.site_id,
            asset_id=request.asset_id,
            system_id=request.system_id,
            location_id=request.location_id,
            days=request.days,
            min_occurrences=request.recurring_threshold,
            limit=request.limit,
        )
        return build_downtime_report_document(
            dashboard=dashboard,
            downtime_rows=downtime_rows,
            recurring_patterns=recurring,
        )

    def _build_execution_overview_document(self, request: MaintenanceReportRequest):
        organization_id = self._active_organization_id()
        rows = self._list_windowed_work_orders(organization_id, request=request)[: request.limit]
        return build_execution_overview_report_document(
            work_orders=rows,
            lookups=self._lookups(organization_id),
            days=request.days,
        )

    def _build_pm_compliance_document(self, request: MaintenanceReportRequest):
        organization_id = self._active_organization_id()
        rows = [
            row
            for row in self._list_windowed_work_orders(organization_id, request=request)
            if row.is_preventive
        ][: request.limit]
        return build_pm_compliance_report_document(
            preventive_rows=rows,
            lookups=self._lookups(organization_id),
            days=request.days,
        )

    def _active_organization_id(self) -> str:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization.id

    def _lookups(self, organization_id: str) -> MaintenanceReportLookups:
        return MaintenanceReportLookups(
            site_codes={
                row.id: row.site_code
                for row in self._site_repo.list_for_organization(organization_id, active_only=None)
            },
            asset_labels={
                row.id: row.asset_code
                for row in self._asset_repo.list_for_organization(organization_id, active_only=None)
            },
            system_labels={
                row.id: row.system_code
                for row in self._system_repo.list_for_organization(organization_id, active_only=None)
            },
            location_labels={
                row.id: row.location_code
                for row in self._location_repo.list_for_organization(organization_id, active_only=None)
            },
            failure_labels={
                row.failure_code: row.name
                for row in self._failure_code_repo.list_for_organization(organization_id, active_only=None)
            },
        )

    def _failure_label(self, organization_id: str, failure_code: str) -> str:
        if not failure_code:
            return ""
        lookup = self._failure_code_repo.get_by_code(organization_id, failure_code)
        return lookup.name if lookup is not None else failure_code

    def _list_windowed_work_orders(
        self,
        organization_id: str,
        *,
        request: MaintenanceReportRequest,
    ) -> list[MaintenanceWorkOrder]:
        windowed = [
            row
            for row in self._list_work_orders(organization_id, request=request)
            if _activity_at(row) >= _window_start(request.days)
        ]
        return sorted(windowed, key=_activity_at, reverse=True)

    def _list_work_orders(
        self,
        organization_id: str,
        *,
        request: MaintenanceReportRequest,
        open_only: bool = False,
    ) -> list[MaintenanceWorkOrder]:
        rows = self._work_order_repo.list_for_organization(
            organization_id,
            site_id=request.site_id,
            asset_id=request.asset_id,
            system_id=request.system_id,
            location_id=request.location_id,
        )
        scoped = list(
            filter_scope_rows(
                rows,
                self._user_session,
                scope_type="maintenance",
                permission_code="maintenance.read",
                scope_id_getter=self._scope_anchor_for_work_order,
            )
        )
        if open_only:
            scoped = [row for row in scoped if row.status not in {MaintenanceWorkOrderStatus.COMPLETED, MaintenanceWorkOrderStatus.VERIFIED, MaintenanceWorkOrderStatus.CLOSED, MaintenanceWorkOrderStatus.CANCELLED}]
        return scoped

    def _list_downtime_events(
        self,
        organization_id: str,
        *,
        request: MaintenanceReportRequest,
    ):
        allowed_work_orders = self._list_work_orders(organization_id, request=request)
        allowed_work_order_ids = {row.id for row in allowed_work_orders}
        allowed_asset_ids = {row.asset_id for row in allowed_work_orders if row.asset_id}
        allowed_system_ids = {row.system_id for row in allowed_work_orders if row.system_id}
        rows = self._downtime_event_repo.list_for_organization(
            organization_id,
            asset_id=request.asset_id,
            system_id=request.system_id,
            started_from=_window_start(request.days),
        )
        filtered = []
        for row in rows:
            if allowed_work_order_ids:
                if row.work_order_id and row.work_order_id in allowed_work_order_ids:
                    filtered.append(row)
                    continue
                if row.asset_id and row.asset_id in allowed_asset_ids:
                    filtered.append(row)
                    continue
                if row.system_id and row.system_id in allowed_system_ids:
                    filtered.append(row)
                    continue
            elif not any(value is not None for value in (request.site_id, request.location_id)):
                filtered.append(row)
        return filtered

    def _scope_anchor_for_work_order(self, work_order: MaintenanceWorkOrder) -> str:
        if work_order.asset_id:
            return work_order.asset_id
        if work_order.component_id:
            component = self._component_repo.get(work_order.component_id)
            if component is not None and component.asset_id:
                return component.asset_id
        if work_order.system_id:
            return work_order.system_id
        if work_order.location_id:
            return work_order.location_id
        return ""


def _timestamp(value) -> str:
    if value is None:
        return ""
    return _to_utc(value).isoformat()


def _activity_at(work_order: MaintenanceWorkOrder) -> datetime:
    return _to_utc(
        work_order.closed_at
        or work_order.actual_end
        or work_order.actual_start
        or work_order.planned_start
        or work_order.requested_at
        or work_order.created_at
        or datetime.now(timezone.utc)
    )


def _window_start(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _to_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


__all__ = [
    "MaintenanceReportRequest",
    "MaintenanceReportingService",
]
