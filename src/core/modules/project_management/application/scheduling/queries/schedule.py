"""Project schedule response query over the authoritative CPM engine."""

from datetime import date

from src.core.modules.project_management.application.scheduling.dto.responses.schedule import (
    SchedulingTaskResponse,
)
from src.core.modules.project_management.application.scheduling.mappers.schedule import (
    map_schedule_item,
)
from src.core.modules.project_management.application.scheduling.services.scheduling_engine import (
    SchedulingEngine,
)


def query_schedule_responses(
    project_id: str, scheduling_engine: SchedulingEngine, *, persist: bool,
) -> tuple[SchedulingTaskResponse, ...]:
    schedule = scheduling_engine.recalculate_project_schedule(project_id, persist=persist)
    items = sorted(
        schedule.values(),
        key=lambda info: (
            info.earliest_start or date.max,
            0 if info.is_critical else 1,
            (info.task.name or "").casefold(),
        ),
    )
    return tuple(map_schedule_item(item) for item in items)
