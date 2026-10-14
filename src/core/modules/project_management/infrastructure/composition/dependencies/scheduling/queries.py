from __future__ import annotations

from src.core.modules.project_management.application.scheduling.forecasting.queries.change_impact import (
    ScheduleChangeImpactQueryHandler,
)
from src.core.modules.project_management.contracts.ports.scheduling.approved_baseline_lookup import (
    ApprovedBaselineLookup,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    DependencyRepository,
    TaskRepository,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)


def build_schedule_change_impact_query(
    *, task_repo: TaskRepository, dependency_repo: DependencyRepository,
    calendar: CalendarProtocol, baseline_lookup: ApprovedBaselineLookup,
) -> ScheduleChangeImpactQueryHandler:
    return ScheduleChangeImpactQueryHandler(
        task_repo=task_repo, dependency_repo=dependency_repo,
        calendar=calendar, baseline_lookup=baseline_lookup,
    )

