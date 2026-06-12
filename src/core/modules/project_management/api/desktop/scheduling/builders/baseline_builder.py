"""Baseline view-model assembly."""

from src.core.modules.project_management.api.desktop.scheduling.models.baselines import (
    SchedulingBaselineOptionDescriptor,
    SchedulingBaselineRowDto,
    SchedulingBaselineVarianceRowDto,
)
from src.core.modules.project_management.api.desktop.scheduling.formatters.baseline_formatter import format_baseline_row


def build_baseline_options(project_id: str, baseline_service=None) -> tuple[SchedulingBaselineOptionDescriptor, ...]:
    if not project_id or baseline_service is None:
        return ()
    baselines = baseline_service.list_baselines(project_id)
    return tuple(
        SchedulingBaselineOptionDescriptor(
            value=b.id, label=f"{b.name} ({b.created_at.isoformat()})"
        )
        for b in baselines
    )


def build_baseline_rows(project_id: str, baseline_service=None) -> tuple[SchedulingBaselineRowDto, ...]:
    if not project_id or baseline_service is None:
        return ()
    baselines = sorted(baseline_service.list_baselines(project_id), key=lambda b: b.created_at, reverse=True)
    return tuple(format_baseline_row(b, i) for i, b in enumerate(baselines))


def build_variance_rows(baseline_id: str, baseline_service=None) -> tuple[SchedulingBaselineVarianceRowDto, ...]:
    if not baseline_id or baseline_service is None:
        return ()
    try:
        records = baseline_service.list_variance_records(baseline_id)
    except Exception:
        return ()
    return tuple(
        SchedulingBaselineVarianceRowDto(
            id=str(getattr(r, "id", "") or ""),
            project_id=str(getattr(r, "project_id", "") or ""),
            new_baseline_id=str(getattr(r, "new_baseline_id", "") or ""),
            superseded_baseline_id=str(getattr(r, "superseded_baseline_id", "") or ""),
            task_id=str(getattr(r, "task_id", "") or ""),
            task_name=str(getattr(r, "task_name", "") or getattr(r, "task_id", "")),
            start_variance_days=int(getattr(r, "start_variance_days", 0) or 0),
            finish_variance_days=int(getattr(r, "finish_variance_days", 0) or 0),
            cost_variance=float(getattr(r, "cost_variance", 0.0) or 0.0),
            created_at=(r.created_at.date() if hasattr(r.created_at, "date") else getattr(r, "created_at", None)),
        )
        for r in records
    )


__all__ = ["build_baseline_options", "build_baseline_rows", "build_variance_rows"]
