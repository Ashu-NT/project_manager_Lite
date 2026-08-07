from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.core.platform.contract.time_management.calendar.calendar_protocol import CalendarProtocol

from src.core.modules.project_management.domain.tasks.task import Task
from src.core.modules.project_management.application.scheduling.models.cpm import CPMTaskInfo


def build_schedule_result(
    tasks_by_id: dict[str, Task],
    es: dict[str, date | None],
    ef: dict[str, date | None],
    ls: dict[str, date | None],
    lf: dict[str, date | None],
    calendar: CalendarProtocol,
) -> dict[str, CPMTaskInfo]:
    result: dict[str, CPMTaskInfo] = {}

    for task_id, task in tasks_by_id.items():
        est = es[task_id]
        eft = ef[task_id]
        lst = ls[task_id]
        lft = lf[task_id]

        if getattr(task, "actual_start", None) is None or getattr(task, "actual_end", None) is None:
            task = replace(
                task,
                start_date=est if getattr(task, "actual_start", None) is None else task.start_date,
                end_date=eft if getattr(task, "actual_end", None) is None else task.end_date,
            )
            tasks_by_id[task_id] = task

        if est is not None and lst is not None:
            if lst < est:
                total_float = 0
            else:
                days = calendar.working_days_between(est, lst)
                total_float = max(0, days - 1)
        else:
            total_float = None

        is_critical = total_float == 0 if total_float is not None else False

        late_by = None
        if task.deadline and eft and eft > task.deadline:
            late_by = calendar.working_days_between(
                calendar.add_working_days(task.deadline, 1),
                eft,
            )

        result[task_id] = CPMTaskInfo(
            task=task,
            earliest_start=est,
            earliest_finish=eft,
            latest_start=lst,
            latest_finish=lft,
            total_float_days=total_float,
            is_critical=is_critical,
            deadline=task.deadline,
            late_by_days=late_by,
        )

    return result
