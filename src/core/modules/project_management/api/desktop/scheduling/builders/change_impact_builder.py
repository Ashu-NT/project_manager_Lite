"""Change impact view-model assembly."""

from __future__ import annotations

import logging
from datetime import date

from src.core.modules.project_management.application.scheduling.dto.responses.change_impact import (
    SchedulingChangeImpactDto,
)

logger = logging.getLogger(__name__)


def build_change_impact(
    project_id: str,
    task_id: str,
    proposed_start: date | None = None,
    proposed_finish: date | None = None,
    proposed_duration_days: int | None = None,
    *,
    change_impact_service=None,
) -> SchedulingChangeImpactDto | None:
    if not task_id or not project_id or change_impact_service is None:
        return None
    try:
        response = change_impact_service.analyse(
            project_id=project_id,
            changed_task_id=task_id,
            proposed_start=proposed_start,
            proposed_finish=proposed_finish,
            proposed_duration_days=proposed_duration_days,
        )
    except Exception:
        logger.exception("Failed to build change impact for project_id=%s, task_id=%s", project_id, task_id)
        return None
    return response

__all__ = ["build_change_impact"]
