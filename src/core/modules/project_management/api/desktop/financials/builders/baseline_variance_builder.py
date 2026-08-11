"""Baseline variance assembly."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.lifecycle import FinancialBaselineVarianceDto
from src.core.modules.project_management.api.desktop.financials.serializers.baseline_variance_serializer import serialize_variance_record
from src.core.modules.project_management.api.desktop.financials.serializers.lifecycle_serializer import serialize_baseline_version


def build_baseline_variance_workspace(
    project_id: str,
    selected_baseline_id: str | None = None,
    baseline_service=None,
) -> FinancialBaselineVarianceDto:
    if not project_id or baseline_service is None:
        return FinancialBaselineVarianceDto()
    baselines = [
        item
        for item in baseline_service.list_baselines(project_id)
        if item.status.value in {"approved", "superseded"}
    ]
    approved = next(
        (item for item in baselines if item.status.value == "approved"),
        None,
    )
    selected = next(
        (item for item in baselines if item.id == selected_baseline_id),
        None,
    )
    selected = selected or approved or (baselines[0] if baselines else None)
    if selected is None:
        return FinancialBaselineVarianceDto()
    records = baseline_service.list_variance_records(selected.id)
    sorted_records = sorted(records, key=lambda r: abs(r.cost_variance or 0.0), reverse=True)
    return FinancialBaselineVarianceDto(
        baselines=tuple(serialize_baseline_version(item) for item in baselines),
        selected_baseline_id=selected.id,
        selected_baseline_label=f"{selected.name} v{selected.version}",
        compared_baseline_id=next(
            (record.superseded_baseline_id for record in sorted_records),
            "",
        ),
        records=tuple(serialize_variance_record(record) for record in sorted_records),
    )


__all__ = ["build_baseline_variance_workspace"]
