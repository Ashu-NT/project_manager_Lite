from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from core.modules.maintenance_management.domain import (
    MaintenancePriority,
    MaintenanceWorkOrder,
    MaintenanceWorkOrderStatus,
)
from core.modules.maintenance_management.interfaces import (
    MaintenanceAssetComponentRepository,
    MaintenanceAssetRepository,
    MaintenanceDowntimeEventRepository,
    MaintenanceFailureCodeRepository,
    MaintenanceLocationRepository,
    MaintenanceSystemRepository,
    MaintenanceWorkOrderRepository,
)
from core.modules.maintenance_management.reporting import (
    MaintenanceRecurringFailurePattern,
    MaintenanceReliabilityDashboard,
    MaintenanceRootCauseInsight,
    MaintenanceRootCauseSuggestion,
    ReportMetric,
)
from core.modules.maintenance_management.support import normalize_maintenance_code
from core.platform.access.authorization import filter_scope_rows
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository, SiteRepository
from core.platform.org.domain import Organization, Site

_TERMINAL_WORK_ORDER_STATUSES = {
    MaintenanceWorkOrderStatus.COMPLETED,
    MaintenanceWorkOrderStatus.VERIFIED,
    MaintenanceWorkOrderStatus.CLOSED,
    MaintenanceWorkOrderStatus.CANCELLED,
}


