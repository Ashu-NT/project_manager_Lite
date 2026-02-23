from __future__ import annotations

from datetime import date
from typing import Dict, Optional

from core.models import Task
from core.services.scheduling.models import CPMTaskInfo
from core.services.work_calendar.engine import WorkCalendarEngine


def build_schedule_result(
    tasks_by_id: Dict[str, Task],
    es: Dict[str, Optional[date]],
    ef: Dict[str, Optional[date]],
    ls: Dict[str, Optional[date]],
    lf: Dict[str, Optional[date]],
    calendar: WorkCalendarEngine,
) -> Dict[str, CPMTaskInfo]:
    result: Dict[str, CPMTaskInfo] = {}

    for task_id, task in tasks_by_id.items():
        est = es[task_id]
        eft = ef[task_id]
        lst = ls[task_id]
        lft = lf[task_id]

        if getattr(task, "actual_start", None) is None:
            task.start_date = est
        if getattr(task, "actual_end", None) is None:
            task.end_date = eft

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

