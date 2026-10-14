from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.dashboard.models.report_models import (
    ProjectKPI,
    ResourceLoadRow,
)
from src.core.modules.project_management.domain.tasks.task import Task


class DashboardAlertBuilder:
    """Builds project dashboard alert lines from already-loaded read data."""

    def build(
        self,
        kpi: ProjectKPI,
        resource_load: list[ResourceLoadRow],
        *,
        tasks: list[Task],
    ) -> list[str]:
        alerts: list[str] = []
        today = date.today()  # noqa: DTZ011
        for row in resource_load:
            utilization = float(getattr(row, "utilization_percent", row.total_allocation_percent) or 0.0)
            capacity = float(getattr(row, "capacity_percent", 100.0) or 100.0)
            if utilization > 100.0:
                alerts.append(
                    f'Resource "{row.resource_name}" is overloaded '
                    f"({utilization:.1f}% utilization, "
                    f"{row.total_allocation_percent:.1f}% assigned / {capacity:.1f}% capacity "
                    f"across {row.tasks_count} tasks)."
                )


        def _status_value(task) -> str:
            raw = getattr(task, "status", "")
            value = getattr(raw, "value", raw)
            return str(value).strip().upper()

        late_open = [
            task
            for task in tasks
            if _status_value(task) != "DONE"
            and task.deadline
            and task.end_date
            and task.end_date > task.deadline
        ]
        if late_open:
            alerts.append(f"There are {len(late_open)} late tasks in this project.")

        missing_dates = [
            task
            for task in tasks
            if (task.duration_days or 0) > 0
            and (task.start_date is None or task.end_date is None)
        ]
        if missing_dates:
            alerts.append(
                f"{len(missing_dates)} task(s) have duration but are missing start or end dates."
            )

        if not tasks:
            alerts.append("This project has no tasks yet.")
        elif not (kpi.start_date and kpi.end_date):
            alerts.append("Project schedule has incomplete dates. Check task start/end.")

        if kpi.end_date and kpi.end_date < today and kpi.tasks_completed < kpi.tasks_total:
            alerts.append(f"Project appears delayed: planned finish was {kpi.end_date.isoformat()}.")

        for task in tasks:
            status = _status_value(task)
            if status == "DONE":
                if task.actual_end and task.end_date:
                    if task.actual_end > task.end_date:
                        alerts.append(
                            f"Task '{task.name}' completed late "
                            f"({task.actual_end.isoformat()} vs plan {task.end_date.isoformat()})."
                        )
                    else:
                        alerts.append(
                            f"Task '{task.name}' completed on time "
                            f"({task.actual_end.isoformat()})."
                        )
                continue

            if task.deadline and task.end_date and task.end_date > task.deadline:
                alerts.append(f"Task '{task.name}' missed its deadline.")

                priority = int(getattr(task, "priority", 0) or 0)
                if priority >= 80:
                    alerts.append(f"High-priority task '{task.name}' is late.")

        return alerts


__all__ = ["DashboardAlertBuilder"]
