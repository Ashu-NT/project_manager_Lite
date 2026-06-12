from __future__ import annotations

from typing import Any

from src.core.modules.project_management.domain.risk.register import (
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.ui_qml.modules.project_management.view_models.register import (
    RegisterMetricViewModel,
    RegisterOverviewViewModel,
)

from .utils import is_active

def build_register_overview(*, scope_entries: Any, filtered_entries: Any) -> RegisterOverviewViewModel:
    return RegisterOverviewViewModel(
        title="Register",
        subtitle="Cross-project risks, issues, changes, and governance review queue.",
        metrics=(
            RegisterMetricViewModel(
                label="Visible entries",
                value=str(len(filtered_entries)),
                supporting_text=f"{len(scope_entries)} total within the selected project scope.",
            ),
            RegisterMetricViewModel(
                label="Open risks",
                value=str(
                    sum(
                        1
                        for entry in filtered_entries
                        if entry.entry_type == RegisterEntryType.RISK.value
                        and is_active(entry.status)
                    )
                ),
                supporting_text="Risk records still open or under mitigation.",
            ),
            RegisterMetricViewModel(
                label="Open issues",
                value=str(
                    sum(
                        1
                        for entry in filtered_entries
                        if entry.entry_type == RegisterEntryType.ISSUE.value
                        and is_active(entry.status)
                    )
                ),
                supporting_text="Execution blockers needing ownership.",
            ),
            RegisterMetricViewModel(
                label="Pending changes",
                value=str(
                    sum(
                        1
                        for entry in filtered_entries
                        if entry.entry_type == RegisterEntryType.CHANGE.value
                        and entry.status in {
                            RegisterEntryStatus.OPEN.value,
                            RegisterEntryStatus.IN_PROGRESS.value,
                        }
                    )
                ),
                supporting_text="Changes awaiting decision or completion.",
            ),
            RegisterMetricViewModel(
                label="Overdue",
                value=str(sum(1 for entry in filtered_entries if entry.is_overdue)),
                supporting_text="Active entries with missed due dates.",
            ),
        ),
    )
