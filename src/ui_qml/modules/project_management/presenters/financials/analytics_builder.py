from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsRecordViewModel,
)


def build_analytics_collection(
    *,
    title: str,
    subtitle: str,
    rows,
) -> FinancialsCollectionViewModel:
    return FinancialsCollectionViewModel(
        title=title,
        subtitle=subtitle,
        empty_state=f"No {title.lower()} data is available for the selected project.",
        items=tuple(
            FinancialsRecordViewModel(
                id=f"{row.dimension}:{row.key}",
                title=row.label,
                status_label=row.exposure_label,
                subtitle=f"Planned {row.planned_label} | Forecast {row.forecast_label}",
                supporting_text=f"Committed {row.committed_label} | Actual {row.actual_label}",
                meta_text=f"Exposure {row.exposure_label}",
                can_primary_action=False,
                can_secondary_action=False,
                state={},
            )
            for row in rows[:8]
        ),
    )
