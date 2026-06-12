from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsRecordViewModel,
)

def build_ledger_collection(snapshot: Any) -> FinancialsCollectionViewModel:
    return FinancialsCollectionViewModel(
        title="Ledger Trail",
        subtitle="Recent entries that feed the selected project's finance view.",
        empty_state="No ledger rows are available for the selected project.",
        items=tuple(
            FinancialsRecordViewModel(
                id=f"{index}",
                title=row.reference_label,
                status_label=row.amount_label,
                subtitle=f"{row.source_label} | {row.stage}",
                supporting_text=f"{row.task_name} | {row.resource_name}",
                meta_text=(
                    f"{row.occurred_on_label} | "
                    + ("Included in policy" if row.included_in_policy else "Outside policy")
                ),
                can_primary_action=False,
                can_secondary_action=False,
                state={},
            )
            for index, row in enumerate(snapshot.ledger[:10], start=1)
        ),
    )