class MaintenanceReliabilityService:
    def __init__(
        self,
        session,
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
        user_session=None,
    ) -> None:
        self._session = session
        self._organization_repo = organization_repo
        self._site_repo = site_repo
        self._asset_repo = asset_repo
        self._component_repo = component_repo
        self._location_repo = location_repo
        self._system_repo = system_repo
        self._work_order_repo = work_order_repo
        self._failure_code_repo = failure_code_repo
        self._downtime_event_repo = downtime_event_repo
        self._user_session = user_session

    def build_reliability_dashboard(
        self,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        days: int = 90,
        recurring_threshold: int = 2,
        limit: int = 5,
    ) -> MaintenanceReliabilityDashboard:
        self._require_report_view("view maintenance reliability dashboard")
        organization = self._active_organization()
        site = self._validate_scope_filters(
            organization=organization,
            site_id=site_id,
            asset_id=asset_id,
            system_id=system_id,
            location_id=location_id,
        )
        window_start = self._window_start(days)
        work_orders = self._list_work_orders(
            organization=organization,
            site_id=site_id,
            asset_id=asset_id,
            system_id=system_id,
            location_id=location_id,
        )
        windowed_work_orders = [row for row in work_orders if self._activity_at(row) >= window_start]
        downtime_rows = self._list_downtime_events(
            organization=organization,
            site_id=site_id,
            asset_id=asset_id,
            system_id=system_id,
            location_id=location_id,
            started_from=window_start,
        )

        open_rows = [row for row in work_orders if self._is_open_status(row.status)]
        overdue_rows = [
            row
            for row in open_rows
            if row.planned_end is not None and row.planned_end < datetime.now(timezone.utc)
        ]
        backlog_by_status = Counter(str(row.status.value) for row in open_rows)
        backlog_by_priority = Counter(str(row.priority.value) for row in open_rows)
        downtime_by_type = Counter(str(row.downtime_type or "UNSPECIFIED") for row in downtime_rows)
        mttr_hours = self._mean_repair_hours(windowed_work_orders)
        mtbf_hours = self._mean_interval_hours(windowed_work_orders)

        return MaintenanceReliabilityDashboard(
            title="Maintenance Reliability Dashboard",
            filters=(
                ReportMetric("Site", site.site_code if site is not None else "All sites"),
                ReportMetric("Asset", self._asset_label(asset_id) if asset_id else "All assets"),
                ReportMetric("System", self._system_label(system_id) if system_id else "All systems"),
                ReportMetric("Location", self._location_label(location_id) if location_id else "All locations"),
                ReportMetric("Window", f"{days} days"),
            ),
            summary=(
                ReportMetric("Open work orders", len(open_rows)),
                ReportMetric("In progress work orders", sum(1 for row in open_rows if row.status == MaintenanceWorkOrderStatus.IN_PROGRESS)),
                ReportMetric("Overdue work orders", len(overdue_rows)),
                ReportMetric("Completed in window", sum(1 for row in windowed_work_orders if row.status in _TERMINAL_WORK_ORDER_STATUSES)),
                ReportMetric("Open downtime events", sum(1 for row in downtime_rows if row.ended_at is None)),
                ReportMetric("Downtime minutes", sum(int(row.duration_minutes or 0) for row in downtime_rows)),
                ReportMetric("MTTR hours", mttr_hours if mttr_hours is not None else "n/a"),
                ReportMetric("MTBF hours", mtbf_hours if mtbf_hours is not None else "n/a"),
            ),
            backlog_by_status=tuple(
                ReportMetric(status.replace("_", " ").title(), backlog_by_status.get(status.value, 0))
                for status in MaintenanceWorkOrderStatus
                if backlog_by_status.get(status.value, 0)
            ),
            backlog_by_priority=tuple(
                ReportMetric(priority.value.title(), backlog_by_priority.get(priority.value, 0))
                for priority in MaintenancePriority
                if backlog_by_priority.get(priority.value, 0)
            ),
            downtime_by_type=tuple(
                ReportMetric(label.replace("_", " ").title(), minutes)
                for label, minutes in sorted(downtime_by_type.items(), key=lambda item: (-item[1], item[0]))
            ),
            top_root_causes=tuple(
                self.list_root_cause_analysis(
                    site_id=site_id,
                    asset_id=asset_id,
                    system_id=system_id,
                    location_id=location_id,
                    days=days,
                    limit=limit,
                )
            ),
            recurring_failures=tuple(
                self.list_recurring_failure_patterns(
                    site_id=site_id,
                    asset_id=asset_id,
                    system_id=system_id,
                    location_id=location_id,
                    days=days,
                    min_occurrences=recurring_threshold,
                    limit=limit,
                )
            ),
        )

    def list_root_cause_analysis(
        self,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        days: int = 180,
        limit: int = 20,
    ) -> list[MaintenanceRootCauseInsight]:
        self._require_report_view("view maintenance root cause analysis")
        organization = self._active_organization()
        self._validate_scope_filters(
            organization=organization,
            site_id=site_id,
            asset_id=asset_id,
            system_id=system_id,
            location_id=location_id,
        )
        window_start = self._window_start(days)
        rows = [
            row
            for row in self._list_work_orders(
                organization=organization,
                site_id=site_id,
                asset_id=asset_id,
                system_id=system_id,
                location_id=location_id,
            )
            if row.root_cause_code and self._activity_at(row) >= window_start
        ]
        failure_lookup = self._failure_lookup(organization.id)
        aggregates: dict[tuple[str, str], dict[str, object]] = {}
        for row in rows:
            key = (row.failure_code or "", row.root_cause_code or "")
            bucket = aggregates.setdefault(
                key,
                {
                    "count": 0,
                    "downtime": 0,
                    "latest": None,
                    "open": 0,
                },
            )
            bucket["count"] = int(bucket["count"]) + 1
            bucket["downtime"] = int(bucket["downtime"]) + int(row.downtime_minutes or 0)
            if self._is_open_status(row.status):
                bucket["open"] = int(bucket["open"]) + 1
            activity_at = self._activity_at(row)
            if bucket["latest"] is None or activity_at > bucket["latest"]:
                bucket["latest"] = activity_at

        insights = [
            MaintenanceRootCauseInsight(
                failure_code=failure_code,
                failure_name=failure_lookup.get(failure_code, failure_code),
                root_cause_code=root_cause_code,
                root_cause_name=failure_lookup.get(root_cause_code, root_cause_code),
                work_order_count=int(values["count"]),
                total_downtime_minutes=int(values["downtime"]),
                average_downtime_minutes=round(int(values["downtime"]) / int(values["count"]), 2),
                latest_occurrence_at=values["latest"],
                open_work_orders=int(values["open"]),
            )
            for (failure_code, root_cause_code), values in aggregates.items()
        ]
        insights.sort(
            key=lambda row: (
                -row.work_order_count,
                -row.total_downtime_minutes,
                row.root_cause_code,
            )
        )
        return insights[:limit]

    def suggest_root_causes(
        self,
        *,
        failure_code: str,
        asset_id: str | None = None,
        system_id: str | None = None,
        days: int = 365,
        limit: int = 5,
    ) -> list[MaintenanceRootCauseSuggestion]:
        self._require_report_view("suggest maintenance root causes")
        organization = self._active_organization()
        normalized_failure_code = normalize_maintenance_code(failure_code, label="Failure code")
        failure = self._failure_code_repo.get_by_code(organization.id, normalized_failure_code)
        if failure is None:
            raise ValidationError(
                "Maintenance failure code not found in the active organization.",
                code="MAINTENANCE_FAILURE_CODE_NOT_FOUND",
            )
        if asset_id is not None:
            self._get_asset(asset_id, organization=organization)
        if system_id is not None:
            self._get_system(system_id, organization=organization)

        window_start = self._window_start(days)
        failure_lookup = self._failure_lookup(organization.id)
        base_rows = [
            row
            for row in self._list_work_orders(organization=organization)
            if row.failure_code == normalized_failure_code
            and row.root_cause_code
            and self._activity_at(row) >= window_start
        ]

        for match_scope, filtered_rows in (
            (
                "asset",
                [row for row in base_rows if asset_id is not None and row.asset_id == asset_id],
            ),
            (
                "system",
                [row for row in base_rows if system_id is not None and row.system_id == system_id],
            ),
            ("organization", base_rows),
        ):
            if not filtered_rows:
                continue
            aggregates: dict[str, dict[str, object]] = {}
            for row in filtered_rows:
                bucket = aggregates.setdefault(
                    row.root_cause_code,
                    {
                        "count": 0,
                        "downtime": 0,
                        "latest": None,
                    },
                )
                bucket["count"] = int(bucket["count"]) + 1
                bucket["downtime"] = int(bucket["downtime"]) + int(row.downtime_minutes or 0)
                activity_at = self._activity_at(row)
                if bucket["latest"] is None or activity_at > bucket["latest"]:
                    bucket["latest"] = activity_at
            suggestions = [
                MaintenanceRootCauseSuggestion(
                    root_cause_code=root_cause_code,
                    root_cause_name=failure_lookup.get(root_cause_code, root_cause_code),
                    match_scope=match_scope,
                    occurrence_count=int(values["count"]),
                    total_downtime_minutes=int(values["downtime"]),
                    latest_occurrence_at=values["latest"],
                )
                for root_cause_code, values in aggregates.items()
            ]
            suggestions.sort(
                key=lambda row: (
                    -row.occurrence_count,
                    -row.total_downtime_minutes,
                    row.root_cause_code,
                )
            )
            return suggestions[:limit]
        return []

    def list_recurring_failure_patterns(
        self,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        days: int = 180,
        min_occurrences: int = 2,
        limit: int = 20,
    ) -> list[MaintenanceRecurringFailurePattern]:
        self._require_report_view("view maintenance recurring failure analytics")
        organization = self._active_organization()
        self._validate_scope_filters(
            organization=organization,
            site_id=site_id,
            asset_id=asset_id,
            system_id=system_id,
            location_id=location_id,
        )
        if min_occurrences < 2:
            raise ValidationError(
                "Recurring failure analysis requires at least two occurrences.",
                code="MAINTENANCE_RECURRING_FAILURE_THRESHOLD_INVALID",
            )
        window_start = self._window_start(days)
        rows = [
            row
            for row in self._list_work_orders(
                organization=organization,
                site_id=site_id,
                asset_id=asset_id,
                system_id=system_id,
                location_id=location_id,
            )
            if row.failure_code and row.status != MaintenanceWorkOrderStatus.CANCELLED and self._activity_at(row) >= window_start
        ]
        failure_lookup = self._failure_lookup(organization.id)
        anchors = self._anchor_lookup(organization.id)
        grouped: dict[tuple[str, str, str, str], list[MaintenanceWorkOrder]] = defaultdict(list)
        for row in rows:
            anchor_type, anchor_id = self._pattern_anchor(row)
            if not anchor_id:
                continue
            grouped[(anchor_type, anchor_id, row.failure_code, row.root_cause_code or "")].append(row)

        patterns: list[MaintenanceRecurringFailurePattern] = []
        for (anchor_type, anchor_id, failure_code, root_cause_code), group_rows in grouped.items():
            if len(group_rows) < min_occurrences:
                continue
            lead_root_cause = root_cause_code or self._leading_root_cause(group_rows)
            activity_points = sorted(self._activity_at(row) for row in group_rows)
            total_downtime = sum(int(row.downtime_minutes or 0) for row in group_rows)
            patterns.append(
                MaintenanceRecurringFailurePattern(
                    anchor_type=anchor_type,
                    anchor_id=anchor_id,
                    anchor_code=anchors.get((anchor_type, anchor_id), ("", ""))[0],
                    anchor_name=anchors.get((anchor_type, anchor_id), ("", ""))[1],
                    failure_code=failure_code,
                    failure_name=failure_lookup.get(failure_code, failure_code),
                    leading_root_cause_code=lead_root_cause,
                    leading_root_cause_name=failure_lookup.get(lead_root_cause, lead_root_cause),
                    occurrence_count=len(group_rows),
                    open_work_orders=sum(1 for row in group_rows if self._is_open_status(row.status)),
                    total_downtime_minutes=total_downtime,
                    mean_interval_hours=self._interval_hours(activity_points),
                    mean_repair_hours=self._repair_hours(group_rows),
                    first_occurrence_at=activity_points[0] if activity_points else None,
                    last_occurrence_at=activity_points[-1] if activity_points else None,
                )
            )
        patterns.sort(
            key=lambda row: (
                -row.occurrence_count,
                -row.total_downtime_minutes,
                row.anchor_code,
                row.failure_code,
            )
        )
        return patterns[:limit]

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _validate_scope_filters(
        self,
        *,
        organization: Organization,
        site_id: str | None,
        asset_id: str | None,
        system_id: str | None,
        location_id: str | None,
    ) -> Site | None:
        site = self._get_site(site_id, organization=organization) if site_id is not None else None
        asset = self._get_asset(asset_id, organization=organization) if asset_id is not None else None
        system = self._get_system(system_id, organization=organization) if system_id is not None else None
        location = self._get_location(location_id, organization=organization) if location_id is not None else None
        if site is not None and asset is not None and asset.site_id != site.id:
            raise ValidationError(
                "Selected maintenance asset does not belong to the selected site.",
                code="MAINTENANCE_SCOPE_SITE_MISMATCH",
            )
        if site is not None and system is not None and system.site_id != site.id:
            raise ValidationError(
                "Selected maintenance system does not belong to the selected site.",
                code="MAINTENANCE_SCOPE_SITE_MISMATCH",
            )
        if site is not None and location is not None and location.site_id != site.id:
            raise ValidationError(
                "Selected maintenance location does not belong to the selected site.",
                code="MAINTENANCE_SCOPE_SITE_MISMATCH",
            )
        return site

    def _list_work_orders(
        self,
        *,
        organization: Organization,
        site_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
    ) -> list[MaintenanceWorkOrder]:
        rows = self._work_order_repo.list_for_organization(
            organization.id,
            site_id=site_id,
            asset_id=asset_id,
            system_id=system_id,
            location_id=location_id,
        )
        return list(
            filter_scope_rows(
                rows,
                self._user_session,
                scope_type="maintenance",
                permission_code="maintenance.read",
                scope_id_getter=self._scope_anchor_for_work_order,
            )
        )

    def _list_downtime_events(
        self,
        *,
        organization: Organization,
        site_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        started_from: datetime | None = None,
    ):
        filtered_work_orders = self._list_work_orders(
            organization=organization,
            site_id=site_id,
            asset_id=asset_id,
            system_id=system_id,
            location_id=location_id,
        )
        site_filtered_work_order_ids = {row.id for row in filtered_work_orders}
        allowed_asset_ids = {row.asset_id for row in filtered_work_orders if row.asset_id}
        allowed_system_ids = {row.system_id for row in filtered_work_orders if row.system_id}
        rows = self._downtime_event_repo.list_for_organization(
            organization.id,
            asset_id=asset_id,
            system_id=system_id,
            started_from=started_from,
        )
        if not site_filtered_work_order_ids and any(value is not None for value in (site_id, location_id)):
            return []
        filtered = []
        for row in rows:
            if site_filtered_work_order_ids:
                if row.work_order_id and row.work_order_id in site_filtered_work_order_ids:
                    filtered.append(row)
                    continue
                if row.asset_id and row.asset_id in allowed_asset_ids:
                    filtered.append(row)
                    continue
                if row.system_id and row.system_id in allowed_system_ids:
                    filtered.append(row)
                    continue
            else:
                filtered.append(row)
        return filtered

    def _failure_lookup(self, organization_id: str) -> dict[str, str]:
        return {
            row.failure_code: row.name
            for row in self._failure_code_repo.list_for_organization(organization_id, active_only=None)
        }

    def _anchor_lookup(self, organization_id: str) -> dict[tuple[str, str], tuple[str, str]]:
        anchors: dict[tuple[str, str], tuple[str, str]] = {}
        for row in self._asset_repo.list_for_organization(organization_id, active_only=None):
            anchors[("asset", row.id)] = (row.asset_code, row.name)
        for row in self._system_repo.list_for_organization(organization_id, active_only=None):
            anchors[("system", row.id)] = (row.system_code, row.name)
        for row in self._location_repo.list_for_organization(organization_id, active_only=None):
            anchors[("location", row.id)] = (row.location_code, row.name)
        return anchors

    def _pattern_anchor(self, row: MaintenanceWorkOrder) -> tuple[str, str]:
        if row.asset_id:
            return "asset", row.asset_id
        if row.system_id:
            return "system", row.system_id
        if row.location_id:
            return "location", row.location_id
        return "", ""

    def _leading_root_cause(self, rows: list[MaintenanceWorkOrder]) -> str:
        counts = Counter(row.root_cause_code for row in rows if row.root_cause_code)
        if not counts:
            return ""
        return counts.most_common(1)[0][0]

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

    @staticmethod
    def _activity_at(work_order: MaintenanceWorkOrder) -> datetime:
        return MaintenanceReliabilityService._normalize_timestamp(
            work_order.closed_at
            or work_order.actual_end
            or work_order.actual_start
            or work_order.planned_start
            or work_order.requested_at
            or work_order.created_at
            or datetime.now(timezone.utc)
        )

    @staticmethod
    def _is_open_status(status: MaintenanceWorkOrderStatus) -> bool:
        return status not in _TERMINAL_WORK_ORDER_STATUSES

    @staticmethod
    def _window_start(days: int) -> datetime:
        if days <= 0:
            raise ValidationError(
                "Analytics window must be greater than zero days.",
                code="MAINTENANCE_ANALYTICS_WINDOW_INVALID",
            )
        return datetime.now(timezone.utc) - timedelta(days=days)

    @staticmethod
    def _mean_repair_hours(rows: list[MaintenanceWorkOrder]) -> float | None:
        values = []
        for row in rows:
            start_at = MaintenanceReliabilityService._normalize_timestamp(row.actual_start)
            end_at = MaintenanceReliabilityService._normalize_timestamp(row.actual_end)
            if start_at is not None and end_at is not None and end_at >= start_at:
                values.append((end_at - start_at).total_seconds() / 3600.0)
            elif row.downtime_minutes:
                values.append(float(row.downtime_minutes) / 60.0)
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    @staticmethod
    def _repair_hours(rows: list[MaintenanceWorkOrder]) -> float | None:
        values = [
            (
                MaintenanceReliabilityService._normalize_timestamp(row.actual_end)
                - MaintenanceReliabilityService._normalize_timestamp(row.actual_start)
            ).total_seconds()
            / 3600.0
            for row in rows
            if MaintenanceReliabilityService._normalize_timestamp(row.actual_start) is not None
            and MaintenanceReliabilityService._normalize_timestamp(row.actual_end) is not None
            and MaintenanceReliabilityService._normalize_timestamp(row.actual_end)
            >= MaintenanceReliabilityService._normalize_timestamp(row.actual_start)
        ]
        if not values:
            values = [float(row.downtime_minutes or 0) / 60.0 for row in rows if row.downtime_minutes]
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    @staticmethod
    def _interval_hours(points: list[datetime]) -> float | None:
        if len(points) < 2:
            return None
        intervals = [
            (current - previous).total_seconds() / 3600.0
            for previous, current in zip(points, points[1:])
            if current >= previous
        ]
        if not intervals:
            return None
        return round(sum(intervals) / len(intervals), 2)

    @staticmethod
    def _normalize_timestamp(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _mean_interval_hours(self, rows: list[MaintenanceWorkOrder]) -> float | None:
        grouped: dict[str, list[datetime]] = defaultdict(list)
        for row in rows:
            if not row.failure_code:
                continue
            anchor_type, anchor_id = self._pattern_anchor(row)
            if not anchor_id:
                continue
            grouped[f"{anchor_type}:{anchor_id}"].append(self._activity_at(row))
        intervals = [
            value
            for points in grouped.values()
            for value in [self._interval_hours(sorted(points))]
            if value is not None
        ]
        if not intervals:
            return None
        return round(sum(intervals) / len(intervals), 2)

    def _get_site(self, site_id: str, *, organization: Organization):
        site = self._site_repo.get(site_id)
        if site is None or site.organization_id != organization.id:
            raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
        return site

    def _get_asset(self, asset_id: str, *, organization: Organization):
        asset = self._asset_repo.get(asset_id)
        if asset is None or asset.organization_id != organization.id:
            raise NotFoundError("Maintenance asset not found in the active organization.", code="MAINTENANCE_ASSET_NOT_FOUND")
        return asset

    def _get_system(self, system_id: str, *, organization: Organization):
        system = self._system_repo.get(system_id)
        if system is None or system.organization_id != organization.id:
            raise NotFoundError("Maintenance system not found in the active organization.", code="MAINTENANCE_SYSTEM_NOT_FOUND")
        return system

    def _get_location(self, location_id: str, *, organization: Organization):
        location = self._location_repo.get(location_id)
        if location is None or location.organization_id != organization.id:
            raise NotFoundError("Maintenance location not found in the active organization.", code="MAINTENANCE_LOCATION_NOT_FOUND")
        return location

    def _asset_label(self, asset_id: str) -> str:
        asset = self._asset_repo.get(asset_id)
        return asset.asset_code if asset is not None else asset_id

    def _system_label(self, system_id: str) -> str:
        system = self._system_repo.get(system_id)
        return system.system_code if system is not None else system_id

    def _location_label(self, location_id: str) -> str:
        location = self._location_repo.get(location_id)
        return location.location_code if location is not None else location_id

    def _require_report_view(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)
        require_permission(self._user_session, "report.view", operation_label=operation_label)


__all__ = ["MaintenanceReliabilityService"]
