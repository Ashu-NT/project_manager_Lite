"""Change impact view-model assembly."""

from __future__ import annotations
from datetime import date

from src.core.modules.project_management.api.desktop.scheduling.models.change_impact import SchedulingChangeImpactDto
from src.core.modules.project_management.api.desktop.scheduling.serializers.change_impact_serializer import serialize_change_impact


def build_change_impact(
    project_id: str,
    task_id: str,
    proposed_start: date | None = None,
    proposed_finish: date | None = None,
    proposed_duration_days: int | None = None,
    *,
    change_impact_service=None,
    baseline_service=None,
) -> SchedulingChangeImpactDto | None:
    if not task_id or not project_id or change_impact_service is None:
        return None
    try:
        has_baseline = False
        if baseline_service is not None:
            try:
                has_baseline = baseline_service.get_approved_baseline(project_id) is not None
            except Exception:
                pass
        report = change_impact_service.analyse(
            project_id=project_id,
            changed_task_id=task_id,
            proposed_start=proposed_start,
            proposed_finish=proposed_finish,
            proposed_duration_days=proposed_duration_days,
            has_approved_baseline=has_baseline,
        )
    except Exception:
        return None
    return serialize_change_impact(task_id, report)


__all__ = ["build_change_impact"]
