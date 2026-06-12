from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCommitmentSummaryViewModel,
)

def build_commitment_summary(summary_dto: Any) -> FinancialsCommitmentSummaryViewModel:
    return FinancialsCommitmentSummaryViewModel(
        planned_label=summary_dto.planned_label,
        uncommitted_label=summary_dto.uncommitted_label,
        committed_label=summary_dto.committed_label,
        invoiced_label=summary_dto.invoiced_label,
        paid_label=summary_dto.paid_label,
        exposure_label=summary_dto.exposure_label,
        commitment_rate_pct=summary_dto.commitment_rate_pct,
    )
