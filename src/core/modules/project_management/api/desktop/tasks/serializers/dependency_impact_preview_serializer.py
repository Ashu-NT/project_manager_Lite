from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.models.dependency import (
    TaskDependencyImpactPreviewDesktopDto,
    TaskDependencyImpactRowDesktopDto,
)


def _date_label(value) -> str:
    return value.isoformat() if value is not None else "--"


def serialize_dependency_impact_preview(diagnostic) -> TaskDependencyImpactPreviewDesktopDto:
    rows = tuple(
        TaskDependencyImpactRowDesktopDto(
            task_id=row.task_id,
            task_name=row.task_name,
            before_start_label=_date_label(row.before_start),
            before_finish_label=_date_label(row.before_finish),
            after_start_label=_date_label(row.after_start),
            after_finish_label=_date_label(row.after_finish),
            start_shift_days=row.start_shift_days,
            finish_shift_days=row.finish_shift_days,
        )
        for row in diagnostic.impact_rows
    )
    largest_shift = 0
    if rows:
        largest_shift = max(
            max(abs(row.start_shift_days or 0), abs(row.finish_shift_days or 0))
            for row in diagnostic.impact_rows
        )
    return TaskDependencyImpactPreviewDesktopDto(
        is_valid=diagnostic.is_valid,
        code=diagnostic.code,
        summary=diagnostic.summary,
        detail=diagnostic.detail,
        risk_level=diagnostic.risk_level,
        affected_task_count=len(rows),
        largest_shift_days=largest_shift,
        rows=rows,
        suggestions=tuple(diagnostic.suggestions),
    )


__all__ = ["serialize_dependency_impact_preview"]
