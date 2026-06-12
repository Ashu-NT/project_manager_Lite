"""Baseline display formatting."""

from src.core.modules.project_management.api.desktop.scheduling.models.baselines import (
    SchedulingBaselineRowDto,
)


def format_baseline_row(baseline, index: int) -> SchedulingBaselineRowDto:
    status_val = str(getattr(baseline.status, "value", baseline.status) or "draft")
    status_label = status_val.replace("_", " ").title()
    return SchedulingBaselineRowDto(
        id=baseline.id,
        name=baseline.name,
        created_at=baseline.created_at.date() if hasattr(baseline.created_at, "date") else baseline.created_at,
        created_at_label=baseline.created_at.strftime("%Y-%m-%d %H:%M"),
        approved_by_label=str(getattr(baseline, "approved_by", "") or "System snapshot"),
        variance_state_label="Latest" if index == 0 else "Stored",
        status=status_val,
        status_label=status_label,
        can_submit=status_val == "draft",
        can_approve=status_val == "submitted",
        can_reject=status_val == "submitted",
    )


__all__ = ["format_baseline_row"]
