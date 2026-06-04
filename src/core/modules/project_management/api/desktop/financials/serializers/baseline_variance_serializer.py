"""Baseline variance record serializer."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.baseline_variance import BaselineVarianceRecordDto


def serialize_variance_record(r) -> BaselineVarianceRecordDto:
    cost_var = float(r.cost_variance or 0.0)
    return BaselineVarianceRecordDto(
        task_id=str(r.task_id or ""),
        task_name=str(r.task_name or r.task_id or "Task"),
        start_variance_days=int(r.start_variance_days or 0),
        finish_variance_days=int(r.finish_variance_days or 0),
        cost_variance=cost_var,
        cost_variance_label=f"+{cost_var:,.2f}" if cost_var >= 0 else f"{cost_var:,.2f}",
        tone="danger" if cost_var > 0 else "success" if cost_var < 0 else "default",
    )


__all__ = ["serialize_variance_record"]
