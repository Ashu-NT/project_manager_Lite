"""Baseline variance assembly."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.baseline_variance import BaselineVarianceRecordDto
from src.core.modules.project_management.api.desktop.financials.serializers.baseline_variance_serializer import serialize_variance_record


def build_baseline_variance(
    project_id: str,
    baseline_service=None,
) -> tuple[BaselineVarianceRecordDto, ...]:
    if not project_id or baseline_service is None:
        return ()
    try:
        approved = baseline_service.get_approved_baseline(project_id)
    except Exception:
        return ()
    if approved is None:
        return ()
    try:
        records = baseline_service.list_variance_records(approved.id)
    except Exception:
        return ()
    sorted_records = sorted(records, key=lambda r: abs(r.cost_variance or 0.0), reverse=True)
    return tuple(serialize_variance_record(r) for r in sorted_records)


__all__ = ["build_baseline_variance"]
