from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementSchedulingDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingCollectionViewModel,
)

from .record_mappers import to_baseline_variance_record


def build_baseline_variance_collection(
    desktop_api: ProjectManagementSchedulingDesktopApi,
    baseline_id: str,
) -> SchedulingCollectionViewModel:
    normalized_id = (baseline_id or "").strip()
    if not normalized_id:
        return SchedulingCollectionViewModel(
            title="Baseline Variance",
            subtitle="Per-task variance recorded when this baseline was approved.",
            empty_state="Select a baseline to review its approval-time variance records.",
        )
    try:
        records = desktop_api.list_baseline_variance_records(normalized_id)
    except Exception:
        records = ()
    if not records:
        return SchedulingCollectionViewModel(
            title="Baseline Variance",
            subtitle="Per-task variance recorded when this baseline was approved.",
            empty_state=(
                "No variance records are stored for this baseline. "
                "Variance is recorded when a new baseline supersedes the previously approved one."
            ),
        )
    return SchedulingCollectionViewModel(
        title="Baseline Variance",
        subtitle=f"Approval-time variance: {len(records)} task(s) changed from the previous baseline.",
        items=tuple(to_baseline_variance_record(rec) for rec in records),
    )


__all__ = ["build_baseline_variance_collection"]
