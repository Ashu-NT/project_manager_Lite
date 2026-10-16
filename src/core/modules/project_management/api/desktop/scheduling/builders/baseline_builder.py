"""Baseline view-model assembly."""

import logging

from src.core.modules.project_management.api.desktop.scheduling.formatters.baseline_formatter import (
    format_baseline_row,
)
from src.core.modules.project_management.api.desktop.scheduling.models.baselines import (
    SchedulingBaselineOptionDescriptor,
    SchedulingBaselineRowDto,
)
from src.core.modules.project_management.application.scheduling.dto.responses.baselines import (
    SchedulingBaselineVarianceRowDto,
)

logger = logging.getLogger(__name__)




def build_baseline_options(project_id: str, baseline_query=None) -> tuple[SchedulingBaselineOptionDescriptor, ...]:
    if not project_id or baseline_query is None:
        return ()
    baselines = baseline_query.list_baselines(project_id)
    return tuple(
        SchedulingBaselineOptionDescriptor(
            value=b.id, label=f"{b.name} ({b.created_at.isoformat()})"
        )
        for b in baselines
    )


def build_baseline_rows(project_id: str, baseline_query=None) -> tuple[SchedulingBaselineRowDto, ...]:
    if not project_id or baseline_query is None:
        return ()
    baselines = sorted(baseline_query.list_baselines(project_id), key=lambda b: b.created_at, reverse=True)
    return tuple(format_baseline_row(b, i) for i, b in enumerate(baselines))


def build_variance_rows(baseline_id: str, baseline_query=None) -> tuple[SchedulingBaselineVarianceRowDto, ...]:
    if not baseline_id or baseline_query is None:
        return ()
    try:
        records = baseline_query.query_variance_responses(baseline_id)
    except Exception:
        logger.exception("Failed to build variance rows for baseline_id=%s", baseline_id)
        return ()
    return records


__all__ = ["build_baseline_options", "build_baseline_rows", "build_variance_rows"]
