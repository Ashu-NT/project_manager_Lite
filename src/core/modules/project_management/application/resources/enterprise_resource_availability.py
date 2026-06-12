"""Enterprise-aware resource availability service.

Delegates all calendar logic to Platform's EnterpriseCalendarResolver.
Employee-backed resources inherit employee calendar automatically.
External resources use PM resource calendar assignment.
"""

from __future__ import annotations

from datetime import date

from src.core.platform.calendar.application.enterprise_calendar_resolver import (
    EnterpriseCalendarResolver,
    ResolvedCalendarContext,
)


class EnterpriseResourceAvailabilityService:
    """
    Calendar-aware availability service for PM resources.

    PM does NOT own calendar logic. All resolution delegates to Platform.

    Employee-backed (worker_type=EMPLOYEE, employee_id set):
        → uses employee calendar, inheriting global/site/dept chain
        → PM resource calendar is NOT consulted (no duplication)

    External (worker_type=EXTERNAL or no employee_id):
        → uses PM resource calendar assignment as source
        → inherits global/site chain if no project-specific override exists
    """

    def __init__(
        self,
        resolver: EnterpriseCalendarResolver,
        resource_repo,
    ) -> None:
        self._resolver = resolver
        self._resource_repo = resource_repo

    def get_availability(
        self,
        resource_id: str,
        *,
        project_id: str | None = None,
        site_id: str | None = None,
        department_id: str | None = None,
        target_date: date,
        assigned_hours: float = 0.0,
    ) -> ResolvedCalendarContext:
        resource = self._resource_repo.get(resource_id)
        if resource is None:
            raise ValueError(f"Resource '{resource_id}' not found.")

        worker_type, employee_id, resolve_resource_id = self._classify(resource, resource_id)

        return self._resolver.resolve_calendar_context(
            site_id=site_id,
            department_id=department_id,
            employee_id=employee_id,
            project_id=project_id,
            resource_id=resolve_resource_id,
            worker_type=worker_type,
            target_date=target_date,
            assigned_hours=assigned_hours,
        )

    def get_availability_range(
        self,
        resource_id: str,
        *,
        project_id: str | None = None,
        site_id: str | None = None,
        department_id: str | None = None,
        start: date,
        end: date,
        assigned_hours_by_date: dict[date, float] | None = None,
    ) -> list[ResolvedCalendarContext]:
        resource = self._resource_repo.get(resource_id)
        if resource is None:
            raise ValueError(f"Resource '{resource_id}' not found.")

        worker_type, employee_id, resolve_resource_id = self._classify(resource, resource_id)

        return self._resolver.resolve_range(
            site_id=site_id,
            department_id=department_id,
            employee_id=employee_id,
            project_id=project_id,
            resource_id=resolve_resource_id,
            worker_type=worker_type,
            start=start,
            end=end,
            assigned_hours_by_date=assigned_hours_by_date,
        )

    def is_available(self, resource_id: str, target_date: date) -> bool:
        ctx = self.get_availability(resource_id, target_date=target_date)
        return ctx.available_hours > 0

    def get_source_chain(self, resource_id: str) -> list[str]:
        resource = self._resource_repo.get(resource_id)
        if resource is None:
            return []
        worker_type, employee_id, resolve_resource_id = self._classify(resource, resource_id)
        return self._resolver.get_source_chain(
            employee_id=employee_id,
            resource_id=resolve_resource_id,
            worker_type=worker_type,
        )

    def _classify(
        self, resource, resource_id: str
    ) -> tuple[str, str | None, str | None]:
        wt = resource.worker_type
        worker_type = wt.value if wt else "EXTERNAL"
        if worker_type == "EMPLOYEE" and resource.employee_id:
            return "EMPLOYEE", resource.employee_id, None
        return "EXTERNAL", None, resource_id


__all__ = ["EnterpriseResourceAvailabilityService"]
