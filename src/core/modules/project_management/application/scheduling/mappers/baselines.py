"""Neutral baseline response mapping; no display labels."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.modules.project_management.application.dashboard.models.report_models import (
        BaselineComparisonRow,
    )
from src.core.modules.project_management.application.scheduling.dto.responses.baselines import (
    SchedulingBaselineComparisonRowDto,
    SchedulingBaselineResponse,
    SchedulingBaselineVarianceRowDto,
)
from src.core.modules.project_management.domain.scheduling.baseline import (
    BaselineVarianceRecord,
    ProjectBaseline,
)
from src.core.platform.common.exceptions import ValidationError


def map_baseline(baseline: ProjectBaseline) -> SchedulingBaselineResponse:
    return SchedulingBaselineResponse(
        id=baseline.id,
        project_id=baseline.project_id,
        name=baseline.name,
        created_at=baseline.created_at,
        status=baseline.status.value,
        version=baseline.version,
        submitted_by=baseline.submitted_by,
        submitted_at=baseline.submitted_at,
        approved_by=baseline.approved_by,
        approved_at=baseline.approved_at,
        notes=baseline.notes,
        can_submit=baseline.can_submit,
        can_approve=baseline.can_approve,
        can_reject=baseline.can_reject,
    )


def _required_decimal(value: Decimal | None) -> Decimal:
    if value is None:
        raise ValidationError(
            "Decimal value is required.", code="DECIMAL_VALUE_REQUIRED"
        )
    return value


def map_baseline_comparison(
    row: BaselineComparisonRow,
) -> SchedulingBaselineComparisonRowDto:
    return SchedulingBaselineComparisonRowDto(
        task_id=row.task_id,
        task_name=row.task_name,
        change_type=row.change_type,
        baseline_a_start=row.baseline_a_start,
        baseline_a_finish=row.baseline_a_finish,
        baseline_b_start=row.baseline_b_start,
        baseline_b_finish=row.baseline_b_finish,
        start_shift_days=row.start_shift_days,
        finish_shift_days=row.finish_shift_days,
        duration_delta_days=row.duration_delta_days,
        planned_cost_delta=_required_decimal(row.planned_cost_delta),
    )


def map_baseline_variance(
    r: BaselineVarianceRecord,
) -> SchedulingBaselineVarianceRowDto:
    return SchedulingBaselineVarianceRowDto(
        id=str(getattr(r, "id", "") or ""),
        project_id=str(getattr(r, "project_id", "") or ""),
        new_baseline_id=str(getattr(r, "new_baseline_id", "") or ""),
        superseded_baseline_id=str(getattr(r, "superseded_baseline_id", "") or ""),
        task_id=str(getattr(r, "task_id", "") or ""),
        task_name=str(getattr(r, "task_name", "") or getattr(r, "task_id", "")),
        start_variance_days=int(getattr(r, "start_variance_days", 0) or 0),
        finish_variance_days=int(getattr(r, "finish_variance_days", 0) or 0),
        cost_variance=r.cost_variance,
        created_at=r.created_at.date()
        if hasattr(r.created_at, "date")
        else getattr(r, "created_at", None),
    )
