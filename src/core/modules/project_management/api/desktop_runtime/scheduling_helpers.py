from __future__ import annotations

from src.core.platform.contract.port.time_management.calendar.calendar_protocol import CalendarProtocol
from src.core.modules.project_management.application.scheduling.forecasting.schedule_change_impact_service import (
    ScheduleChangeImpactService,
)
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)


def build_schedule_change_impact_service(
    task_service: TaskService | None,
    calendar: CalendarProtocol | None,
    baseline_service: BaselineService | None,
) -> ScheduleChangeImpactService | None:
    if task_service is None or calendar is None or baseline_service is None:
        return None
    task_repo = getattr(task_service, "_task_repo", None)
    dependency_repo = getattr(task_service, "_dependency_repo", None)
    if task_repo is None or dependency_repo is None:
        return None
    return ScheduleChangeImpactService(
        task_repo=task_repo,
        dependency_repo=dependency_repo,
        calendar=calendar,
        baseline_lookup=baseline_service,
    )


__all__ = ["build_schedule_change_impact_service"]
