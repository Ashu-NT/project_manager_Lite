from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from core.models import Task


@dataclass
class CPMTaskInfo:
    task: Task
    earliest_start: Optional[date]
    earliest_finish: Optional[date]
    latest_start: Optional[date]
    latest_finish: Optional[date]
    total_float_days: Optional[int]
    is_critical: bool
    deadline: Optional[date] = None
    late_by_days: Optional[int] = None

