from __future__ import annotations

import re
import shlex
from datetime import date

from src.core.modules.project_management.contracts.reads.tasks import (
    TaskWorkspaceCondition,
    TaskWorkspaceCriteria,
)


_CONDITION = re.compile(
    r"^(status|priority|progress|start|end|deadline)(:|<=|>=|=|<|>)(.+)$",
    flags=re.IGNORECASE,
)


def build_task_workspace_criteria(
    *,
    project_id: str | None,
    search_text: str,
    status: str,
    priority: str,
    schedule: str,
    as_of: date,
    milestones_only: bool = False,
) -> TaskWorkspaceCriteria:
    terms: list[str] = []
    conditions: list[TaskWorkspaceCondition] = []
    for token in shlex.split(str(search_text or "")):
        match = _CONDITION.match(token)
        if match is None:
            terms.append(token.casefold())
            continue
        field, operator, value = match.groups()
        conditions.append(
            TaskWorkspaceCondition(
                field=field.casefold(),
                operator=operator,
                value=value.strip(),
            )
        )
    return TaskWorkspaceCriteria(
        project_id=str(project_id or "").strip() or None,
        search_terms=tuple(terms),
        conditions=tuple(conditions),
        status=str(status or "all").strip().upper(),
        priority=str(priority or "all").strip().lower(),
        schedule=str(schedule or "all").strip().lower(),
        milestones_only=bool(milestones_only),
        as_of=as_of,
    )


__all__ = ["build_task_workspace_criteria"]
